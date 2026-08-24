#!/usr/bin/env python3
"""Extract rookie cards, injury report, and season-context notes from fetched UDK pages."""
import re, json, os

BASE = os.path.expanduser('~/ff-draft-board')
DATA = os.path.join(BASE, 'data')

def blurb_cards(path):
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
        for a, b in [('&#8217;', "'"), ('&#8216;', "'"), ('&#8220;', '"'), ('&#8221;', '"'), ('&#8230;', '...'), ('&#8211;', '-')]:
            blurb = blurb.replace(a, b)
        if name:
            cards.append({'pid': pid, 'name': name, 'pos': pos, 'team': team, 'blurb': blurb})
    uniq = {}
    for c in cards:
        uniq.setdefault(c['name'], c)
    return list(uniq.values())

def main_text(path):
    h = open(path, encoding='utf-8', errors='ignore').read()
    m = re.search(r'<main[^>]*>(.*?)</main>', h, re.S)
    body = m.group(1) if m else h
    body = re.sub(r'<script.*?</script>', '', body, flags=re.S)
    body = re.sub(r'<style.*?</style>', '', body, flags=re.S)
    text = re.sub(r'<[^>]+>', ' ', body)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# rookies
rookies = blurb_cards('/tmp/ffb_udk-rookie-report.html')
json.dump(rookies, open(os.path.join(DATA, 'rookies.json'), 'w'), ensure_ascii=False)
print('rookies:', len(rookies))

# injury report: split text into per-player paragraphs
inj_text = main_text('/tmp/ffb_udk-injury-report.html')
# find start of actual report (after intro); paragraphs are player-name led
paras = [p.strip() for p in inj_text.split('. ') if p.strip()]
# heuristic: find segments that look like player sections (name + position)
segments = re.split(r'(?=(?:[A-Z][a-z]+ ){1,3}(?:QB|RB|WR|TE|K|D/ST|DL|LB|CB|S)\b)', inj_text)
clean = []
for s in segments:
    s = s.strip()
    if len(s) > 80:
        clean.append(s)
json.dump({'raw': inj_text[:60000]}, open(os.path.join(DATA, 'injury.json'), 'w'), ensure_ascii=False)
print('injury text chars:', len(inj_text))

# context notes: free agency, coaching changes, nfl draft offense
notes = {}
for f, key in [('ffb_udk-free-agency-review', 'free_agency'), ('ffb_udk-coaching-changes', 'coaching'), ('ffb_udk-nfl-draft-offense', 'draft_offense')]:
    t = main_text(f'/tmp/{f}.html')
    notes[key] = t[:20000]
    print(key, 'text chars:', len(t))
json.dump(notes, open(os.path.join(DATA, 'context_notes.json'), 'w'), ensure_ascii=False)

# strength of schedule: check for structured data
sos = main_text('/tmp/ffb_udk-strength-of-schedule_.html')
print('sos text chars:', len(sos), '| sample:', sos[:400])
