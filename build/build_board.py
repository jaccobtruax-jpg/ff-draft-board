#!/usr/bin/env python3
"""Build compact board.json for the draft page: players + rankings (6 scoring systems) + expert tags + rookies + auction values."""
import json, os, math

BASE = os.path.expanduser('~/ff-draft-board')
DATA = os.path.join(BASE, 'data')

players = json.load(open(os.path.join(DATA, 'players.json')))
rankings = json.load(open(os.path.join(DATA, 'rankings.json')))
expert = json.load(open(os.path.join(DATA, 'expert_lists.json')))
rookies = json.load(open(os.path.join(DATA, 'rookies.json')))
injury = json.load(open(os.path.join(DATA, 'injury.json')))
notes = json.load(open(os.path.join(DATA, 'context_notes.json')))

# ---- expert tags: player_id -> tag name + blurb (expert pages' cards carry the blurb)
tags = {}   # pid -> {'sleeper': blurb, ...}
tag_order = {'sleepers': 'sleeper', 'breakouts': 'breakout', 'busts': 'bust', 'values': 'value'}
for list_key, tag in tag_order.items():
    for c in expert.get(list_key, []):
        tags.setdefault(c['pid'], {})[tag] = c.get('blurb', '')

rookie_by_pid = {}
for r in rookies:
    rookie_by_pid[r['pid']] = r.get('blurb', '')

# ---- compact players
P = {}
for pid, p in players.items():
    anal = p.get('analysts', {})
    def avg(k):
        vals = []
        for a in anal.values():
            v = a.get(k)
            if v is not None:
                try:
                    vals.append(float(v))
                except (TypeError, ValueError):
                    pass
        return round(sum(vals) / len(vals), 1) if vals else None
    proj = {}
    if p['pos'] == 'QB':
        for k, lbl in [('pa', 'pa'), ('py', 'py'), ('ptd', 'ptd'), ('pc', 'pc'), ('int', 'int'), ('ra', 'ra'), ('ry', 'ry'), ('rtd', 'rtd'), ('fl', 'fl')]:
            v = avg(k)
            if v is not None:
                proj[lbl] = v
    else:
        for k, lbl in [('ra', 'ra'), ('ry', 'ry'), ('rtd', 'rtd'), ('rec', 'rec'), ('rey', 'rey'), ('retd', 'retd'), ('ret', 'ret'), ('fl', 'fl')]:
            v = avg(k)
            if v is not None:
                proj[lbl] = v
    hs = p.get('headshot') or ''
    hs = hs.replace('\\\\', '/').replace('\\/', '/')
    P[pid] = {
        'n': p['name'], 't': p['team'], 'b': p.get('bye'), 'p': p['pos'],
        'adp': p.get('adp'), 'adp_h': p.get('adp_half_ppr'), 'adp_p': p.get('adp_ppr'), 'adp_q': p.get('adp_2qb'),
        'risk': avg('risk'), 'up': avg('upside'),
        'blurb': p.get('blurb', '')[:700], 'dyn': p.get('dynasty_blurb', '')[:500],
        'proj': proj, 'tags': tags.get(pid, {}), 'rb': rookie_by_pid.get(pid, '')
    }

