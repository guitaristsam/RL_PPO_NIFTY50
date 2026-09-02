# HANDOFF — auto-run-B

Last updated: 2026-09-02T21:15:00Z

## Status: IN PROGRESS — v19 running

**Current task:** v19 (B&H-relative reward) full 10-stock panel
**Variant:** v19 — reward = clip((log(eq_t/eq_{t-1}) - log(close_t/close_{t-1}))*100, -10, 10) minus DD

## Progress
- RELIANCE: RUNNING (background task bkeutn72m) — first stock, ~10 min per stock
- 0/10 stocks committed yet

## What was done THIS session

- Set up branch auto/run-b from origin/auto/run-b
- Read FRONTIER: v26 done by run-a (-51.49pp, 2/10); no CANDIDATES pending
- Advisor (opus): recommended v19 as top priority (B&H-relative reward for trending stocks)
- Installed deps: stable-baselines3, sb3-contrib, gymnasium, finrl, matplotlib, scikit-learn, tensorboard, rich, pandas-ta 0.4.71b0
- Patched: pandas-ta hma.py (Python 3.11), finrl __init__.py (try/except wrapping)
- Running v19 RELIANCE now

## Setup commands for next session (CRITICAL)
```bash
pip install stable-baselines3 sb3-contrib gymnasium matplotlib scikit-learn tensorboard rich "numpy==2.2.6"
pip install --ignore-requires-python "pandas-ta==0.4.71b0"

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
PATCH

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
PATCH
```

## Running v19 panel
Results go to: results_v19/ models_v19/
Command: RESULTS_DIR=results_v19 TRAINED_MODEL_DIR=models_v19 CONSOLIDATED_REPORT=consolidated_report_v19.txt python run_panel.py v19

## PANEL stocks (10)
RELIANCE, INFY, TATAMOTORS, ITC, ADANIENT, HDFCBANK, TCS, SBIN, AXISBANK, HINDALCO

## Previous session context
- v21 was REJECTED: -73.16pp vs v18 -38.8pp, 0/10 beats B&H
- v26 done by run-a: -51.49pp, 2/10 (improvement but inactivity artifact)
- PR #3 exists for v21 on auto/run-b → main

## Gotchas
- ~10-15 min per stock on CPU. Full panel ~100-150 min.
- Resume guard: if results_v19/{SYMBOL}/{SYMBOL}_report.txt exists, stock is skipped
- v18 10-panel baseline is -38.8pp per run-b's prior measurements (FRONTIER says -63.2pp — stale)
- Commit after each stock to preserve progress
- models_v19/ is gitignored — only results_v19/ committed

## Next after v19
- v20 (best-by-Sharpe) — second priority per advisor
- v22 (ensemble seeds) — not recommended until root-cause fixed
