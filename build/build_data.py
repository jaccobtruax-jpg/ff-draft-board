#!/usr/bin/env python3
"""Build the ff-draft-board dataset from the FFB UDK site data.
Sources: window.udk.data blob (projections/essentials/tiers/multipliers) + DOM expert lists.
Ports the site's own UdkRankings algorithm faithfully.
"""
import json, re, os, sys, math

BASE = os.path.expanduser('~/ff-draft-board')
RAW = os.path.join(BASE, 'raw')
DATA = os.path.join(BASE, 'data')
os.makedirs(RAW, exist_ok=True)
os.makedirs(DATA, exist_ok=True)

BLOB = json.load(open('/tmp/ffb_sleepers_blob.json'))

def to_f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

# ---------------------------------------------------------------- scoring systems
SCORING = json.load(open('/tmp/scoring_systems.json'))
print('scoring systems:', list(SCORING.keys()))

TIERS = BLOB['tiers']
TOP200_MULT = BLOB['top200_multipliers']
TWOQB_MULT = BLOB['2qb_multipliers']

# ---------------------------------------------------------------- projections -> players
PROJ = BLOB['projections']
ANALYSTS = {'1': 'andy', '2': 'jason', '3': 'mike'}

players = {}  # player_id -> merged record
for row in PROJ:
    pid = row['player_id']
    if pid not in players:
        players[pid] = {
            'id': pid, 'name': row['name'], 'slug': row['slug'], 'pos': row['fantasy_position'],
            'team': row['team'], 'bye': row['bye_week'], 'number': row['number'],
            'headshot': row.get('headshot'), 'adp': to_f(row.get('adp')), 'adp_half_ppr': to_f(row.get('adp_half_ppr')),
            'adp_ppr': to_f(row.get('adp_ppr')), 'adp_2qb': to_f(row.get('adp_2qb')),
            'exp': row.get('experience'), 'analysts': {}
        }
    a = ANALYSTS.get(str(row.get('analyst_id')), 'x')
    players[pid]['analysts'][a] = {
        'pa': row.get('passing_attempts'), 'py': row.get('passing_yards'), 'ptd': row.get('passing_touchdowns'),
        'pc': row.get('passing_completions'), 'int': row.get('interceptions_thrown'),
        'ra': row.get('rushing_attempts'), 'ry': row.get('rushing_yards'), 'rtd': row.get('rushing_touchdowns'),
        'rec': row.get('receptions'), 'rey': row.get('receiving_yards'), 'retd': row.get('receiving_touchdowns'),
        'ret': row.get('receiving_targets'), 'fl': row.get('fumbles_lost'), 'risk': row.get('risk'), 'upside': row.get('upside')
    }

# essentials -> blurbs keyed by player_id (last per analyst wins, prefer non-empty)
blurbs = {}
for k, v in BLOB['essentials'].items():
    pid = v.get('player_id')
    if not pid:
        continue
    entry = blurbs.setdefault(pid, {'blurb': '', 'dynasty_blurb': ''})
    if v.get('blurb'):
        entry['blurb'] = v['blurb']
    if v.get('dynasty_blurb'):
        entry['dynasty_blurb'] = v['dynasty_blurb']

for pid, p in players.items():
    b = blurbs.get(pid, {})
    p['blurb'] = b.get('blurb', '')
    p['dynasty_blurb'] = b.get('dynasty_blurb', '')

# ---------------------------------------------------------------- scoring math
def calc_score(stats, pos, sc):
    n = 0.0
    if pos == 'QB':
        n += (stats.get('py') or 0) / max(sc.get('amtPassingYards', 25), 1) * sc.get('pointsPerAmtPassingYards', 1)
        n += (stats.get('pa') or 0) * sc.get('pointsPerPassingAttempt', 0)
        n += (stats.get('ptd') or 0) * sc.get('pointsPerPassingTouchdown', 4)
        n += (stats.get('pc') or 0) * sc.get('pointsPerPassingCompletion', 0)
        n += (stats.get('int') or 0) * sc.get('pointsPerPassingInterception', -2)
        n += (stats.get('fl') or 0) * sc.get('pointsPerFumbleLost', -2)
        n += (stats.get('ra') or 0) * sc.get('pointsPerRushingAttempt', 0)
        n += (stats.get('ry') or 0) / max(sc.get('amtRushingYards', 10), 1) * sc.get('pointsPerAmtRushingYards', 1)
        n += (stats.get('rtd') or 0) * sc.get('pointsPerRushingTouchdown', 6)
    else:
        ppc = sc.get('pointsPerReceptionRB' if pos == 'RB' else 'pointsPerReceptionTE' if pos == 'TE' else 'pointsPerReceptionWR', 0)
        n += (stats.get('rec') or 0) * ppc
        n += (stats.get('fl') or 0) * sc.get('pointsPerFumbleLost', -2)
        n += (stats.get('ra') or 0) * sc.get('pointsPerRushingAttempt', 0)
        n += (stats.get('ry') or 0) / max(sc.get('amtRushingYards', 10), 1) * sc.get('pointsPerAmtRushingYards', 1)
        n += (stats.get('rtd') or 0) * sc.get('pointsPerRushingTouchdown', 6)
        n += (stats.get('rey') or 0) / max(sc.get('amtReceivingYards', 10), 1) * sc.get('pointsPerAmtReceivingYards', 1)
        n += (stats.get('retd') or 0) * sc.get('pointsPerReceivingTouchdown', 6)
    return n

