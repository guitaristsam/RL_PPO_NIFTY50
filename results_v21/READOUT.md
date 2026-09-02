# v21 Panel Readout — target-exposure action

**Run date:** 2026-09-01/02 (auto/run-b nightly session)
**Branch:** auto/run-b
**Variant:** Rl_v21.py — target-exposure action (`raw_action ∈ [-1,1]` → `target_frac ∈ [0,1]`)

> NOT A NEW CHAMPION. v21 mean outperf -73.16pp < v18 baseline -63.2pp. Variant REJECTED.

---

## Summary

| metric | v21 | v18 baseline (FRONTIER) |
|--------|-----|-------------------------|
| mean outperf vs B&H | **-73.16pp** | -63.2pp |
| beats B&H count | **1/10** | 1/10 |
| avg Sharpe | +0.086 | — |
| avg MaxDD | -20.85% | — |
| avg trade count | **243.7** | ~90 |

**Verdict: v21 is a clear regression from v18 baseline. Not adopted.**

---

## Per-stock results vs v18 baseline

| Stock | v21 outperf | v18 outperf | Δ | v21 trades | v18 trades |
|-------|-------------|-------------|---|------------|------------|
| ADANIENT | +25.29pp ✓ | +66.82pp ✓ | **-41.5pp** | 9 (near-degen) | 94 |
| TCS | -11.49pp | -8.53pp | **-2.96pp** | 157 | 90 |
| HDFCBANK | -16.98pp | -55.20pp | **+38.2pp** ↑ | 423 | 90 |
| INFY | -32.04pp | -61.90pp | **+29.9pp** ↑ | 146 | 206 |
| AXISBANK | -37.39pp | -5.35pp | **-32.0pp** | 139 | 74 |
| ITC | -43.64pp | +40.09pp ✓ | **-83.7pp** | 261 | 161 |
| RELIANCE | -61.50pp | -41.47pp | **-20.0pp** | 456 | 51 |
| SBIN | -101.60pp | -110.02pp | **+8.4pp** ↑ | 415 | 162 |
| HINDALCO | -190.56pp | -188.18pp | **-2.4pp** | 205 | 91 |
| TATAMOTORS | -261.65pp | -24.10pp | **-237.5pp** ⚠️ | 226 | 78 |
| **Mean** | **-73.16pp** | **-38.8pp** (10-panel) | **-34.4pp** | **243.7** | **109.7** |

↑ = v21 improves vs v18 (3/10 stocks: HDFCBANK, INFY, SBIN)
⚠️ = catastrophic regression (TATAMOTORS: v21 misses a 251% B&H rally, costs drag to -262pp)

ITC control stock: v18 beat B&H by 40pp; v21 loses to B&H by 44pp. **The v18 B&H-beat did not survive the action-space change.**

---

## Baseline comparisons (dumb strategies)

| strategy | beats B&H | mean outperf | median outperf |
|----------|-----------|--------------|----------------|
| v21 PPO | 1/10 | -73.15pp | -40.51pp |
| SMA20/50 crossover | 1/10 | -50.25pp | -58.02pp |
| MOM126 momentum | 1/10 | -32.56pp | -32.34pp |

**v21 PPO underperforms even SMA crossover (-23pp worse) and momentum (-41pp worse). Coin-flip or worse vs dumb strategies.**

v21 beats SMA on 4/10 stocks; beats MOM on 3/10 stocks.

---

## Statistical significance

All active return tests (PPO − B&H daily):
- 0/10 pass p_boot < 0.05 (nominal)
- 0/10 survive Benjamini-Hochberg FDR
- Three stocks have **statistically significant negative** alpha: TATAMOTORS (p=0.977), HINDALCO (p=0.996), SBIN (p=1.000)
- No evidence of any positive edge

---

## Root cause diagnosis

**Target-exposure action creates excessive turnover.** The `(a+1)/2` mapping means any action ≠ -1 implies active position adjustment. The LSTM continuously churns the portfolio:

- v18 avg trades: ~90/stock
- v21 avg trades: 243.7/stock — **2.7x more turnover**
- Average transaction costs: ₹1,900/stock (19% of ₹10,000 initial capital)

This cost drag destroys returns on trending stocks (TATAMOTORS B&H +251%, HINDALCO +178%) where a simple buy-and-hold would win. v21 spent 19% of capital on friction while missing 250% rallies.

The 3 stocks where v21 improves (INFY, HDFCBANK, SBIN) are ones where the v18 policy was already badly losing. In those cases, any active trading looks better than v18's losing positions. This is false hope — v21 doesn't beat B&H on any of them.

ADANIENT beats B&H (+25.3pp) with just 9 trades — near-degenerate, holding cash during B&H decline. Not a skill signal.

**The advisor's pre-run warning was correct:** "a=0 means 50% exposure, not 'hold' — expect turnover and 0.25%/side cost drag to spike." The cost drag is the kill shot.

---

## Recommended next steps (from queue)

1. **v20** (best-by-Sharpe in ValidationCallback) — directly targets the checkpoint-selection problem. Lower turnover risk than v21 since it only changes which checkpoint is saved, not the action space.
2. **v22** (ensemble 3 seeds) — variance reduction. Requires 3x compute per stock (~30 stocks' worth of training). Best run on a dedicated long session.
3. **v26** (feature reduction 98→22 indicators) — currently being run by auto/run-a. Wait for results before stacking.

The cost-drag lesson: any future variant that changes position-sizing or action space should cap hmax or add a turnover penalty to the reward.

---

## Champion status

**v18 remains champion.** v21 mean outperf -73.16pp < v18 -63.2pp (FRONTIER).
