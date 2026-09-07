# HANDOFF — auto-run-B

Last updated: 2026-09-07T00:00:00Z

## Status: COMPLETE — run-B queue exhausted

All four assigned variants are now done. v18 remains production champion.

## Queue Final Status

| Variant | Status | Result | vs v18 |
|---------|--------|--------|--------|
| v19 (B&H-relative reward) | DONE | -71.92pp | +0.82pp (null) |
| v20 (best-by-Sharpe) | DONE | -71.58pp | +1.16pp (null) |
| v21 (target-exposure) | DONE | -73.16pp | -0.42pp (null) |
| v23 (warmup=150k) | DONE | -69.69pp | +3.05pp (null — NO RATCHET) |
| v63 (obs-noise) | DEFERRED | — | Not started — other session owns branch |

**Checkpoint-timing lever exhausted. Four consecutive null results.**

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

## Branch State

- **Lease**: 2026-09-06T23:25:00Z (belongs to concurrent session running v29)
- **DO NOT write a new lease** — other session owns this branch
- **DO NOT start new runs** — other session is running v29
- PR #3 updated with full v23 analysis

## Concurrent Session (v29) — IN PROGRESS

v29 panel (DD penalty lambda=0) started ~23:25 UTC. Panel running, watcher script commits each stock as it completes.

**Progress as of ~00:00 UTC:**
- RELIANCE: -47.17pp (v18: -76.93pp, **+29.76pp lift**)
- INFY: -47.11pp (v18: -39.50pp, -7.61pp regression)
- TATAMOTORS: training (~87k/200k steps at 00:00 UTC)
- ITC through HINDALCO: queued

**Key diagnostic**: TATAMOTORS had 5 degenerate trades in v18 (-257.93pp). If trade count >20 in v29, DD penalty removal fixed the beta gap.

After panel: analytics → READOUT.md → ADVISOR boundary (b) → PR update.

## Key Findings This Run-B Campaign

1. **Correct v18 baseline = -72.74pp** (was -38.78pp due to vecnorm-fix data issue)
2. **All four variants = null results** (±3pp of v18, within noise)
3. **TATAMOTORS structurally untrainable**: every variant degenerates on this stock
4. **Cost drag = 15.2% avg** but beta gap (-47pp gross-of-cost) is the dominant term
5. **Advisor ratchet rule**: ≥6/10 improved, no new degeneracy, ≥1 FDR survivor
6. **Next frontier**: v29 (DD penalty=0), then cross-stock signals (v51/v61)

## Next Session: Wait for v29 Results

If next session fires on this branch:
1. Check if v29 is done (`ls results_v29/`)
2. If done: run analytics, write READOUT, update PR
3. If other session still running: update handoff and yield
4. v63 (obs-noise) is ready to run when branch is free (Rl_v63.py committed)

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