def avg_proj(p, keys):
    """Average per-analyst stats for the given keys."""
    vals = {k: [] for k in keys}
    for a in ('andy', 'jason', 'mike'):
        st = p['analysts'].get(a)
        if st and (st.get('py') or st.get('rey') or st.get('ry') or st.get('risk')):
            for k in keys:
                v = st.get(k)
                if v is not None:
                    vals[k].append(v)
    out = {}
    for k, v in vals.items():
        out[k] = sum(v) / len(v) if v else 0
    return out

def ppr_cat(sc):
    rb = sc.get('pointsPerReceptionRB', 0)
    return 'STD' if rb < 0.4 else ('HALF' if rb < 0.9 else 'PPR')

def qb_cat(sc):
    pt = sc.get('pointsPerPassingTouchdown', 4)
    return '6PT' if abs(pt - 6.0) < 0.01 else '4PT'

def is_superflex(sc):
    slots = sc.get('rosterSlots') or []
    for slot, n in slots:
        if (slot == 'QB' and n > 1) or (slot == 'SFLEX' and n > 0):
            return True
    return False

def pick_adp(p, sc, sf):
    if sf:
        return p.get('adp_2qb')
    rb = sc.get('pointsPerReceptionRB', 0)
    if abs(rb - 0.5) < 0.01:
        return p.get('adp_half_ppr')
    if abs(rb - 1.0) < 0.01:
        return p.get('adp_ppr')
    return p.get('adp')

def adp_fmt(adp, league_size=12):
    adp = to_f(adp)
    if adp is None or adp <= 0:
        return ''
    r = int(round(adp))
    pick = (r - 1) % league_size + 1
    rnd = (r - 1) // league_size + 1
    return f'{rnd}.{pick:02d}'

def get_tier_mult(settings, analyst, category, pos, tier, key):
    try:
        arr = settings.get(analyst, {}).get(category, {}).get(pos, [])
        idx = max(0, min(tier - 1, len(arr) - 1)) if arr else 0
        return arr[idx] if arr else 1.0
    except Exception:
        return 1.0

def compute_position_rankings(sc, sf):
    """Port of calcPositionRankings for QB/RB/WR/TE."""
    result = {}
    for pos in ('QB', 'RB', 'WR', 'TE'):
        cat = qb_cat(sc) if pos == 'QB' else ppr_cat(sc)
        rows = []
        for pid, p in players.items():
            if p['pos'] != pos:
                continue
            avg = avg_proj(p, ['py', 'pa', 'ptd', 'pc', 'int', 'fl', 'ra', 'ry', 'rtd', 'rec', 'rey', 'retd', 'risk', 'upside'])
            if not (avg['py'] or avg['rey'] or avg['ry'] or avg['risk']):
                continue
            score = calc_score(avg, pos, sc)
            rows.append({
                'id': pid, 'name': p['name'], 'pos': pos, 'team': p['team'], 'bye': p['bye'],
                'adp': pick_adp(p, sc, sf), 'score': score,
                'risk': avg.get('risk', 0), 'upside': avg.get('upside', 0),
                'headshot': p.get('headshot')
            })
        rows.sort(key=lambda r: -r['score'])
        mn = rows[-1]['score'] if rows else 0
        mx = rows[0]['score'] if rows else 0
        span = (mx - mn) or 1
        thresh = TIERS.get(f'{pos}.{cat}', [0])
        prev_tier = 1
        tier_count = 0
        for i, r in enumerate(rows):
            r['rank'] = i + 1
            r['percentile'] = (r['score'] - mn) / span
            tier = 1
            for ti, t in enumerate(thresh):
                if r['percentile'] < t:
                    tier = ti + 1
            if tier != prev_tier or i == 0:
                tier_count += 1
                prev_tier = tier
            r['tier'] = tier
            r['tier_band'] = tier_count
            r['adp_fmt'] = adp_fmt(r['adp'])
        result[pos] = rows
    return result

