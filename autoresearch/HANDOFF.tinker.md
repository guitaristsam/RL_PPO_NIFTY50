# HANDOFF — auto-tinker session state

**Session start:** 2026-09-01T19:41:10Z

## Current task

FIRST SESSION. Need to:
1. Run baseline calibration at SEED 42/43/44 to establish noise gate.
2. Then run single-variable experiments.

## Progress

- [ ] Calibration seed 42 (baseline)
- [ ] Calibration seed 43
- [ ] Calibration seed 44
- [ ] Set noise gate
- [ ] Experiments

## Next step

Run `python autoresearch/train.py` unmodified (SEED=42) for baseline.

## Gotchas

- Log.md has no measured noise gate yet — all "wins" are unconfirmed until calibration is done.
- Data: RELIANCE, TATAMOTORS, HDFCBANK all present in data/.
- BUDGET_TIMESTEPS=60000 for the proxy runs.
