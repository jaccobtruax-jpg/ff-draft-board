# 2026 Draft Board — Fantasy Footballers UDK

Draft-day companion board for Jaccob's two leagues, built on the Fantasy Footballers 2026 Ultimate Draft Kit data.

## What's inside

- **The Board** — FFB rankings with tier bands, search, position tabs, ADP + value + projected points sorting, expert tags (sleeper/breakout/bust/value), rookie badges
- **Intel bar** (top of the board) — who's on the clock, predicted next 7 picks (team · bye · ADP · tier, color-coded gone/borderline/falls), your pick highlighted gold, 🔥 position-run detector, and a Targets row showing whether each of your guys is likely gone before your pick
- **My Team** — roster grid with bye-week chips on every player, bye-cluster warning when 2+ starters share a week, next-pick call with alternatives, positional scarcity meter
- **Draft Context** — pick-by-pick log (sequential real pick numbers; team names auto-fill from the draft order you enter in settings), My Guys list, sleepers/busts/values panels, league notes
- **Player modal** — one-line at-a-glance strip (rank, tier, pts, value vs ADP, ADP, bye, risk, upside) with the long-form FFB outlook + dynasty notes collapsed behind a toggle, so you only expand when you have time to read
- **Two leagues** — toggle in the header; each has its own scoring, roster, draft order, and draft state (saved to localStorage)
- **Scoring** — rankings computed with the FFB UDK engine for 8 systems: STD/HALF/PPR × 4pt/6pt passing TD, plus TE PREM (0.5 PPR WR/RB + 1.0 TE) × 4pt/6pt QB; superflex-aware rankings auto-enable when the league has a SFLEX slot
- **3-minute pick timer** — one tap starts the clock for your turn

## Files

- `index.html` — the app (single page, vanilla JS, no build step)
- `test_harness.html` — in-browser smoke test, **41 checks** (open it, PASS/FAIL list renders)
- `data/board.json` — all player/ranking data (~660KB)
- `build/` — the scripts that scraped the UDK site and built board.json

## League defaults

- Dolphin Fans (League 1) — imported from Sleeper "League of Champs": TE PREM (4pt QB: 0.5 PPR WR/RB + 1.0 TE, 4pt pass TD, INT −1), 10 teams, pick 5, superflex, roster QB1/RB2/WR2/TE1/FLEX2/RBW1/SFLEX1/DST1/K1/BN10/IR3, team "Dolphin fans are gay"
- League 2: TBD — candidate from FFB account: "O.G." (6pt QB, TE premium, QB1/RB2/WR3) or "Leg of bastards" (4pt QB, TE premium, 10 teams)

## Use

Serve over http (e.g. `python3 -m http.server`) — the page fetches `data/board.json` and needs same-origin http. State lives in localStorage per league. Click a player's ✓ to mark drafted (each mark takes the next real pick number), ★ for My Guys. Gear icon opens league settings (name, scoring, roster, team name, draft order). Enter the draft order as comma-separated team names (pick 1 → N) to get team names on predictions and the log; snake reversal is handled automatically.
