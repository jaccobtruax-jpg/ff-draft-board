#!/usr/bin/env python3
"""Build data/mocks.json — mock-draft corpus for the pre-draft page.

Two jobs:
  1. ingest(paths...) — convert user mock data (canonical JSON or CSV) into
     the board schema, matching player names to board.json pids.
  2. sample generation — a seeded, clearly-labeled sample corpus so the
     pre-draft UI is demonstrable before the user's real mocks arrive.

Canonical input JSON (what the importer in the browser also accepts):
  {
    "league": 0,                      # which league tab this mock belongs to
    "label": "Aug 24 mock",           # display name
    "format": "snake",                # snake | auction
    "mySlot": 5,                      # user's draft slot in this mock
    "teams": ["Dolphin fans are gay", "Taco Tuesday", ...],  # slot 1..N
    "picks": [
      {"slot": 5, "round": 1, "player": "Josh Allen", "pos": "QB",
       "adp": 3.2, "pts": 425.5}
    ]
  }

CSV input: header row with (round|r), (slot|pick), (team), (player|name), (pos),
optional (adp), (pts). team column may be the team NAME or the slot number.
"""
import json, re, sys, csv, random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOARD = json.loads((ROOT / "data" / "board.json").read_text())
PLAYERS = BOARD["players"]
RANKINGS = BOARD["rankings"]

SUFFIXES = (" jr", " sr", " iii", " ii", " iv", " v", " dst", " d/st", " defense", " d")
ALIASES = {
    "commanders": "washington commanders",
    "washington": "washington commanders",
    "patriots d": "new england patriots dst",
}

def norm_name(s):
    """Lowercase, strip suffixes/punctuation -> comparable key."""
    if not s: return ""
    s = str(s).lower().strip()
    for suf in SUFFIXES:
        if s.endswith(suf):
            s = s[: -len(suf)].rstrip()
    s = re.sub(r"[^a-z0-9]+", "", s)
    return ALIASES.get(s, s)

# precompute lookup
BY_NORM = {}
for pid, p in PLAYERS.items():
    BY_NORM.setdefault(norm_name(p["n"]), []).append(pid)

def match_player(raw_name):
    """Return (pid, confidence) for a raw mock name, or (None, 0)."""
    if not raw_name: return None, 0
    key = norm_name(raw_name)
    if key in BY_NORM:
        return BY_NORM[key][0], 1.0
    # token-subset fallback: every token of the input appears in a board name
    tokens = set(key)
    # word-level fallback
    words = re.findall(r"[a-z]+", raw_name.lower())
    best, best_pid = 0.0, None
    for pid, p in PLAYERS.items():
        pwords = set(re.findall(r"[a-z]+", p["n"].lower()))
        inter = len(words and pwords.intersection(words))
        if words and inter / len(words) >= 0.9 and inter / max(1, len(pwords)) >= 0.6:
            score = inter / max(1, len(words))
            if score > best:
                best, best_pid = score, pid
    if best >= 0.9:
        return best_pid, best
    return None, 0

def adp_for(p, pos):
    v = p.get("adp_q") or p.get("adp_h") or p.get("adp_p") or p.get("adp")
    return round(v, 1) if v else None

def pts_for(pid, scoring="TE PREM (4pt QB)"):
    r = RANKINGS.get(scoring, {})
    top = r.get("top200", [])
    for row in top:
        if row[0] == pid:
            return round(row[2], 1)
    for posrows in r.get("positions", {}).values():
        for row in posrows:
            if row[0] == pid:
                return round(row[2], 1)
    return None

