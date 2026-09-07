# v19 Full 10-Stock Panel — READOUT

**Variant:** v19 — B&H-relative reward  
**Run date:** 2026-09-02/03 (auto/run-b)  
**Status:** REJECTED — worse than v18 baseline

---

## Verdict vs v18 Baseline

| Metric | v18 baseline | v19 B&H-relative | Δ |
|---|---|---|---|
| Mean outperformance vs B&H | −63.2pp | **−71.92pp** | −8.7pp (worse) |
| Beats B&H count | 1/10 | 1/10 | no change |
| Avg Sharpe | ~+0.15 | +0.048 | worse |
| Degenerate stocks (< 5 trades) | 1/10 | 1/10 (HINDALCO, 0 trades) | same |

**v19 does NOT beat the current champion (v18 at −63.2pp).** No RATCHET update.

---

## Per-Stock Results

| Stock | v19 PPO | v19 B&H | v19 Outperf | v18 Outperf | Δ vs v18 | Sharpe | DD | Trades | Notes |
|---|---|---|---|---|---|---|---|---|---|
| ADANIENT | −20.48% | −21.61% | **+1.13pp** | +66.83pp | −65.7pp | −0.179 | −63.7% | 60 | REGRESSION: v18 was +66.8pp |
| TCS | −12.04% | +4.96% | −17.00pp | −8.53pp | −8.5pp | −0.324 | −22.4% | 113 | regression |
| HDFCBANK | +10.36% | +30.62% | −20.26pp | −55.20pp | +34.9pp | +0.155 | −19.5% | 186 | apparent improvement |
| INFY | +2.07% | +22.50% | −20.43pp | (est. ~−62pp) | better | +0.025 | −38.7% | 164 | |
| AXISBANK | +17.98% | +51.62% | −33.64pp | n/a | n/a | +0.391 | −22.4% | 93 | |
| RELIANCE | −5.69% | +68.70% | −74.39pp | −36.89pp | −37.5pp | −0.068 | −33.3% | 116 | regression |
| ITC | +4.21% | +105.88% | **−101.67pp** | +40.09pp | −141.8pp | +0.064 | −30.1% | 149 | SEVERE REGRESSION — ITC was the flagship v18 win |
| SBIN | −14.49% | +88.72% | −103.21pp | n/a | n/a | −0.525 | −20.4% | 68 | |
| TATAMOTORS | +79.36% | +250.97% | −171.61pp | −24.10pp | −147.5pp | +0.944 | −17.2% | 118 | severe regression |
| HINDALCO | 0.00% | +178.12% | −178.12pp | n/a | n/a | 0.000 | 0.0% | 0 | **DEGENERATE: 0 trades** |

---

## Statistical Analysis

- **Significance:** 0/10 nominal p_boot < 0.05; 0/10 survive BH-FDR at q=0.05. No statistical edge.  
- **vs SMA20/50:** PPO beats SMA on 1/10 (mean PPO −71.9pp vs SMA −50.3pp). PPO loses.  
- **vs MOM126:** PPO beats MOM on 4/10 (mean PPO −71.9pp vs MOM −32.6pp). PPO loses badly.

---

## Diagnosis — Why v19 Failed

The B&H-relative reward (`clip((log(eq_t/eq_{t-1}) - log(close_t/close_{t-1})) * 100, -10, 10)`) had the following failure modes:

1. **ITC catastrophic regression (−101pp vs v18 +40pp):** The v18 ITC win relied on disciplined holds through a volatile val period. The B&H-relative reward makes holding a rising stock during a bull run *worse* than doing nothing (reward = 0 for matching B&H). This removed the incentive to stay invested — the policy instead traded frequently and gave up the trend.

2. **HINDALCO degenerate (0 trades):** The relative reward may create a "sit in cash during bull runs" Nash equilibrium: during a strong B&H uptrend, the agent can never gain positive relative reward by holding. The easiest path to non-negative reward is cash-hold (both B&H and PPO return zero when cash).

3. **TATAMOTORS severe regression (−171pp vs B&H +251%):** Same mechanism — strong bull trend stocks are penalized by definition when the policy tries to participate.

4. **ADANIENT apparent win (+1.13pp):** ADANIENT's B&H was −21.6% (Hindenburg crash) so B&H-relative reward accidentally helped this one stock where B&H lost.

**Root cause:** The B&H-relative reward penalizes the agent for participating in bull markets, creating incentives toward cash-hoarding on trending stocks. The absolute log-return reward (v18) is better-aligned with wealth creation, and early stopping already addresses the B&H-underperformance problem via validation selection.

---

## Conclusion

**VERDICT: REJECTED.**  
v19 (B&H-relative reward) is definitively worse than v18 on this panel: −71.92pp vs −63.2pp mean outperformance, with catastrophic regressions on v18's two best stocks (ITC −141pp swing, ADANIENT −65pp swing).

**The B&H-relative reward hypothesis is falsified.**

**Next:** v20 (best-by-Sharpe in ValidationCallback) — targets the INFY-style high-variance overfit via a different mechanism (risk-adjusted checkpoint selection, not reward reshaping). This is now the highest-value unrun item in the queue.
