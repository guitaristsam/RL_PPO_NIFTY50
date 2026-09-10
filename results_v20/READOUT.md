# v20 Full Panel Readout — 2026-09-06

## Verdict: CLEAR LOSS vs v18

v18 remains PRODUCTION CHAMPION. v20 does NOT earn a `NEW CHAMPION` line.

---

## Summary

| Metric | v18 (baseline) | v20 (val Sharpe selection) | Delta |
|--------|---------------|---------------------------|-------|
| Mean outperf vs B&H | **-38.78pp** | **-69.10pp** | **-30.3pp worse** |
| Beats B&H count | 2/10 (ITC, ADANIENT) | 2/10 (ADANIENT*, AXISBANK) | 0 (but different stocks!) |
| Average Sharpe | +0.35 | +0.115 | worse |
| Average max DD | -25.3% | -15.07% | better (but due to inactivity) |
| Degenerate stocks | 0 | 1 (ADANIENT, 6 trades) | worse |
| Avg trade count | ~90 | 68.5 | fewer trades |

*ADANIENT v20 win is a DEGENERATE CASH-HOLD: 6 trades over 689 test days,
flagged by the system's `⚠️ DEGENERATE POLICY WARNING`. +22.69pp outperf
is an artifact (policy held cash while B&H fell 21.61%).

---

## Per-Stock Comparison

| Stock | v20 outperf | v18 outperf | Delta | Notes |
|-------|-------------|-------------|-------|-------|
| ADANIENT | +22.69pp | +66.82pp | **-44.1pp ✗** | DEGENERATE (6 trades) — not a real win |
| AXISBANK | +3.98pp | -5.35pp | **+9.3pp ✓** | Genuine improvement |
| TCS | -18.80pp | -8.53pp | **-10.3pp ✗** | Regression |
| HDFCBANK | -30.55pp | -55.20pp | **+24.7pp ✓** | Genuine improvement |
| INFY | -37.09pp | -61.90pp | **+24.8pp ✓** | Genuine improvement |
| RELIANCE | -57.94pp | -41.47pp | **-16.5pp ✗** | Regression |
| SBIN | -86.47pp | -110.02pp | **+23.6pp ✓** | Genuine improvement |
| ITC | -90.83pp | +40.09pp | **-130.9pp ✗** | Lost v18 winner — catastrophic |
| HINDALCO | -183.08pp | -188.18pp | **+5.1pp ✓** | Marginal |
| TATAMOTORS | -212.94pp | -24.10pp | **-188.8pp ✗** | Catastrophic regression |

**Score: 5/10 improved (4 genuine, 1 marginal), 5/10 regressed (2 catastrophic)**

---

## Analysis

### What broke: ITC (-131pp) and TATAMOTORS (-189pp)

v18's two biggest failures on this panel—TATAMOTORS and SBIN—actually improved
under v20. But the two stocks that drove v18's mean outperf upward (ITC +40pp,
ADANIENT +67pp) both regressed catastrophically.

**ITC story:** In v18, ITC's val Sharpe was NEGATIVE (val return was -7%), yet the
best-return checkpoint captured a policy that made +146% on test. Under v20's
Sharpe selection, this policy was rejected in favour of whichever checkpoint had
the highest val Sharpe—which appears to have been a more conservative, low-volatility
checkpoint that traded far more cautiously. With 156 trades but only +15% return,
the Sharpe-selected policy is clearly trading actively but missing the trend.

**TATAMOTORS story:** v18 achieved +229% (outperf -24pp vs B&H +254%). v20 achieves
only +38% (outperf -213pp). Only 20 trades, very low activity — likely the Sharpe
criterion selected a checkpoint that learned to avoid volatility, missing the 250%
bull run entirely.

**Root cause:** Val Sharpe as a checkpoint selector does NOT fix the core problem.
The failure mode (val overfit to high-variance signals) is best characterised as
the policy finding val Sharpe optima through INACTIVITY (low vol = high Sharpe
on val period). This is the same degenerate cash-hold pattern as HDFCBANK v16.
Ironically, the actual inactivity problem already tracked by the code's
`DEGENERATE POLICY WARNING` shows up in ADANIENT but the deeper cases (ITC,
TATAMOTORS) escape detection because they maintain enough trade count.

### What improved (genuine)

AXISBANK, HDFCBANK, INFY, SBIN all improved by 10–25pp. This suggests Sharpe
selection does filter out some overfit val winners. But the catastrophic loss of
ITC and TATAMOTORS (total -320pp) vastly outweighs these gains (+74pp combined).

### Significance

No statistical significance detected:
- 0/10 stocks reach nominal p_boot < 0.05
- 0/10 survive Benjamini-Hochberg FDR at q=0.05
- ADANIENT and AXISBANK appear as "wins" but ADANIENT is degenerate

### vs. Dumb Baselines

| Strategy | Beats B&H | Mean outperf | vs SMA | vs MOM |
|----------|-----------|--------------|--------|--------|
| v20 PPO | 2/10 | -69.10pp | beats SMA on 3/10 | beats MOM on 4/10 |
| SMA20/50 | 1/10 | -50.25pp | — | — |
| MOM126 | 1/10 | -32.56pp | — | — |

PPO v20 is WORSE than both dumb baselines on mean outperformance. Even the
simple 126-day momentum rule beats v20 by ~36pp on average.

---

## Recommendation

v20 (val-Sharpe checkpoint selection) is a net negative. **Do not build on v20.**

Returning to v18 as the PRODUCTION CHAMPION.

**Next actions for run-A routine:**
1. v22 (ensemble seeds, 3×). Reduces variance ~1/√3. Primary target: TATAMOTORS
   and INFY variance — verify whether seed averaging changes the +22pp ADANIENT
   result and catastrophic TATAMOTORS result. ~3h with `python run_panel.py v22 --seeds 3`.
2. After v22: consider deeper diagnostics or follow the FRONTIER NEXT ACTIONS.

---

## v18 Baseline Note

FRONTIER.md states v18 mean outperf = -63.2pp. The actual computed value from
the 10-stock panel (`results/`) is **-38.78pp** (confirmed by v19 READOUT).
The FRONTIER figure likely reflects the full 50-stock sweep rather than the
10-stock panel. `auto-tinker` should propagate the 10-stock figure to FRONTIER.
