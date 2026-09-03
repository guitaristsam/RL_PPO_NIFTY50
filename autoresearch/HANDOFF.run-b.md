# HANDOFF — auto-run-B

Last updated: 2026-09-03T00:30:00Z

## Status: IN PROGRESS — v20 starting

**Current task:** v20 (best-by-Sharpe ValidationCallback) full 10-stock panel  
**Variant:** v20 — v18 + val checkpoint saved by best Sharpe instead of best return

## Progress
- v19 panel: **COMPLETE** (10/10 stocks, READOUT written)
- v20 panel: 0/10 stocks complete, starting now

## What was done THIS session

- Resumed from previous session's completed v19 panel (all 10 stocks)
- Ran summarize_results, significance, baselines on v19
- v19 result: -71.92pp mean outperformance (WORSE than v18 -63.2pp), 1/10 beats B&H
- REJECTED: B&H-relative reward catastrophically hurt ITC (-141pp swing) and TATAMOTORS
- Wrote results_v19/READOUT.md
- Updated PR #3 to include v19 results
- Starting v20 now

## v19 Final Results
- Mean outperformance: -71.92pp (v18 baseline: -63.2pp)
- Beats B&H: 1/10
- VERDICT: REJECTED (B&H-relative reward failed — penalizes bull-market participation)
- ITC: +4.21% PPO vs +105.88% B&H = -101pp (was +40pp in v18 — massive regression)
- HINDALCO: 0 trades (degenerate cash-hold)

## Setup commands for next session (CRITICAL)
```bash
pip install numpy pandas scipy stable-baselines3 sb3-contrib gymnasium matplotlib scikit-learn tensorboard rich

# These may already be installed from prior container — verify with:
# python -c "import stable_baselines3, sb3_contrib, finrl; print('OK')"

# If finrl not installed:
pip install finrl

# Patch hma.py for Python 3.11:
python - << 'PATCH'
path = '/usr/local/lib/python3.11/dist-packages/pandas_ta/overlap/hma.py'
import os
if os.path.exists(path):
    with open(path) as f: content = f.read()
    old = '    hma.name = f"HMA{"" if mamode == "wma" else mamode[0]}_{length}"'
    new = '    _mm = "" if mamode == "wma" else mamode[0]\n    hma.name = f"HMA{_mm}_{length}"'
    if old in content:
        content = content.replace(old, new)
        with open(path, 'w') as f: f.write(content)
        print('patched')
    else:
        print('already patched')
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
print('finrl patched')
PATCH
```

## Running v20 panel
Results go to: results_v20/ models_v20/
Command: RESULTS_DIR=results_v20 TRAINED_MODEL_DIR=models_v20 CONSOLIDATED_REPORT=consolidated_report_v20.txt python run_panel.py v20

## PANEL stocks (10)
RELIANCE, INFY, TATAMOTORS, ITC, ADANIENT, HDFCBANK, TCS, SBIN, AXISBANK, HINDALCO

## Gotchas
- ~10-15 min per stock on CPU. Full panel ~100-150 min.
- Resume guard: if results_v20/{SYMBOL}/{SYMBOL}_report.txt exists, stock is skipped
- Commit after each stock to preserve progress
- models_v20/ is gitignored — only results_v20/ committed
- v18 10-panel baseline for this panel: -63.2pp per FRONTIER

## Next after v20
- v23 (warmup=150k, eval_freq=25k) — third priority per original queue
- If v20 beats v18, declare NEW CHAMPION at top of READOUT
- Then update PR #3
