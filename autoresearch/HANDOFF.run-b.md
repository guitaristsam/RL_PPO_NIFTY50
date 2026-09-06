# HANDOFF — auto-run-B

Last updated: 2026-09-06T21:40:00Z

## Status: IN PROGRESS — v23 panel running (task bi26mq8a8), v63 queued

**Current task:** v23 full panel (warmup=150k, eval_freq=25k) — ~40% complete (RELIANCE at ~78k/200k)
**Next task:** v63 (additive Gaussian obs-noise, train-only) — Rl_v63.py fetched from research branch

## Queue Status (as of 2026-09-06)

| Variant | Status | Result |
|---------|--------|--------|
| v19 (B&H-relative reward) | DONE | -71.92pp — null vs v18 -72.74pp |
| v20 (best-by-Sharpe) | DONE | -71.58pp — null vs v18 -72.74pp |
| v21 (target-exposure) | DONE | -73.16pp — null vs v18 -72.74pp |
| v23 (warmup=150k) | **IN PROGRESS** | task bi26mq8a8, ~23:30 UTC finish |
| v63 (obs-noise regularizer) | **QUEUED** | Rl_v63.py fetched, ready to run |
| v22 (ensemble seeds) | SKIPPED | needs active policy first |

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

## Cost-Drag Finding (Confirmed 2026-09-06, Opus advisor)

Transaction costs average **15.2% of initial capital** across the panel.
ITC 31.4%, RELIANCE 27.5%, SBIN 20.3%. Win rates are 56-87% but costs eat all gains.
Root cause: NOT reward shaping or overfit — it's **excessive turnover**.

Corrected v27 proposal: action deadband (`|action| < 0.1*hmax → 0`) + min-hold 3 bars.
(See NEEDS_HUMAN.md for implementation details)

## v23 Completion Steps (CRITICAL for next session)

When task bi26mq8a8 completes (or use fallback at 23:20 UTC trigger trig_017Kka4QRfXPGR5b8DhErRtu):
1. Run analytics:
   ```bash
   python summarize_results.py results_v23
   python significance.py results_v23
   python baselines.py results_v23
   ```
2. Key diagnostic: TATAMOTORS trades count. If >20, warmup fix worked.
3. Compare mean vs v18 clean (-72.74pp). If >5pp better with active policies = progress.
4. Write results_v23/READOUT.md
5. Commit + push all results
6. ADVISOR CONSULT (second boundary — before PR update): spawn Opus advisor with v23 results
7. Update PR #3 (mcp__github__update_pull_request owner=guitaristsam repo=rl_ppo_nifty50 pull_number=3)
8. Start v63 panel: `python run_panel.py v63` (background task)

## v63 Details

- Fetched from `origin/auto/research:Rl_v63.py` (auto-research drafted, ast-clean, 63 ins/3 del vs v18)
- Single variable: additive Gaussian obs-noise sigma=0.1 on NORMALIZED train observations
- Anti-overfit regularizer: "v63 jitters ALL features by small amount, post-normalization"
- Auto-research ranked: priority 3 (after v61 market-breadth, v62 action-repeat)
- Expected runtime: same as v23, ~140 min for full panel

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

# If v63 not present, fetch from research branch
git show origin/auto/research:Rl_v63.py > Rl_v63.py 2>/dev/null && echo "v63 fetched"
```

## Key Insights
- Correct v18 baseline = -72.74pp (NOT -38.78pp)
- v19/v20/v21 were all null results (within ±1.2pp of v18)
- Cost drag = root cause (15.2% avg, not reward or overfit)
- TATAMOTORS degeneracy (-258pp, 5 trades) dominates mean outperf
- v27 = action deadband (NOT start-fully-invested — that was wrong)
- FRONTIER.md champion section needs updating (auto-tinker job)
- v63 = obs-noise regularizer, ready to run
