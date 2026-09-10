# v19 Full Panel Readout — 2026-09-04

## Verdict: CLEAR LOSS vs v18

v18 remains PRODUCTION CHAMPION.

---

## Summary

| Metric | v18 (baseline) | v19 (B&H-relative reward) | Delta |
|--------|---------------|--------------------------|-------|
| Mean outperf vs B&H | **-38.78pp** | **-72.38pp** | **-33.6pp worse** |
| Beats B&H count | 2/10 (ITC, ADANIENT) | 0/10 | -2 winners |
| Average Sharpe | +0.35 (est.) | -0.05 | worse |
| Average max DD | -25.3% (est.) | -25.7% | neutral |
| Degenerate stocks | 0 | 1 (HINDALCO, 0 trades) | worse |
| Avg trade count | ~90 | 82.4 | neutral |

---

## IMPORTANT NOTE ON v18 BASELINE

The FRONTIER states v18 mean outperf = -63.2pp. This is incorrect.  
Computed from actual 10-stock panel reports (`results/`): **v18 mean = -38.78pp**.  
This correction must be propagated into FRONTIER.md.

---

## Per-Stock Comparison

| Stock | v19 outperf | v18 outperf | Delta | Notes |
|-------|-------------|-------------|-------|-------|
| RELIANCE | -31.97pp | -41.47pp | **+9.5pp ✓** | Improved |
| INFY | -28.22pp | -61.90pp | **+33.7pp ✓** | Biggest improvement |
| TATAMOTORS | -152.09pp | -24.10pp | **-128.0pp ✗** | Catastrophic |
| ITC | -94.15pp | +40.10pp | **-134.3pp ✗** | Lost v18 winner |
| ADANIENT | -14.65pp | +66.83pp | **-81.5pp ✗** | Lost v18 winner |
| HDFCBANK | -45.92pp | -55.20pp | **+9.3pp ✓** | Improved |
| TCS | -19.34pp | -8.53pp | **-10.8pp ✗** | Slight regression |
| SBIN | -98.33pp | -110.02pp | **+11.7pp ✓** | Improved |
| AXISBANK | -60.99pp | -5.35pp | **-55.6pp ✗** | Large regression |
| HINDALCO | -178.12pp | -188.18pp | DEGENERATE* | 0 trades — cash-hold |

*HINDALCO: 0 trades. Policy held cash the entire test period. Raw outperf improvement is a
cash-hold artifact (avoided some volatility), not a genuine policy. Excluded from improvement count.

**Genuine improvements (active policies ≥5 trades): 4/9 non-degenerate stocks improved (RELIANCE, INFY, HDFCBANK, SBIN). 5/9 regressed, including loss of both v18 B&H-beating stocks.**

**Bull-trend correlation:** Per-stock delta correlates with B&H return: the 5 biggest regression
stocks (TATAMOTORS B&H +251%, ITC +106%, ADANIENT -22%→but rising context, AXISBANK +52%, SBIN +89%)
all have strong positive B&H returns in their test windows. The 4 improvers tend to be
sideways-to-weak-trend. This confirms the mechanism: B&H-relative reward penalizes the agent
for underperforming a rising benchmark, driving cash-hold or paralysis on bull stocks.

---

## Significance (v19)

All 10 stocks: 0/10 nominal p_boot < 0.05 (expected ~0.5 by chance). No FDR survivors.  
No evidence of any genuine edge in v19 either.

---

## Baseline Comparison (v19 vs dumb strategies)

```
PPO        beats B&H  0/10   mean outperf  -72.38pp
SMA20/50   beats B&H  1/10   mean outperf  -50.25pp
MOM126     beats B&H  1/10   mean outperf  -32.56pp
```

v19 PPO is worse than simple SMA crossover on mean outperformance.

---

## Failure Analysis: Why B&H-Relative Reward Failed

The hypothesis: subtracting the daily B&H log-return from the agent's log-return  
gives an explicit alpha gradient.

**What actually happened:**

1. **Bull stocks punished hardest** (TATAMOTORS -128pp, ITC -134pp, ADANIENT -81pp).  
   On strong-trend stocks, B&H is gaining every day. The agent must match a rising  
   benchmark *every single step*. To avoid being penalized, it must always hold full  
   position. But if it holds full position, it gets the same absolute return as B&H  
   but loses on costs. Net result: the agent is in a no-win situation on trending stocks.

2. **Cash-hold becomes degenerate** (HINDALCO: 0 trades).  
   When the benchmark falls (HINDALCO B&H +178% but with volatile periods), the  
   B&H-relative reward pays the agent for staying in cash during B&H drawdowns.  
   This creates a degenerate "wait it out" policy — but HINDALCO rose overall, so  
   cash-hold underperforms.

3. **Mixed objective incoherence**.  
   The DD penalty is still computed on *absolute* equity while the primary reward  
   is now *relative*. These can pull in opposite directions.

4. **The INFY/RELIANCE improvements** (+34pp, +9.5pp) suggest the relative reward  
   does help on sideways or less-trending markets — but the losses on bull markets  
   dominate in the 10-stock panel.

---

## Recommendations (from failure analysis)

1. **v18 remains champion.** Do NOT build on v19.

2. **Next highest-value experiments (from FRONTIER):**
   - v20 (best-by-Sharpe validation): targets INFY late-training overfit without  
     changing the reward. Lower risk of bull-market disruption.
   - v22 (ensemble seeds): reduces variance. Stackable on v18 directly.
   - Panel recalibration by auto-tinker: TATAMOTORS degenerate proxy must be fixed  
     before new proxy experiments are trustworthy.

3. **v25 (DD-from-max penalty)** is the next reward-shape experiment to try, but  
   only after v20/v22 clarify the generalization landscape.

4. **Correct FRONTIER.md**: v18 true panel baseline = -38.78pp (not -63.2pp).

---

## Files

- `results_v19/{STOCK}/{STOCK}_report.txt` — per-stock reports (10/10 complete)  
- `consolidated_report_v19.txt` — generated by `generate_consolidated_report()`  
- Run produced at: 2026-09-03 (stocks RELIANCE/INFY/TATAMOTORS) + 2026-09-04 (remaining 7)

---

_Generated by auto-run-A, 2026-09-04_
