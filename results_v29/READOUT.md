# v29 Full 10-Stock Panel — READOUT

**Variant:** v29 — DD penalty removed (lambda=0, pure log-return reward)  
**Run date:** 2026-09-06/07 (auto/run-b)  
**Status:** IN PROGRESS

---

## Hypothesis

v18's drawdown penalty (lambda=1.0) makes holding equities negative-EV in the
reward signal:
- Mean equity reward per step: +0.046 units
- Mean DD penalty per step: -0.059 units
- Net drift of holding: **-0.013 units/step** (cash = 0.0)

The agent rationally prefers cash, resulting in ~40% average realized exposure.
This drives ~47pp of the 73pp outperformance gap (the "beta gap"), with only
~26pp attributable to transaction costs.

v29 removes the DD penalty entirely (lambda=0). This is v9's pure log-return
reward combined with v18's warmup/validation machinery.

---

## Verdict vs v18 Baseline

[TO BE FILLED AFTER PANEL COMPLETES]

| Metric | v18 baseline | v29 DD-removed | Δ |
|---|---|---|---|
| Mean outperformance vs B&H | −72.74pp | TBD | TBD |
| Median outperformance vs B&H | −41.95pp | TBD | TBD |
| Beats B&H count | 1/10 | TBD | TBD |
| Avg Sharpe | +0.013 | TBD | TBD |
| Degenerate stocks (<5 trades) | 1/10 | TBD | TBD |
| Mean exposure (if computed) | 40.3% | TBD | TBD |

---

## Per-Stock Results

[TO BE FILLED]

---

## Diagnostics

**Key questions to answer:**
1. Does removing lambda raise mean realized exposure above 40%?
2. Does TATAMOTORS recover (was 5 degenerate trades in v18)?
3. Does ITC recover (was -65.99pp in v18, +40pp in v16)?
4. Does median outperformance improve (mean dominated by TATAMOTORS/HINDALCO outliers)?

---

## Statistical Analysis

[TO BE FILLED AFTER significance.py runs]

---

## Baseline Comparison (SMA/MOM)

[TO BE FILLED AFTER baselines.py runs]