def compute_top200(pos_rankings, sc, key='top200'):
    """Port of getTierMultiplierRankings: re-score with tier multipliers, sort, rank."""
    mult = TOP200_MULT if key == 'top200' else TWOQB_MULT
    cat_global = ppr_cat(sc)
    rows = []
    for pos in ('QB', 'RB', 'WR', 'TE'):
        for r in pos_rankings[pos]:
            p = players[r['id']]
            scores = []
            for a in ('andy', 'jason', 'mike'):
                st = p['analysts'].get(a)
                if st and (st.get('py') or st.get('rey') or st.get('ry') or st.get('risk')):
                    s = calc_score(st, pos, sc)
                    s *= get_tier_mult(mult, a, cat_global, pos, r['tier'], key)
                    scores.append(s)
            avg = sum(scores) / len(scores) if scores else 0
            row = dict(r)
            row['score'] = avg
            rows.append(row)
    rows.sort(key=lambda x: -x['score'])
    for i, r in enumerate(rows):
        r['rank'] = i + 1
    return rows

def build_rankings(sc_name, sc, sf=False):
    pr = compute_position_rankings(sc, sf)
    top = compute_top200(pr, sc, 'top200' if not sf else '2qb')
    out = {'scoring': sc_name, 'superflex': sf, 'positions': pr, 'top200': top}
    return out

# ---------------------------------------------------------------- rankings for all default systems
rankings_all = {}
for sc_name, sc in SCORING.items():
    sf = is_superflex(sc) or '2QB' in sc_name or '2QB' == sc_name
    rankings_all[sc_name] = build_rankings(sc_name, sc, sf)
    print('computed', sc_name, 'sf=', sf)

json.dump(rankings_all, open(os.path.join(DATA, 'rankings.json'), 'w'))
print('players:', len(players))
json.dump(players, open(os.path.join(DATA, 'players.json'), 'w'))

# ---------------------------------------------------------------- expert lists from DOM
def parse_expert_cards(path, label):
    h = open(path, encoding='utf-8', errors='ignore').read()
    cards = []
    seen = set()
    for m in re.finditer(r'<div class="ffb-blurb--content"[^>]*data-id="(\d+)"[^>]*>(.*?)</div>\s*</div>', h, re.S):
        pid = m.group(1)
        if pid in seen:
            continue
        seen.add(pid)
        inner = m.group(2)
        nm = re.search(r'<a href\s*=\s*"/fantasy/([^/"]+)/">([^<]+)</a>', inner)
        tm = re.search(r'<span class="team">\s*\(?(\w+)\)?\s*([A-Z]{2,3})?\s*</span>', inner)
        pm = re.search(r'<p>(.*?)</p>', inner, re.S)
        name = nm.group(2).strip() if nm else ''
        pos = tm.group(1) if tm else ''
        team = tm.group(2) or ''
        blurb = re.sub(r'<[^>]+>', '', pm.group(1)).strip() if pm else ''
        blurb = blurb.replace('&#8217;', "'").replace('&#8216;', "'").replace('&#8220;', '"').replace('&#8221;', '"').replace('&#8230;', '...')
        if name:
            cards.append({'pid': pid, 'name': name, 'pos': pos, 'team': team, 'blurb': blurb})
    # dedupe by name+pos as extra safety
    uniq = {}
    for c in cards:
        uniq.setdefault(c['name'], c)
    cards = list(uniq.values())
    print(label, 'cards:', len(cards), '|', ', '.join(c['name'] for c in cards[:8]))
    return cards

expert = {}
for slug, label in [('ffb_sleepers', 'sleepers'), ('ffb_udk-expert-lists-breakouts', 'breakouts'),
                    ('ffb_udk-expert-lists-busts', 'busts'), ('ffb_udk-expert-lists-values', 'values')]:
    expert[label] = parse_expert_cards(f'/tmp/{slug}.html', label)
json.dump(expert, open(os.path.join(DATA, 'expert_lists.json'), 'w'))

# ---------------------------------------------------------------- quick summary stats
print()
for sc_name, r in rankings_all.items():
    top = r['top200'][:5]
    print(sc_name, '| top5:', ', '.join(f"{x['name']} {x['score']:.0f}" for x in top))
print()
print('HALF (6pt QB) RB tier1:', [x['name'] for x in rankings_all['HALF (6pt QB)']['positions']['RB'] if x['tier'] == 1])
print('HALF (6pt QB) QB tier1:', [x['name'] for x in rankings_all['HALF (6pt QB)']['positions']['QB'] if x['tier'] == 1])
