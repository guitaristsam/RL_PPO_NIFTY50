NEW CHAMPION: v26 mean_outperf -51.49pp beats v18 -63.2pp
⚠️ BOOKKEEPING CHAMPION ONLY — improvement is an inactivity artifact (see below)

---

# v26 READOUT — Feature Reduction (98 → 22 indicators)

**Run date:** 2026-09-01/02  
**Branch:** auto/run-a  
**Panel:** 10 stocks (RELIANCE, INFY, TATAMOTORS, ITC, ADANIENT, HDFCBANK, TCS, SBIN, AXISBANK, HINDALCO)

---

## Verdict

v26 improves mean outperformance to -51.49pp from v18's -63.2pp and takes the ratchet, but the gain is an artifact of inactivity: 4/10 stocks are degenerate or near-degenerate, and both B&H-beating stocks (ADANIENT 0 trades, HDFCBANK 5) simply held cash. The hypothesis' mechanism was confirmed — final explained variance fell from v18's 0.95–0.99 to ~0.55–0.99 range (mean ≈0.80) — yet test performance did not improve, refuting the claim that critic overfit is the binding constraint and echoing v11. **v26 should NOT be layered under later variants.** The next lever should target signal and reward shape (v19 B&H-relative reward), not further regularization.

---

## Results vs v18 Baseline

| Stock | v26 outperf | v18 outperf | Δ | Notes |
|---|---|---|---|---|
| ADANIENT | +22.54pp | +66.83pp | -44.3pp | **DEGENERATE**: 0 trades, held cash. B&H was -22.54%. |
| HDFCBANK | +2.19pp | -55.20pp | +57.4pp | 5 trades — borderline degenerate |
| TCS | -8.81pp | -8.53pp | -0.3pp | ~flat |
| INFY | -15.05pp | -61.90pp | +46.9pp | better |
| AXISBANK | -35.46pp | -5.35pp | -30.1pp | worse |
| ITC | -61.12pp | +40.09pp | **-101.2pp** | severe regression (lost signal) |
| SBIN | -62.61pp | -110.02pp | +47.4pp | better |
| RELIANCE | -71.62pp | -41.47pp | -30.2pp | worse; 10 trades (near-degenerate) |
| HINDALCO | -136.04pp | -188.18pp | +52.1pp | better |
| TATAMOTORS | -148.94pp | -24.10pp | **-124.8pp** | severe regression; 13 trades |

**Summary:**
- Mean outperf: **-51.49pp** (vs v18 champion -63.2pp, +11.71pp improvement)
- Beats B&H: **2/10** (both degenerate/borderline)
- Positive Sharpe: 7/10
- Degenerate (<5 trades): 1/10 (ADANIENT 0 trades; RELIANCE 10, TATAMOTORS 13 near-degenerate)
- 0/10 survive BH-FDR at q=0.05

---

## Mechanism Analysis

### EV de-pegged (mechanism confirmed)
Feature reduction from 98 → 22 indicators succeeded in reducing critic overfit:
- v18 final EV: 0.95–0.99 across all stocks
- v26 final EV: 0.55–0.99 (mean ≈0.80) — de-pegged as hypothesized

### Test performance unchanged (hypothesis refuted)  
Despite EV falling, test outperformance did not improve. This echoes v11's lesson: "Critic overfit isn't the dominant problem." The EV reduction is real but doesn't translate to better generalization.

### Trade collapse = signal loss
ITC and TATAMOTORS show catastrophic regression coinciding with collapsed trade counts (TATAMOTORS 78→13 trades, ITC 161→76 trades). The 22-name feature list removed entry-timing signals that v18's 98 indicators were capturing. Result: policy went quiet and held through adverse moves.

---

## Statistical significance

0/10 stocks survive BH-FDR at q=0.05. No statistically demonstrable edge. TATAMOTORS has the most significant negative signal (p_boot=0.986), indicating the policy is reliably losing relative to B&H.

---

## vs Dumb Baselines

```
PPO        beats B&H  2/10   mean outperf  -51.49pp
SMA20/50   beats B&H  1/10   mean outperf  -50.02pp   (essentially tied with PPO)
MOM126     beats B&H  1/10   mean outperf  -33.15pp   (MOM beats PPO by 18.3pp)
```

PPO beats SMA on only 4/10 stocks, and MOM126 beats PPO in mean outperformance. The 22-indicator version is not beating simple rules.

---

## Ratchet Status

v26 takes the ratchet on mean outperf (-51.49pp > -63.2pp) with the following caveat flag:
- This is an **inactive-policy artifact**: the mean improved primarily because degenerate cash-holding on ADANIENT (B&H -22.54%) and near-degenerate behavior on other stocks avoids the downside rather than capturing alpha.
- Do NOT use v26 as the base for subsequent variants. Fork future experiments from v18 until a genuine alpha-positive mechanism is found.

---

## Next Actions

1. **v19 (B&H-relative reward)** — highest priority. If the policy is losing to B&H because it makes absolute returns but misses the benchmark, explicit alpha gradient is the lever. This is supported by the MOM126 result: simple momentum beats PPO on mean outperf.
2. **Avoid further regularization experiments** until v19 results are in. v11, v26 both confirmed EV can be reduced without benefit.
3. Consider: is the 10-stock panel long enough to see signal through the noise? significance.py says no for all 10 stocks.

---

## Setup Notes (for reproducibility)

- Python 3.11.15
- pandas-ta 0.4.71b0 (force-installed from PyPI whl; not on PyPI for Python <3.12)
- Patch required: `/usr/local/lib/python3.11/dist-packages/pandas_ta/overlap/hma.py` line 69 — Python 3.12 f-string syntax must be replaced for Python 3.11 compatibility (see HANDOFF.run-a.md for patch script)