def build_mock(src, scoring="TE PREM (4pt QB)"):
    """src: dict in canonical schema -> normalized mock dict with pids."""
    teams = src["teams"]
    n = len(teams)
    picks = []
    unmatched = []
    for p in src["picks"]:
        slot = int(p.get("slot") or 0)
        rnd = int(p.get("round") or 0)
        overall = int(p.get("overall") or ((rnd - 1) * n + slot))
        raw = p.get("player") or p.get("name") or ""
        pid, conf = match_player(raw)
        if not pid:
            unmatched.append(raw)
            continue
        pl = PLAYERS[pid]
        pos = (p.get("pos") or pl["p"]).upper()
        picks.append({
            "slot": slot, "team": slot - 1, "round": rnd, "overall": overall,
            "pid": pid, "name": pl["n"], "pos": pos,
            "adp": p.get("adp") if p.get("adp") is not None else adp_for(pl, pos),
            "pts": p.get("pts") if p.get("pts") is not None else pts_for(pid, scoring),
        })
    picks.sort(key=lambda x: x["overall"])
    return {
        "id": src.get("id") or re.sub(r"[^a-z0-9]+", "-", src.get("label", "mock").lower()).strip("-"),
        "league": int(src.get("league") or 0),
        "label": src.get("label") or "Mock draft",
        "format": src.get("format") or "snake",
        "mySlot": int(src.get("mySlot") or 1),
        "teams": teams,
        "picks": picks,
    }, unmatched

