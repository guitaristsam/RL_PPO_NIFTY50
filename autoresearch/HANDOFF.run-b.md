# HANDOFF — auto-run-B

Last updated: 2026-09-02T03:00:00Z

## Status: SESSION COMPLETE

v21 10-stock panel: DONE. PR opened. Lease deleted. Session ending.

---

## What was done (2026-09-01/02 nightly session)

**Variant:** v21 — target-exposure action (`(a+1)/2 ∈ [0,1]` = capital fraction)

**Result: NOT A NEW CHAMPION. REJECTED.**

| metric | v21 | v18 (10-panel) |
|--------|-----|----------------|
| mean outperf | -73.16pp | -38.8pp |
| beats B&H | 0*/10 | 1/10 |
| avg trades | 243.7 | ~90 |

*ADANIENT's 9-trade beat is near-degenerate cash-hold, not skill.

Root cause: 2.7x more trades → avg ₹1,900 transaction costs = 19% of capital.
TATAMOTORS catastrophic: PPO -10.7% vs B&H +251% → -261.65pp outperf.
ITC control: v18 +40pp → v21 -44pp. Action-space change destroyed the B&H-beat.

## PR

https://github.com/guitaristsam/RL_PPO_NIFTY50/pull/3 (draft, auto/run-b → main)

## Environment setup

- pandas_ta 0.4.71b0 + hma.py patched for Python 3.11
- finrl __init__.py wrapped in try/except
- run_one_v21.py: sets env vars before importing Rl_v21 (module-level RESULTS_DIR)
- run_panel_v21_with_commits.sh: sequential panel runner

## Next recommended experiment

1. **v19** (B&H-relative reward) — highest leverage on trending-stock failure mode
2. Wait for v26 results from run-a first (feature reduction, anti-overfit)
3. v20 (best-by-Sharpe) after v26 results

## Gotchas for next session

- v18 10-panel baseline is -38.8pp (not -63.2pp from old FRONTIER.md)
- FRONTIER.md figure may be stale; recompute from results_v18/ before quoting
- Any future action-space or position-sizing change: cap hmax or add turnover penalty
- v21 models in models_v21/ are NOT committed (gitignored); re-train from Rl_v21.py if needed
