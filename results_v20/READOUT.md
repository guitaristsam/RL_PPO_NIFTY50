# v20 Full Panel Readout — 2026-09-05

## Verdict: REJECTED — worse than v18 baseline

v18 remains PRODUCTION CHAMPION. v20 (best-by-Sharpe ValidationCallback) mean
outperformance = **-71.58pp vs v18 -38.78pp** (32.8pp worse). Lost both v18 B&H-beating
stocks (ITC, ADANIENT), added degenerate policies.

---

## Summary

| Metric | v18 (baseline) | v20 (best-by-Sharpe) | Delta |
|--------|---------------|----------------------|-------|
| Mean outperf vs B&H | **-38.78pp** | **-71.58pp** | **-32.8pp worse** |
| Beats B&H count (genuine) | 2/10 (ITC, ADANIENT) | 0/10 | -2 winners |
| Average Sharpe | +0.15 | +0.02 | worse |
| Degenerate stocks (<20 trades) | 0 | 2 (ADANIENT 0, TATAMOTORS 5) | worse |
| Avg trade count | ~109 | 94.3 | fewer |

---

## Per-Stock Comparison

| Stock | v20 outperf | v20 Sharpe | v20 Trades | v18 outperf | Delta | Degenerate? |
|-------|-------------|-----------|------------|-------------|-------|-------------|
| RELIANCE | -75.43pp | -0.102 | 117 | -41.47pp | **-33.96pp ✗** | No |
| INFY | -39.50pp | -0.598 | 59 | -61.90pp | **+22.4pp ✓** | No |
| TATAMOTORS | -257.93pp | -0.559 | 5 | -24.10pp | **-233.83pp ✗** | **YES (5 trades)** |
| ITC | -65.99pp | +0.534 | 129 | +40.10pp | **-106.09pp ✗** | No |
| ADANIENT | +21.61pp | 0.000 | 0 | +66.83pp | -45.22pp | **YES (0 trades)** |
| HDFCBANK | -15.91pp | +0.300 | 46 | -55.20pp | **+39.29pp ✓** | No |
| TCS | -12.80pp | -0.207 | 85 | -8.53pp | -4.27pp ✗ | No |
| SBIN | -44.39pp | +0.452 | 98 | -110.02pp | **+65.63pp ✓** | No |
| AXISBANK | -24.74pp | +0.587 | 69 | -5.35pp | -19.39pp ✗ | No |
| HINDALCO | -200.74pp | -0.292 | 181 | -188.18pp | -12.56pp ✗ | No |

**Mean v20 outperf: -71.58pp** (all 10 stocks)  
**Mean v18 outperf: -38.78pp**

### Degenerate count: 2/10
- ADANIENT: 0 trades — pure cash hold. +21.61pp is an artifact.
- TATAMOTORS: 5 trades — near-degenerate. -257.93pp suggests a failed short-cycle trade.

### Genuine improvements (active policies ≥20 trades): 3/8 non-degenerate stocks
INFY (+22.4pp), HDFCBANK (+39.29pp), SBIN (+65.63pp)

### Genuine regressions: 5/8 non-degenerate stocks
RELIANCE (-33.96pp), ITC (-106.09pp), TCS (-4.27pp), AXISBANK (-19.39pp), HINDALCO (-12.56pp)

---

## Failure Analysis: Why Best-by-Sharpe Failed

**Hypothesis tested:** selecting the best val checkpoint by Sharpe instead of raw return
would prevent high-variance lucky-long winners (INFY@200k in v18) from being chosen.

**What actually happened:**

1. **Sharpe selector killed ITC** — ITC was v18's biggest winner (+40pp). In v20,
   the Sharpe selector chose a lower-return checkpoint with a smoother equity curve,
   resulting in -65.99pp. This is the hypothesis's Achilles heel: sometimes the
   high-return checkpoint IS the right policy, not a fluke.

2. **Sharpe selector created degeneracy** — TATAMOTORS (5 trades) and ADANIENT (0 trades)
   both suggest the selector is picking cash-hold checkpoints that have artificially high
   Sharpe ratios (zero volatility = infinite/undefined Sharpe, handled as 0 but still
   preferred when alternates have negative Sharpe).

3. **Partial wins** — HDFCBANK (+39.29pp) and SBIN (+65.63pp) improved significantly.
   The Sharpe metric does useful work on stocks where v18's return-best was selecting
   noisy/lucky checkpoints.

4. **Net loss** — 3 improvements vs 5 regressions (non-degenerate). ITC's -106pp swing
   alone accounts for the bulk of the -32.8pp aggregate deterioration.

**Root cause:** Sharpe-best is penalizing genuine skill (steady compounding) when the
return-best would have been right, and rewarding cash-hold policies (low volatility,
Sharpe ≈ 0) over trading policies with negative Sharpe. The cash-hold corner case
needs explicit filtering (min_val_trades=20 perhaps) to prevent degenerate wins.

**Interaction with the 3-checkpoint constraint:** v20 only chooses among 3 eligible
checkpoints (warmup 100k → evals at 100k/150k/200k). That's very little resolution.
v23 (eval_freq=25k, warmup=150k) gives 3 checkpoints in the 150-200k range — may give
better signal but is a separate experiment.

---

## Statistical Note

- Beats B&H (genuine): 0/10. p_boot < 0.05 expected ~0 by chance.
- No evidence of genuine edge.

---

## Comparison: Run-B Queue Summary

| Variant | Mean outperf | Beats B&H | Status | vs v18 |
|---------|-------------|-----------|--------|--------|
| v18 (baseline) | -38.78pp | 2/10 | CHAMPION | — |
| v21 (target-exposure) | -73.16pp | 1/10 (degen) | REJECTED | -34.4pp worse |
| v19 (B&H-relative reward) | -72.38pp | 0/10 | REJECTED | -33.6pp worse |
| v20 (best-by-Sharpe) | -71.58pp | 0/10 (degen) | REJECTED | -32.8pp worse |
| v23 (warmup=150k) | TBD | TBD | NEXT | — |

---

## Recommendation: v23

v23 (warmup=150k, eval_freq=25k) is the last remaining queue item. It concentrates
all val checkpoints in the 150k-200k range where policies are more converged. This is
a more conservative change than v20 and directly targets the "lucky early checkpoint"
failure mode without changing the val metric (still return-based). Worth running.

After v23, if all queue items are rejected, consider:
- Feature reduction variant (v26 was a bookkeeping artifact — NOT the right approach)
- Architecture changes (smaller LSTM, regularization-on-critic)
- Cross-stock transfer approach (v24 pooled — needs GPU for viability)
