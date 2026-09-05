# v18 Clean Panel Readout — 2026-09-05

## Purpose: Correct Baseline

The original `results/` directory (v18 baseline used for all experiment comparisons)
contains pre-vecnorm-fix data for 9/10 stocks. This READOUT reflects a fresh
full-panel run with current code on branch auto/run-b.

**This is now the canonical v18 baseline for all future comparisons.**

---

## ⚠️ Critical Finding: Old Baseline Was Inflated

| Stock | Old baseline | This run | Delta | Note |
|-------|-------------|----------|-------|------|
| RELIANCE | -41.47pp | -76.93pp | -35pp | Much worse post-fix |
| INFY | -61.90pp | -39.50pp | +22pp | Better post-fix |
| ITC | +40.10pp | -65.99pp | -106pp | **NOT a B&H win** |
| ADANIENT | +66.83pp | +4.12pp | -63pp | Still beats B&H (B&H -21%) |
| TATAMOTORS | -24.10pp | TBD | — | pending |
| HDFCBANK | -55.20pp | TBD | — | pending |
| TCS | -8.53pp | TBD | — | pending |
| SBIN | -110.02pp | TBD | — | pending |
| AXISBANK | -5.35pp | TBD | — | pending |
| HINDALCO | -188.18pp | TBD | — | pending |

---

## Per-Stock Results (v18 clean)

| Stock | PPO Return | B&H Return | Outperf | Sharpe | Trades | Degenerate? |
|-------|-----------|-----------|---------|--------|--------|-------------|
| RELIANCE | TBD | 68.70% | -76.93pp | -0.102 | 139 | No |
| INFY | TBD | TBD | -39.50pp | TBD | 59 | No |
| TATAMOTORS | TBD | TBD | TBD | TBD | TBD | ? |
| ITC | TBD | 105.88% | -65.99pp | 0.534 | 129 | No |
| ADANIENT | TBD | -21.61% | +4.12pp | -0.180 | 53 | No |
| HDFCBANK | TBD | TBD | TBD | TBD | TBD | ? |
| TCS | TBD | TBD | TBD | TBD | TBD | ? |
| SBIN | TBD | TBD | TBD | TBD | TBD | ? |
| AXISBANK | TBD | TBD | TBD | TBD | TBD | ? |
| HINDALCO | TBD | TBD | TBD | TBD | TBD | ? |

_Panel still running as of this draft — will be updated when complete._

---

## Preliminary Assessment

**ITC's +40pp result — the primary "PPO beats B&H" achievement — does NOT reproduce.**
ADANIENT still beats B&H but by only +4pp on a down market (B&H -22%).

The true v18 mean outperformance is likely in the range of **-65 to -80pp** once all 10
stocks are collected, significantly worse than the -38.78pp previously cited.

**Implication for prior experiments:**
- v19 (-72pp), v20 (-71pp), v21 (-73pp) may all be closer to the correct v18 baseline
  than the -38pp gap suggested. Re-ranking needed once complete.

---

## New Baseline Summary (to be computed when panel complete)

| Metric | v18 clean |
|--------|-----------|
| Mean outperf vs B&H | TBD |
| Beats B&H (genuine) | ≥1/10 (ADANIENT +4pp) |
| Average Sharpe | TBD |
| Degenerate stocks | TBD |

---

## Recommendations

1. Update FRONTIER.md champion entry to use this clean baseline.
2. Re-evaluate v19/v20/v21 rejections against clean v18 baseline.
3. Consider v27 (turnover penalty) as next experiment — advisor-identified as highest-
   value lever (cost drag = ~26pp of the underperformance gap).
