# 2026 Draft Board — Fantasy Footballers UDK

Draft-day companion board for Jaccob's two leagues, built on the Fantasy Footballers 2026 Ultimate Draft Kit data.

## What's inside

- **The Board** — FFB rankings with tier bands, search, position tabs, ADP + value + projected points sorting, expert tags (sleeper/breakout/bust/value), rookie badges
- **My Team** — roster grid, next-pick call with alternatives, positional scarcity meter
- **Draft Context** — pick-by-pick log, My Guys list, sleepers/busts/values panels, league notes
- **Two leagues** — toggle in the header; each has its own scoring, roster, and draft state (saved to localStorage)
- **Scoring** — rankings computed with the FFB UDK engine for 6 systems: STD/HALF/PPR × 4pt/6pt passing TD

## Files

- `index.html` — the app (single page, vanilla JS, no build step)
- `test_harness.html` — in-browser smoke test (open it, PASS/FAIL list renders)
- `data/board.json` — all player/ranking data (~660KB)
- `build/` — the scripts that scraped the UDK site and built board.json

## League defaults

- League 1: half PPR, 6pt pass TD, 12 teams, pick 5, roster 1/2/2/1/1/1/1/6
- League 2: PPR, 6pt pass TD (roster TBD)

## Use

Serve over http (e.g. `python3 -m http.server`) — the page fetches `data/board.json` and needs same-origin http. State lives in localStorage per league. Click a player's ✓ to mark drafted, ★ for My Guys. Gear icon opens league settings (name, scoring, roster, team name).
