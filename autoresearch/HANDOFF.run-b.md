# HANDOFF — auto-run-B

Last updated: 2026-09-06T23:56:01Z

## Status: RUNNING — v29 panel (DD lambda=0)

**Current task:** v29 full panel (DD penalty removed, lambda=0.0) — STARTED ~23:25 UTC
**Progress:** RELIANCE done (-47.17pp, +29.76pp vs v18). INFY done (-47.11pp, -7.61pp vs v18). TATAMOTORS training (~87k/200k steps as of 00:00 UTC).
**Next task:** after panel completes — analytics, READOUT.md, ADVISOR boundary B, PR update

## Decision: Why v29 (not v23/v27/v63)

Advisor (Opus, 2026-09-06 session boundary A) rejected v23/v27/v63 and proposed v29:
- **Root cause is beta gap, NOT costs.** Gross-of-cost mean outperf = -47pp; net = -72.74pp.
  Costs are real (18.4% multiplicative drag, ~26pp) but the minority term.
- **DD penalty is broken post-vecnorm-fix.** Mean penalty (-0.059 units/step) > mean equity
  premium (+0.046 units/step). The reward function tells the policy that cash > equities.
  This explains the observed 40.3% average realized exposure across the panel.
- **v27 premise refuted.** Only 5.6% of trades are below the 0.1*hmax deadband threshold.
  The agent makes large all-in/all-out swings, not tiny nibbles.
- **v29 = single-character change.** `self._dd_lambda = 1.0 → 0.0` in IntegerTradingEnv.__init__.
  Otherwise byte-identical to v18. No reward normalization issue (norm_reward=False).

## Queue Status

| Variant | Status | Result |
|---------|--------|--------|
| v19 (B&H-relative reward) | DONE | -71.92pp — null vs v18 -72.74pp |
| v20 (best-by-Sharpe) | DONE | -71.58pp — null vs v18 -72.74pp |
| v21 (target-exposure) | DONE | -73.16pp — null vs v18 -72.74pp |
| v23 (warmup=150k) | SKIP (advisor: null, wrong lever) | — |
| v29 (DD penalty removed) | **IN PROGRESS** | RELIANCE: -47.17pp (v18: -76.93pp, +29.76pp). INFY: -47.11pp (v18: -39.50pp, -7.61pp). TATAMOTORS in training. |
| v63 (obs-noise) | SKIP (advisor: wrong lever) | — |
| v28 (turnover penalty) | QUEUED if v29 shows exposure is not binding | — |

## Correct v18 Baseline (canonical, run-b 2026-09-05)

| Stock | Outperf | Sharpe | Trades | B&H Return |
|-------|---------|--------|--------|-----------|
| RELIANCE | -76.93pp | -0.102 | 139 | +68.70% |
| INFY | -39.50pp | -0.598 | 59 | +22.50% |
| TATAMOTORS | -257.93pp | -0.559 | **5 DEGEN** | +250.97% |
| ITC | -65.99pp | 0.534 | 129 | +105.88% |
| ADANIENT | **+4.12pp** ✓ | -0.180 | 53 | -21.61% |
| HDFCBANK | -15.91pp | 0.300 | 46 | +30.62% |
| TCS | -5.35pp | -0.010 | 64 | +4.96% |
| SBIN | -44.39pp | 0.452 | 98 | +88.72% |
| AXISBANK | -24.74pp | 0.587 | 69 | +51.62% |
| HINDALCO | -200.74pp | -0.292 | 181 | +178.12% |
| **Mean** | **-72.74pp** | +0.013 | 84.3 | +98.04% |

## Key Insights from Opus Advisor (2026-09-06)

### Beta gap is the dominant failure term (~47pp of 73pp gap)
- Mean exposure across panel = 40.3% (policy prefers cash)
- After removing cost drag: gross-of-costs mean outperf = -47pp
- TATAMOTORS: gross outperf still -156pp (not a cost problem)

### DD penalty makes cash > equities in reward
- Mean reward for holding equity: +0.046 units/step
- Mean DD penalty for holding equity: -0.059 units/step
- Net: -0.013 units/step per step of holding (cash = 0.0)
- Spearman ρ(net reward drift, exposure) = 0.55 (0.77 ex-TATAMOTORS)

### v27 (deadband) premise refuted
- Median trade size = 0.50-0.88 * hmax (large all-in/all-out swings)
- Only 5.6% of trades below 0.1*hmax threshold
- Only 1.2% of transaction costs from sub-threshold trades
- Deadband removes ~1% of cost drag, not 50-70%

## v29 Completion Steps (for next session if incomplete)

1. Resume: `python run_panel.py v29` (resume guard handles already-done stocks)
2. After completion, run analytics:
   ```bash
   python summarize_results.py results_v29
   python significance.py results_v29
   python baselines.py results_v29
   ```
3. Key diagnostics:
   - Mean realized exposure per stock (compare to v18's 40.3%)
   - TATAMOTORS trades count (if >20: beta fix working)
   - Median outperf (not just mean — TATAMOTORS/HINDALCO dominate mean)
4. Write results_v29/READOUT.md with RATCHET check vs v18 (-72.74pp)
5. ADVISOR CONSULT (second boundary — before PR update)
6. Commit + push all results
7. Update/create PR

## Setup Commands for Fresh Session

```bash
pip install stable-baselines3 sb3-contrib finrl gymnasium scikit-learn matplotlib tensorboard tqdm rich -q

WHL="https://files.pythonhosted.org/packages/00/c8/4ed6c9bc469bc937e0e437da78a437e320a9a001984a556463b8a00f5910/pandas_ta-0.4.67b0-py3-none-any.whl"
curl -sL "$WHL" -o /tmp/pandas_ta.whl
cp /tmp/pandas_ta.whl "/tmp/pandas_ta-0.4.67b0-py3-none-any.whl"
pip install "/tmp/pandas_ta-0.4.67b0-py3-none-any.whl" --ignore-requires-python -q

python - << 'PATCH'
path = '/usr/local/lib/python3.11/dist-packages/pandas_ta/overlap/hma.py'
with open(path) as f: c = f.read()
old = '    hma.name = f"HMA{"" if mamode == "wma" else mamode[0]}_{length}"'
new = '    _mm = "" if mamode == "wma" else mamode[0]\n    hma.name = f"HMA{_mm}_{length}"'
if old in c:
    with open(path,'w') as f: f.write(c.replace(old,new))
    print('patched')
else: print('ok')
PATCH

python - << 'PATCH'
path = '/usr/local/lib/python3.11/dist-packages/finrl/__init__.py'
with open(path, 'w') as f:
    f.write("from __future__ import annotations\ntry:\n    from finrl.test import test\nexcept Exception:\n    pass\n")
print('finrl patched')
PATCH
```

## Impl Files on Branch

- `Rl_v29.py`: committed, byte-identical to v18 except lambda=0 + version comment