# ---- auction values per scoring system (port of calcAuctionValues)
def auction_values(sc_name, sc, pos_rankings, team_comp, league_size=12, budget=200):
    # replacement points: waiver = starters*teams + flex/2 ... simplified per original
    counts = {}
    for slot, n in team_comp:
        counts[slot] = counts.get(slot, 0) + n
    repl = {}
    for pos in ('QB', 'RB', 'WR', 'TE'):
        n_teams = league_size
        if pos == 'QB':
            repl[pos] = counts.get('QB', 1) * n_teams + n_teams * counts.get('BN', 6) * counts.get('QB', 1) / (counts.get('QB', 1) + counts.get('RB', 2) + counts.get('WR', 2) + counts.get('FLEX', 1) + counts.get('TE', 1)) if counts.get('QB', 1) > 1 else counts.get('QB', 1) * n_teams + 1
        elif pos in ('RB', 'WR'):
            repl[pos] = counts.get(pos, 2) * n_teams + n_teams * counts.get('FLEX', 1) / 2 + 1
        else:
            repl[pos] = counts.get(pos, 1) * n_teams + 1
    rows = {}
    for pos in ('QB', 'RB', 'WR', 'TE'):
        rl = pos_rankings[pos]
        idx = min(len(rl) - 1, max(0, int(repl[pos]) - 1))
        repl_pts = rl[idx]['score'] if idx < len(rl) else 0
        par_total = 0
        vals = []
        for r in rl:
            if r['score'] <= repl_pts:
                vals.append({'id': r['id'], 'v': 0})
                continue
            par = r['score'] - repl_pts
            risk_adj = par * (1 + abs(5 - r['risk']) ** 2 / 100 * (1 if 5 - r['risk'] >= 0 else -1))
            vals.append({'id': r['id'], 'v': risk_adj})
            par_total += risk_adj
        for v in vals:
            v['v'] = max(1, round(budget * v['v'] / par_total)) if par_total else 1
        rows[pos] = vals
    return rows

DEFAULT_COMP = [['QB', 1], ['RB', 2], ['WR', 2], ['TE', 1], ['FLEX', 1], ['D', 1], ['K', 1], ['BN', 6]]

# ---- per-scoring-system team composition + league size (from the league's own rosterSlots)
SCORING = json.load(open('/tmp/scoring_systems.json'))

def comp_from_slots(slots):
    counts = {}
    for slot, n in (slots or []):
        s = str(slot).upper()
        if s in ('RB/WR',):
            s = 'FLEX'
        elif s in ('SFLEX', 'SUPERFLEX'):
            s = 'QB'
        elif s in ('TX', 'IR', 'BENCH'):
            continue
        counts[s] = counts.get(s, 0) + n
    order = ['QB', 'RB', 'WR', 'TE', 'FLEX', 'D', 'K', 'BN']
    return [[p, counts.get(p, 0)] for p in order if counts.get(p, 0)]

# ---- compact rankings
R = {}
for sc_name, r in rankings.items():
    sc_cfg = SCORING.get(sc_name, {})
    comp = comp_from_slots(sc_cfg.get('rosterSlots')) or DEFAULT_COMP
    lsize = sc_cfg.get('leagueSize', 12)
    entry = {'positions': {}, 'top200': [], 'auction': {}}
    for pos in ('QB', 'RB', 'WR', 'TE'):
        entry['positions'][pos] = [[x['id'], x['rank'], round(x['score'], 1), x['tier'], x['tier_band'], x['adp_fmt']] for x in r['positions'][pos]]
    entry['top200'] = [[x['id'], x['rank'], round(x['score'], 1), x['tier']] for x in r['top200']]
    entry['auction'] = {pos: [[x['id'], x['v']] for x in auction_values(sc_name, sc_cfg, r['positions'], comp, league_size=lsize)[pos]] for pos in ('QB', 'RB', 'WR', 'TE')}
    R[sc_name] = entry

board = {
    'meta': {'season': '2026', 'source': 'Fantasy Footballers Ultimate Draft Kit 2026', 'updated': '2026-08-25'},
    'players': P,
    'rankings': R,
    'rookies': [{'id': x['pid'], 'n': x['name'], 'p': x['pos'], 't': x['team']} for x in rookies],
    'injury_text': injury.get('raw', '')[:50000],
    'notes': notes
}
out = os.path.join(DATA, 'board.json')
json.dump(board, open(out, 'w'), ensure_ascii=False)
print('board.json bytes:', os.path.getsize(out))
print('players:', len(P))
print('scoring systems:', list(R.keys()))
# sanity: check a few
pid = next(iter(P))
print('sample player:', P[pid]['n'], P[pid]['p'], P[pid]['t'])
for sc_name in list(R.keys())[:2]:
    print(sc_name, 'QB rows:', len(R[sc_name]['positions']['QB']), 'top200:', len(R[sc_name]['top200']))
    print('  RB #1:', R[sc_name]['positions']['RB'][0])
