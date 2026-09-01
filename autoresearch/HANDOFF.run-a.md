# HANDOFF — auto-run-A

Last updated: 2026-09-01

## Current task
Running v26 full 10-stock panel (feature reduction: 98→22 indicators, obs 101→25 dims).

## Progress
- 0/10 stocks done (starting fresh)
- Next: run `python run_panel.py v26`

## Context
- Branch: auto/run-a (fresh from main, no prior results)
- Champion: v18 (mean outperf -63.2pp, 1/10 beats B&H)
- Queue: v26 first, then v22
- No CANDIDATES pending

## Gotchas
- run_panel.py handles the 10-stock panel; use it
- Resume guard: if {SYMBOL}_report.txt exists, stock is skipped automatically
