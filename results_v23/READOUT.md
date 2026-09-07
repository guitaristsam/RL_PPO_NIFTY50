# v23 Full Panel READOUT — 2026-09-06

## Hypothesis

v18 used `warmup_steps=100k`, `eval_freq=50k` → eligible val evals at 100k, 150k, 200k.
The 100k checkpoint is under-trained (ADANIENT's v18 win was saved at 100k from a "lucky long"
during the 2020 bull). v23 changes ONLY the cadence: `warmup_steps=150k`, `eval_freq=25k`
→ eligible evals at **150k, 175k, 200k**. Same number of evals but entirely in the converged
post-warmup window.

**Single-variable change vs v18:** only `ValidationCallback` eval timing. Algorithm, reward,
features, architecture, hyperparameters, and splits are unchanged.

---

## Results — Full 10-Stock Panel

| Stock | v23 PPO | v23 B&H | v23 Outperf | v18 Outperf | Δ vs v18 | Sharpe | DD | Trades |
|-------|---------|---------|------------|------------|---------|--------|-----|--------|
| ADANIENT | -19.35% | -21.61% | **+2.26pp** ✓ | +4.12pp | -1.85pp | -0.201 | -58.81% | 44 |
| AXISBANK | +49.68% | +51.62% | -1.94pp | -24.74pp | **+22.80pp** | +0.947 | -18.07% | 81 |
| TCS | -7.84% | +4.96% | -12.80pp | -5.35pp | -7.45pp | -0.207 | -21.50% | 85 |
| HDFCBANK | +14.71% | +30.62% | -15.91pp | -15.91pp | 0.00pp | +0.300 | -15.71% | 46 |
| INFY | -17.00% | +22.50% | -39.50pp | -39.50pp | 0.00pp | -0.598 | -27.97% | 59 |
| SBIN | +44.33% | +88.72% | -44.39pp | -44.39pp | 0.00pp | +0.452 | -23.98% | 98 |
| ITC | +34.82% | +105.88% | -71.06pp | -65.99pp | -5.07pp | +0.440 | -16.41% | 138 |
| RELIANCE | -8.24% | +68.70% | -76.94pp | -76.94pp | 0.00pp | -0.102 | -32.47% | 139 |
| HINDALCO | -7.54% | +178.12% | -185.66pp | -200.74pp | **+15.08pp** | -0.249 | -17.09% | 15 |
| TATAMOTORS | +0.00% | +250.97% | -250.97pp | -257.93pp | +6.96pp | 0.000 | 0.00% | **0 DEGEN** |

---

## Summary Statistics

| Metric | v23 | v18 (baseline) | Δ |
|--------|-----|----------------|---|
| Mean outperf vs B&H | **-69.69pp** | -72.74pp | **+3.05pp** |
| Beats B&H (genuine, ≥20 trades) | 1/10 (ADANIENT) | 1/10 (ADANIENT) | 0 |
| Degenerate (<5 trades) | 1/10 (TATAMOTORS 0T) | 1/10 (TATAMOTORS 5T) | 0 |
| Avg Sharpe | +0.078 | +0.013 | +0.065 |
| Avg max DD | -23.20% | -25.82% | +2.62% |
| Avg trades | 70.5 | 84.3 | -13.8 |
| Stocks improved | 3/10 | — | — |
| Significance (p_boot<0.05) | 0/10 | 0/10 | — |

---

## Per-Stock Analysis

### AXISBANK: +22.80pp improvement (v18 -24.74pp → v23 -1.94pp)
The most notable single improvement. v18's checkpoint (likely at 100k) appears to have
been a mediocre early policy; v23's 150k warmup forced selection from a better-trained
checkpoint. AXISBANK Sharpe rose from +0.587 to +0.947. This is the strongest evidence
that the cadence change is doing something real for at least one stock.

### TATAMOTORS: still degenerate (0 trades → was 5 in v18)
The longer warmup made TATAMOTORS MORE degenerate. By 150k the policy had fully converged
to "do nothing." The 5 trades in v18 came from the earlier 100k checkpoint (a partially
explored policy). At 150k–200k the "sit in cash" absorber has fully engaged. This is a
fundamental signal that TATAMOTORS is feature-untrainable in the current regime — no
warmup adjustment fixes it.

### HINDALCO: +15.08pp (but still -185.66pp)
HINDALCO outperformance improved slightly (from -200.74pp to -185.66pp). Still deeply
negative. HINDALCO's B&H returned +178% in the test period — the policy has no mechanism
to track this bull trend.

