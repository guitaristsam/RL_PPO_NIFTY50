# HANDOFF — auto-run-B

Last updated: 2026-09-01T00:00:00Z

## Current task
Running v21 full 10-stock panel (target-exposure action: action∈[0,1]=capital fraction).

## Why v21 (not v22 or v20)
- run-a is doing v26 (feature reduction) — no conflict
- Advisor recommended v21 over v20: v20 only re-ranks 3 checkpoints per stock (ceiling bounded), v21 changes what the policy expresses
- v22 requires 3x compute (30 training runs), not feasible in one session
- v21 has env-math test coverage (test_variant_envs.py) — both tests now PASS

## Environment setup done
- pandas_ta 0.4.71b0 installed; patched hma.py for Python 3.11 compat
- finrl patched: __init__.py wrapped in try/except to skip alpaca/broker imports
- test_variant_envs.py: 2/2 tests pass (v19 reward + v21 action math)
- All deps installed: numpy, pandas, torch, stable-baselines3, sb3-contrib, finrl, matplotlib, scipy, tensorboard

## Progress
Panel: 0/10 stocks done (starting fresh)
Stocks: RELIANCE, INFY, TATAMOTORS, ITC, ADANIENT, HDFCBANK, TCS, SBIN, AXISBANK, HINDALCO

## Running
Command: python run_panel.py v21

## Next steps
1. Run panel; commit+push after each stock
2. After panel: summarize_results, significance, baselines → write results_v21/READOUT.md
3. If v21 beats v18 baseline (-63.2pp, 1/10 beats B&H), mark NEW CHAMPION
4. Open PR to main

## Gotchas for next session
- Expect higher trade counts vs v18 (a=0 = 50% exposure, not hold)
- Watch for cost drag from higher turnover
- ITC control: v18 had +40pp outperf; if that degrades, check if v21 is flipping to idle
- HDFCBANK is likely still a loser — feature-untrainable
- Resume guard: if results_v21/{SYMBOL}/{SYMBOL}_report.txt exists, stock is skipped
