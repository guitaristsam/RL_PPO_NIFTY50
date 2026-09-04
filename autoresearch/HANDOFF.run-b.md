# HANDOFF — auto-run-B

Last updated: 2026-09-04T21:15:00Z

## Status: IN PROGRESS — v20 panel running

**Current task:** v20 (best-by-Sharpe ValidationCallback) full 10-stock panel  
**Variant:** v20 — v18 + val checkpoint saved by best Sharpe instead of best return

## CRITICAL: Correct v18 Baseline

**v18 10-panel mean outperf = −38.8pp** (NOT −63.2pp as FRONTIER says).  
Recomputed from actual results/ files:  
ADANIENT +66.83, TCS -8.53, HDFCBANK -55.20, INFY -61.90, RELIANCE -41.47,  
ITC +40.10, SBIN -110.02, TATAMOTORS -24.10, AXISBANK -5.35, HINDALCO -188.18  
Mean = -38.8pp. Use this for all v20/v23 comparisons.

## Progress
- v19 panel: **COMPLETE** (10/10 stocks, READOUT at results_v19/READOUT.md)
- v21 panel: **COMPLETE** (10/10 stocks, READOUT at results_v21/READOUT.md) — REJECTED -73.16pp
- v20 panel: STARTING (0/10 stocks), 2026-09-04

## What was done in PREVIOUS sessions

### Session ~2026-09-02
- v19 full panel complete: mean -71.92pp vs correct baseline -38.8pp → REJECTED
- B&H-relative reward fails: penalizes bull-market participation, ITC -141pp swing
- Wrote results_v19/READOUT.md, updated PR #3

### Session ~2026-09-01
- v21 full panel complete: mean -73.16pp vs -38.8pp → REJECTED  
- Target-exposure action caused over-trading (avg 243.7 trades vs v18's 109.7)
- TATAMOTORS catastrophic: -261pp vs B&H +251%
- results_v21/READOUT.md written

## v19 Final Results (for reference)
- Mean outperformance: -71.92pp
- Beats B&H: 1/10
- VERDICT: REJECTED

## v21 Final Results (for reference)
- Mean outperformance: -73.16pp
- Beats B&H: 1/10 (degenerate cash-hold, 9 trades)
- VERDICT: REJECTED

## Setup commands for next session (CRITICAL)

```bash
# Install pandas-ta (NOT available normally in Python 3.11):
WHL="https://files.pythonhosted.org/packages/00/c8/4ed6c9bc469bc937e0e437da78a437e320a9a001984a556463b8a00f5910/pandas_ta-0.4.67b0-py3-none-any.whl"
curl -sL "$WHL" -o /tmp/pandas_ta-0.4.67b0-py3-none-any.whl
pip install /tmp/pandas_ta-0.4.67b0-py3-none-any.whl --ignore-requires-python -q

# Patch hma.py for Python 3.11:
python - << 'PATCH'
path = '/usr/local/lib/python3.11/dist-packages/pandas_ta/overlap/hma.py'
with open(path) as f: content = f.read()
old = '    hma.name = f"HMA{"" if mamode == "wma" else mamode[0]}_{length}"'
new = '    _mm = "" if mamode == "wma" else mamode[0]\n    hma.name = f"HMA{_mm}_{length}"'
if old in content:
    content = content.replace(old, new)
    with open(path, 'w') as f: f.write(content)
    print('patched')
else:
    print('already patched or different version')
PATCH

# Install other deps:
pip install stable-baselines3 sb3-contrib finrl gymnasium scikit-learn matplotlib tensorboard -q

# Patch finrl __init__.py:
python - << 'PATCH'
path = '/usr/local/lib/python3.11/dist-packages/finrl/__init__.py'
with open(path, 'w') as f:
    f.write("""from __future__ import annotations
try:
    from finrl.test import test
except Exception:
    pass
try:
    from finrl.trade import trade
except Exception:
    pass
try:
    from finrl.train import train
except Exception:
    pass
""")
print('finrl patched')
PATCH
```

## Running v20 panel

Results go to: results_v20/ models_v20/

```bash
python run_panel.py v20
```

Or per-stock:
```bash
python -c "from Rl_v20 import process_stock, NIFTY50_PATH; import os; os.environ['RESULTS_DIR']='results_v20'; os.environ['TRAINED_MODEL_DIR']='models_v20'; process_stock(os.path.join(NIFTY50_PATH, 'RELIANCE_daily.csv'))"
```

## PANEL stocks (10) — all unstarted for v20
RELIANCE, INFY, TATAMOTORS, ITC, ADANIENT, HDFCBANK, TCS, SBIN, AXISBANK, HINDALCO

## Gotchas
- ~10-15 min per stock on CPU. Full panel ~100-150 min.
- Resume guard: if results_v20/{SYMBOL}/{SYMBOL}_report.txt exists, stock is skipped
- Commit after each stock to preserve progress
- models_v20/ is gitignored — only results_v20/ committed
- **Correct v18 baseline: -38.8pp** (not -63.2pp)
- Watch for degenerate cash-holds (< 20 trades) — don't count as genuine B&H-beats
- Sharpe-best may pick low-exposure checkpoints — log trades + exposure carefully
- v20 can only reshuffle among 3 eligible checkpoints (100k/150k/200k post-warmup)

## Next after v20
- v23 (warmup=150k, eval_freq=25k) — shift all evals to 150-200k range
- If v20 beats v18 (-38.8pp) with GENUINE active policies, declare NEW CHAMPION
- Update PR #3 with READOUT

## Immediate next step
Run v20 full panel. Check each stock for: outperf, Sharpe, trades, degenerate?
