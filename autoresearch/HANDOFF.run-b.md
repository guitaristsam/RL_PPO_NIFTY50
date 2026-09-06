# HANDOFF — auto-run-B

Last updated: 2026-09-06T21:12:00Z

## Status: IN PROGRESS — v23 panel running (task bi26mq8a8)

**Current task:** v23 full panel (warmup=150k, eval_freq=25k) — 0/10 complete as of 21:12 UTC

## Queue Status (as of 2026-09-06)

| Variant | Status | Result |
|---------|--------|--------|
| v19 (B&H-relative reward) | DONE | -71.92pp — null vs v18 -72.74pp |
| v20 (best-by-Sharpe) | DONE | -71.58pp — null vs v18 -72.74pp |
| v21 (target-exposure) | DONE | -73.16pp — null vs v18 -72.74pp |
| v23 (warmup=150k) | **IN PROGRESS** | task bi26mq8a8 |
| v22 (ensemble seeds) | SKIPPED — needs active policy first | — |

## Correct v18 Baseline (canonical)

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

## v23 Completion Steps (CRITICAL for next session)

When task bi26mq8a8 completes (or on session start if session is fresh):
1. Check run log: `/tmp/.../scratchpad/v23_run.log`
2. Collect results:
   ```bash
   python summarize_results.py results_v23
   python significance.py results_v23
   python baselines.py results_v23
   ```
3. Key diagnostic: TATAMOTORS trades count. If >20, warmup fix worked.
4. Compare mean vs v18 clean (-72.74pp). If >5pp better with active policies = progress.
5. Write results_v23/READOUT.md
6. Commit + push all results
7. Update PR with v23 results
8. Advisor consult (second boundary: before opening/updating PR)
9. After queue exhausted: propose v27 (start fully invested)

## After Queue Exhausted

All queue items (v19-v23) will be done. Next session should:
- Propose v27 variant: v18 + initial position fully invested (not cash)
  - Hypothesis: agent in cash at start misses early bull runs; "beta gap"
  - Single variable change: set `self.state[1+stock_dim : 1+2*stock_dim] = initial_shares`
  - Prior advisor (Opus, 2026-09-05) ranked this #1 recommendation
- Alternatively: n_epochs 5→3 to reduce critic overfit

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

## Key Insights
- Correct v18 baseline = -72.74pp (NOT -38.78pp)
- v19/v20/v21 were all null results (within ±1.2pp of v18)
- TATAMOTORS degeneracy (-258pp, 5 trades) dominates mean outperf
- All reward/checkpoint variants tried so far: no improvement
- v27 "start fully invested" is top recommendation for next variant
- FRONTIER.md champion section needs updating (auto-tinker job)