### TCS/ITC: slight regressions (-7.45pp, -5.07pp)
The cadence shift moved the selection slightly into over-trained territory for these two.
Recall v16/v17 observed INFY late-training overfit at val@200k. A similar mechanism may
be at play for TCS/ITC when warmup=150k forces all evals into the 150k-200k range.

### 5/10 stocks unchanged
HDFCBANK, INFY, RELIANCE, SBIN, ADANIENT are statistically identical to v18. The
cadence change had no meaningful effect on more than half the panel.

---

## Diagnostic: Val Checkpoint Selection

v23's eligible checkpoints (150k, 175k, 200k) vs v18's (100k, 150k, 200k):
- The 100k checkpoint was removed from contention
- Stocks that benefited from the 100k checkpoint (ADANIENT in v18) now get 150k instead
- This mattered for AXISBANK (+22pp) and marginally for HINDALCO/TATAMOTORS
- The 100k removal hurt TCS and ITC slightly

---

## Statistical Significance

```
0/10 stocks with p_boot < 0.05 (vs 0/10 for v18)
0/10 survive BH-FDR at q=0.05
Reminder: no correction for ~20 versions tried.
```

No statistically demonstrable edge. AXISBANK's +22pp improvement is the largest single-stock
movement but does not survive multiple-testing correction.

---

## Verdict

**NULL RESULT WITH ONE OUTLIER. v18 remains PRODUCTION CHAMPION. NO RATCHET.**

Independent advisor (Opus, 2026-09-06) assessment:
- 4/10 stocks are checkpoint-identical (same policy selected) → effective sample is 6
- 3 up / 3 down among the non-identical stocks → sign test is zero information
- TATAMOTORS "+6.96pp" is the **same false-win pathology as HDFCBANK-v16** (0 trades; CLAUDE.md §Known failure modes already documents this)
- HINDALCO "+15.08pp" moves -200pp to -185pp on 15 trades — noise on a catastrophe
- AXISBANK +22.80pp with 81 trades and Sharpe 0.947 is the only real effect: **one stock out of ten, 0/10 FDR survivors**
- v23 INTRODUCED a new degenerate case (TATAMOTORS 0 trades vs v18's 5 trades) — this is a regression, not a delta

**Ratchet criteria not met** (advisor proposed rule: ≥6/10 improved, no new degeneracy, ≥1 FDR survivor).

**The checkpoint-timing lever is exhausted.** v19/v20/v21/v23 are four consecutive nulls vs v18 using checkpoint selection / reward shape / action space variants. v18 remains the production champion.

**The cadence change is a wash.** It helped AXISBANK (one stock's checkpoint timing was
suboptimal) but didn't solve the structural problems (TATAMOTORS, HINDALCO, cost drag).

---

## Comparison: Full Run-B Queue Summary

| Variant | Mean outperf | Beats B&H | vs v18 | Status |
|---------|-------------|-----------|--------|--------|
| v18 (baseline) | **-72.74pp** | 1/10 | — | **CHAMPION** |
| v23 (warmup=150k) | -69.69pp | 1/10 | +3.05pp | NEUTRAL |
| v20 (best-by-Sharpe) | -71.58pp | 0/10 | +1.16pp | REJECTED |
| v19 (B&H-relative reward) | -71.92pp | 0/10 | +0.82pp | REJECTED |
| v21 (target-exposure) | -73.16pp | 1/10 degen | -0.42pp | REJECTED |

All four variants produced null-to-marginal results vs v18. The single-variable forks of
v18 (checkpoint timing, reward shape, action space) have not moved the needle.

---

## What This Tells Us

The reward/checkpoint lever space is effectively exhausted. The remaining high-value levers:

1. **v29 (DD penalty = 0)** — *running concurrently on this branch*. The DD penalty may
   be counterproductive post-vecnorm-fix (mean penalty > mean equity premium, incentivizing
   cash holds). This is the highest-priority ongoing experiment.

2. **v27/v28 (cost drag)** — confirmed 15.2% avg cost drag, but gross-of-cost outperf is
   still -47pp (beta gap dominates). Action deadband targets the minority term.

3. **Cross-stock signals (v51/v61)** — proposed by auto-research as ceiling levers.

4. **v63 (obs-noise regularizer)** — designed by auto-research. Queued on this branch.

---

## Run Metadata
- Date: 2026-09-06
- Runtime: ~160 minutes (10 stocks × 16 min CPU)
- Code: `Rl_v23.py`, run via `python run_panel.py v23`
- Session: `https://claude.ai/code/session_01BRu7XTtDCBwxPcHiujf53q`
