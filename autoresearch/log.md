# autoresearch experiment log

Newest first. One row per experiment. `mean_val_outperf_pp` is the objective
(higher is better); `test` is report-only. Keep a change only if val beats the
current best by ≥ +**60.4 pp** (calibrated gate). See `program.md`.

## Noise gate calibration (2026-09-01)

Baseline (v18 defaults, BUDGET=60k, panel=RELIANCE/TATAMOTORS/HDFCBANK) at three seeds:

| seed | RELIANCE val | TATAMOTORS val | HDFCBANK val | mean_val_outperf_pp |
|---|---|---|---|---|
| 42 | -250.23pp | +177.13pp | -153.55pp | **-75.552** |
| 43 | -249.18pp | -13.26pp | -139.97pp | -134.135 |
| 44 | -244.26pp | -10.74pp | -96.85pp | -117.284 |

- stdev([-75.55, -134.14, -117.28]) = 30.2pp
- **Gate = max(3.0pp, 2 × 30.2pp) = 60.4pp**
- Baseline (SEED=42) = **-75.552pp** → must beat **-15.2pp** to keep

Note: TATAMOTORS seed=42 has +177pp val due to B&H=-55.75% (bear market in val period);
likely a degenerate cash-hold. Seeds 43/44 show TATAMOTORS around -10 to -13pp — more realistic.
This inflates seed-42 baseline, making the gate harder to clear on the mean.

| # | date (UTC) | change (one variable) | mean_val_outperf_pp | test | kept? | commit |
|---|---|---|---|---|---|---|
| 1 | 2026-09-01 | INDICATORS: 106→22 (v26 curated set: 7 trend, 7 momentum, 4 volatility, 3 volume, 1 return) | **-7.855** | -51.637 | **KEPT** (+67.7pp vs baseline, beats 60.4pp gate) | TBD |
| 0 | 2026-09-01 | baseline (v18 defaults, BUDGET=60k, 3-stock panel, SEED=42) | -75.552 | -96.192 | baseline | — |

