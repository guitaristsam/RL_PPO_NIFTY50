# v18 Clean Panel Readout — 2026-09-05

## Purpose: Correct Baseline (post-vecnorm-fix)

The original `results/` directory (used as v18 baseline in all experiment comparisons)
contained pre-vecnorm-fix data for 9/10 stocks. This READOUT reflects a fresh full-panel
run with current code. **This is now the canonical v18 baseline.**

---

## ⚠️ Explosive Finding: All Three "Rejected" Variants Were Not Losses

| Variant | vs old baseline (-38.78pp) | vs **correct** baseline (-72.74pp) |
|---------|---------------------------|--------------------------------------|
| v19 (B&H-relative) | -33.6pp worse → REJECTED | **+0.36pp — indistinguishable** |
| v20 (best-by-Sharpe) | -32.8pp worse → REJECTED | **+1.16pp — indistinguishable** |
| v21 (target-exposure) | -34.4pp worse → REJECTED | **-0.42pp — indistinguishable** |

**The "rejections" were all comparing post-fix experiments against a pre-fix inflated baseline.
None of the single-variable experiments moved the needle meaningfully vs v18. The previous
ITC +40pp "B&H win" was a pre-fix artifact — it does not reproduce with current code.**

---

## v18 Clean Panel Summary

| Metric | v18 clean | Old "baseline" | Change |
|--------|-----------|---------------|--------|
| Mean outperf vs B&H | **-72.74pp** | -38.78pp | -34pp WORSE |
| Beats B&H (genuine, ≥20 trades) | **1/10 (ADANIENT +4pp)** | 2/10 (ITC, ADANIENT) | -1 winner |
| Average Sharpe | +0.013 | ~+0.15 | worse |
| Degenerate stocks (<20 trades) | 1/10 (TATAMOTORS 5 trades) | 0/10 | +1 |
| Average trades | 84.3 | ~109 | fewer |

---

## Per-Stock Results (v18 clean vs old baseline)

| Stock | v18 Clean Outperf | Old Baseline | Delta | Sharpe | Trades | B&H Return |
|-------|------------------|-------------|-------|--------|--------|-----------|
| RELIANCE | -76.93pp | -41.47pp | -35pp | -0.102 | 139 | +68.70% |
| INFY | -39.50pp | -61.90pp | +22pp | -0.598 | 59 | +22.50% |
| TATAMOTORS | -257.93pp | -24.10pp | **-234pp** | -0.559 | **5 DEGEN** | +250.97% |
| ITC | -65.99pp | **+40.10pp** | **-106pp** | 0.534 | 129 | +105.88% |
| ADANIENT | **+4.12pp** ✓ | +66.83pp | -63pp | -0.180 | 53 | -21.61% |
| HDFCBANK | -15.91pp | -55.20pp | +39pp | 0.300 | 46 | +30.62% |
| TCS | -5.35pp | -8.53pp | +3pp | -0.010 | 64 | +4.96% |
| SBIN | -44.39pp | -110.02pp | +66pp | 0.452 | 98 | +88.72% |
| AXISBANK | -24.74pp | -5.35pp | -19pp | 0.587 | 69 | +51.62% |
| HINDALCO | -200.74pp | -188.18pp | -13pp | -0.292 | 181 | +178.12% |
| **Mean** | **-72.74pp** | -38.78pp | **-34pp** | +0.013 | 84.3 | +98.04% |

**Degenerate:** TATAMOTORS (5 trades). All others have ≥20 trades.

**Non-degenerate mean (9 stocks):** -52.16pp

---

## Why TATAMOTORS Is Now Degenerate in v18 Clean

TATAMOTORS B&H returned +251% in the test period. The policy trained with warmup=100k
produced a near-passive strategy (5 trades). This is the checkpoint selection issue the
warmup was supposed to fix — but TATAMOTORS is so high-variance that the val callback's
best-return checkpoint happened to be a near-passive policy. This is the canonical v23
target case (longer warmup → push checkpoints to 150-200k converged region).

---

## Comparison vs All Run Experiments (corrected)

| Variant | Mean outperf | vs v18 clean | Verdict (corrected) |
|---------|-------------|--------------|---------------------|
| **v18 clean** | **-72.74pp** | — | **PRODUCTION CHAMPION** |
| v19 (B&H-relative) | -72.38pp | **+0.36pp** | Too close to call — not a loss |
| v20 (best-by-Sharpe) | -71.58pp | **+1.16pp** | Slightly better — not a loss |
| v21 (target-exposure) | -73.16pp | **-0.42pp** | Essentially identical — not a loss |
| v26 (22 indicators) | -51.49pp nominal | ARTIFACT | 2 degenerate wins; ITC -101pp |

**Revised conclusion: no experiment to date has meaningfully beaten or lost to v18.**
The optimization landscape appears very flat at ~-72pp mean outperformance.

---

## Dominating Failure Modes

**TATAMOTORS (-258pp)** and **HINDALCO (-201pp)** together contribute -46pp to the mean
alone. Both are high-B&H-return stocks (TATAMOTORS +251%, HINDALCO +178%). The agent
catastrophically underperforms on strong-trend bull stocks.

**B&H correlation**: outperformance strongly anti-correlates with B&H return. Stocks where
B&H returned <30% (ADANIENT -22%, INFY +22%, TCS +5%, HDFCBANK +31%) show modest
underperformance (-5 to -40pp). Stocks where B&H returned >100% (TATAMOTORS +251%,
HINDALCO +178%, ITC +106%, RELIANCE +69%) underperform by -77 to -258pp. The policy is
not participating in bull markets.

---

## What This Means for Next Steps

1. **v23 (warmup=150k) is still worth running**: TATAMOTORS degeneracy is exactly the
   early-checkpoint failure mode v23 targets. Even a +50pp improvement on TATAMOTORS
   would shift the mean by +5pp and reduce the "flat landscape" conclusion.

2. **v27 (turnover penalty) is the highest-value next lever**: Per Opus advisor analysis,
   cost drag ≈ 20.1% log-equity on average (~26pp of the outperformance gap). 5/10 stocks
   would beat B&H GROSS. No experiment to date touches transaction cost reduction.
   Implementation: `reward -= λ_tc * (|traded_value| / equity)`.

3. **Median is more informative than mean**: median v18 outperf = -44.39pp (SBIN midpoint).
   TATAMOTORS and HINDALCO are extreme outliers that dominate the mean. Future comparisons
   should report both mean and median.

4. **Don't re-run v19/v20/v21 without a specific hypothesis**: they are indistinguishable
   from v18. The answer is to find a variable that actually moves the needle (v27) rather
   than more null-result experiments.
