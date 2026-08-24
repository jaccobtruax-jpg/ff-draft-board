# 2026 Draft Board — Fantasy Footballers UDK

Draft-day companion board for Jaccob's two leagues, built on the Fantasy Footballers 2026 Ultimate Draft Kit data.

## What's inside

- **The Board** — FFB rankings with tier bands, search, position tabs, ADP + value + projected points sorting, expert tags (sleeper/breakout/bust/value), rookie badges
- **My Team** — roster grid, next-pick call with alternatives, positional scarcity meter
- **Draft Context** — pick-by-pick log, My Guys list, sleepers/busts/values panels, league notes
- **Two leagues** — toggle in the header; each has its own scoring, roster, and draft state (saved to localStorage)
- **Scoring** — rankings computed with the FFB UDK engine for 8 systems: STD/HALF/PPR × 4pt/6pt passing TD, plus TE PREM (0.5 PPR WR/RB + 1.0 TE) × 4pt/6pt QB; superflex-aware rankings auto-enable when the league has a SFLEX slot

## Files

- `index.html` — the app (single page, vanilla JS, no build step)
- `test_harness.html` — in-browser smoke test (open it, PASS/FAIL list renders)
- `data/board.json` — all player/ranking data (~660KB)
- `build/` — the scripts that scraped the UDK site and built board.json

## League defaults

- Dolphin Fans (League 1) — imported from Sleeper "League of Champs": TE PREM (4pt QB: 0.5 PPR WR/RB + 1.0 TE, 4pt pass TD, INT −1), 10 teams, pick 5, superflex, roster QB1/RB2/WR2/TE1/FLEX2/RBW1/SFLEX1/DST1/K1/BN10/IR3, team "Dolphin fans are gay"
- League 2: half PPR, 6pt pass TD, 12 teams (roster TBD — candidate from FFB account: "O.G." TE PREM 6pt QB, QB1/RB2/WR3/TE1/FLEX1/DST1/K1/BN8/IR2)

## Use

Serve over http (e.g. `python3 -m http.server`) — the page fetches `data/board.json` and needs same-origin http. State lives in localStorage per league. Click a player's ✓ to mark drafted, ★ for My Guys. Gear icon opens league settings (name, scoring, roster, team name).
