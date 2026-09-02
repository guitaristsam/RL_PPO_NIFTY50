# v21 Panel Readout — target-exposure action

**Run date:** 2026-09-01/02 (auto/run-b nightly session)
**Branch:** auto/run-b
**Variant:** Rl_v21.py — target-exposure action (`raw_action ∈ [-1,1]` → `target_frac ∈ [0,1]`)

> NOT A NEW CHAMPION. v21 mean outperf -73.16pp < v18 10-panel recomputed baseline -38.8pp. Variant REJECTED.
>
> FRONTIER.md stored -63.2pp (may reflect a different panel or prior computation). The -38.8pp used here is computed directly from v18 per-stock results on the same 10-stock panel — use this figure for apples-to-apples comparisons.

---

## Summary

| metric | v21 | v18 10-panel (recomputed) |
|--------|-----|--------------------------|
| mean outperf vs B&H | **-73.16pp** | -38.8pp |
| beats B&H count | **1\*/10** | 1/10 |
| avg Sharpe | +0.086 | — |
| avg MaxDD | -20.85% | — |
| avg trade count | **243.7** | ~90 |

\* ADANIENT's "beat" (9 trades, near-degenerate cash-hold) is **not a skill signal** and should not be counted as a genuine B&H-beat. Treating it as void: v21 beats B&H on **0/10** stocks.

**Verdict: v21 is a clear regression from v18 baseline (-34.4pp worse). Not adopted.**

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

1. **v19** (B&H-relative reward) — highest-leverage fix for the root cause. TATAMOTORS lost -262pp while B&H gained +251%; v18's absolute-return reward gave no gradient signal for missing that rally. `reward -= log(close_t/close_{t-1})` adds that signal directly. Run TATAMOTORS + RELIANCE first as a quick diagnostic before the full panel.
2. **v26** (feature reduction 98→22 indicators) — currently being run by auto/run-a. Wait for those results before stacking changes.
3. **v20** (best-by-Sharpe in ValidationCallback) — run after v26 results are in. Targets INFY-style late-training overfit.
4. **v22** (ensemble 3 seeds) — hold until at least one variant beats v18. Requires 3x compute; only worth running on a policy that's already competitive.
5. **v23** — speculative, lowest priority.

The cost-drag lesson: any future variant that changes position-sizing or action space should cap hmax or add a turnover penalty to the reward.

---

## Training curves

Training logs are in `runs/` (TensorBoard). Specific diagnostics were not collected during this nightly run. The key observable is turnover (trades/stock) which already explains the result fully. If the v21 action space is revisited, add a turnover penalty and record std/clip_frac/EV at that time.

---

## Champion status

**v18 remains champion.** v21 mean outperf -73.16pp < v18 10-panel recomputed -38.8pp (Δ = -34.4pp). FRONTIER.md should be updated from -63.2pp to -38.8pp to reflect the recomputed 10-panel figure.