def parse_csv(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    if not rows: return None
    def col(*names):
        for n in names:
            if n in rows[0] and rows[0][n] != "":
                return n
        return None
    c_round = col("round", "r")
    c_slot = col("slot", "pick", "pk")
    c_team = col("team", "manager", "tm")
    c_pl = col("player", "name", "pname")
    c_pos = col("pos", "position")
    if not (c_round and c_pl): raise ValueError("CSV needs at least round + player columns")
    teams = []
    picks = []
    for r in rows:
        if not r.get(c_pl): continue
        team = (r.get(c_team) or "").strip()
        slot = None
        if c_slot and r.get(c_slot): slot = int(float(r[c_slot]))
        elif team:
            m = re.match(r"^(\d+)", team)
            if m: slot = int(m.group(1))
        if slot is None: raise ValueError("CSV needs a slot/pick column or numeric team column")
        while len(teams) < max(1, slot):
            teams.append("Manager %d" % (len(teams) + 1))
        if not teams[slot - 1] or teams[slot - 1].startswith("Manager"):
            teams[slot - 1] = team or ("Manager %d" % slot)
        picks.append({
            "round": int(float(r[c_round])),
            "slot": slot,
            "player": r[c_pl],
            "pos": (r.get(c_pos) or "").upper(),
            "adp": float(r["adp"]) if r.get("adp") else None,
            "pts": float(r["pts"]) if r.get("pts") else None,
        })
    return {"label": path.stem, "mySlot": 1, "teams": teams, "picks": picks}

# ---------------------------------------------------------------- sample gen
SAMPLE_TEAMS = [
    "Taco Tuesday", "Gurley Men", "The Bluffs", "Saquon's Kids",
    "Dolphin fans are gay", "GridIron Goblins", "Puny Humans", "League Winner",
    "Waddle Waddle", "Barkley's Barking",
]
MY_SLOT = 5
# persona: position pick-order template per round 1..16 (M=my slot; others by index)
PERSONAS = {
    0: ["RB","RB","TE","WR","QB","WR","RB","TE","QB","WR","RB","WR","TE","WR","RB","QB"],  # Taco Tuesday (TE early)
    1: ["RB","RB","RB","WR","WR","QB","WR","TE","RB","WR","QB","RB","WR","TE","WR","RB"],  # Gurley Men
    2: ["QB","RB","WR","RB","WR","TE","QB","WR","RB","WR","RB","TE","WR","QB","RB","WR"],  # The Bluffs (QB r1, 2QB early)
    3: ["RB","WR","RB","WR","RB","QB","TE","WR","RB","WR","RB","QB","WR","TE","WR","RB"],  # Saquon's Kids
    4: ["RB","RB","TE","WR","QB","WR","RB","TE","QB","WR","WR","RB","TE","WR","RB","QB"],  # ME — Dolphin fans
    5: ["WR","RB","WR","RB","WR","TE","WR","RB","QB","WR","RB","WR","TE","RB","QB","WR"],  # GridIron Goblins (waits QB)
    6: ["WR","WR","WR","RB","TE","RB","WR","QB","WR","RB","WR","RB","TE","WR","QB","RB"],  # Puny Humans
    7: ["RB","WR","WR","RB","TE","QB","WR","RB","WR","TE","RB","WR","QB","RB","WR","TE"],  # League Winner (balanced)
    8: ["WR","TE","WR","RB","WR","TE","RB","QB","WR","RB","WR","RB","TE","WR","QB","RB"],  # Waddle Waddle (2TE early)
    9: ["RB","WR","TE","WR","RB","QB","WR","RB","WR","TE","RB","WR","QB","WR","RB","TE"],  # Barkley's Barking
}
# per-mock variation: shift some rounds for a couple of personas so trends show spread
MOCK_TWEAKS = [
    {4: {3: "WR", 5: "QB", 7: "TE"}},   # mock 1: I take WR r3, QB r5, TE r7
    {},                                  # mock 2: base (TE r3)
    {2: {1: "QB"}, 0: {4: "TE"}},        # mock 3: Bluffs again QB r1, Taco TE r4
]

def gen_sample(scoring="TE PREM (4pt QB)"):
    rnd = random.Random(2026)
    mocks = []
    for mi in range(3):
        teams = list(SAMPLE_TEAMS)
        pools = {pos: [] for pos in "QB RB WR TE".split()}
        r = RANKINGS[scoring]
        for pos in "QB RB WR TE".split():
            rows = sorted(r["positions"][pos], key=lambda x: x[1])
            pools[pos] = [x[0] for x in rows]
        taken = set()
        picks = []
        n = len(teams)
        tweak = MOCK_TWEAKS[mi]
        for rndno in range(1, 17):
            order = list(range(1, n + 1)) if rndno % 2 == 1 else list(range(n, 0, -1))
            for slot in order:
                persona = PERSONAS[slot - 1]
                pos = tweak.get(slot - 1, {}).get(rndno, persona[rndno - 1])
                pool = [p for p in pools[pos] if p not in taken]
                if not pool:  # fall back to best available at any pos
                    pos = next((q for q in "RB WR TE QB".split() if any(p for p in pools[q] if p not in taken)), None)
                    if not pos: break
                    pool = [p for p in pools[pos] if p not in taken]
                pid = pool[rnd.randrange(max(1, len(pool) // 2))] if mi == 2 else pool[0]
                # vary: mid-round picks sometimes take the 2nd/3rd pool option
                if rndno >= 4 and rnd.random() < 0.35:
                    pid = pool[min(1, len(pool) - 1)]
                taken.add(pid)
                pl = PLAYERS[pid]
                overall = (rndno - 1) * n + (slot if rndno % 2 == 1 else n + 1 - slot)
                picks.append({
                    "slot": slot, "team": slot - 1, "round": rndno, "overall": overall,
                    "pid": pid, "name": pl["n"], "pos": pl["p"],
                    "adp": adp_for(pl, pl["p"]), "pts": pts_for(pid, scoring),
                })
        mocks.append({
            "id": "sample-%d" % (mi + 1), "league": 0,
            "label": "Sample mock %d" % (mi + 1), "format": "snake",
            "mySlot": MY_SLOT, "teams": teams, "picks": picks,
        })
    return mocks

def main():
    args = sys.argv[1:]
    mocks = []
    unmatched_all = []
    for a in args:
        p = Path(a)
        if not p.exists():
            print("skip (missing):", a); continue
        try:
            if p.suffix.lower() == ".csv":
                src = parse_csv(p)
                m, un = build_mock(src)
            else:
                data = json.loads(p.read_text())
                srcs = data if isinstance(data, list) else data.get("mocks", [data])
                for src in srcs:
                    m, un = build_mock(src)
                    mocks.append(m); unmatched_all.extend(un)
            print("ingested:", a)
        except Exception as e:
            print("ERROR %s: %s" % (a, e))
    out = {"generated": "2026-08-25", "sample": False, "mocks": mocks}
    if not args:
        out = {"generated": "2026-08-25", "sample": True, "mocks": gen_sample()}
    (ROOT / "data" / "mocks.json").write_text(json.dumps(out, indent=1))
    n = sum(len(m["picks"]) for m in out["mocks"])
    print("wrote data/mocks.json: %d mocks, %d picks, sample=%s" % (len(out["mocks"]), n, out["sample"]))
    if unmatched_all:
        print("UNMATCHED names:", sorted(set(unmatched_all)))

if __name__ == "__main__":
    main()
