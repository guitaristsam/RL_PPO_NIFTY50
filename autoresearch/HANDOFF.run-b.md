# HANDOFF — auto-run-B

Last updated: 2026-09-05T21:20:00Z

## Status: IN PROGRESS — v18 panel re-run (correct baseline)

**Current task:** Re-run v18 10-stock panel to establish correct post-vecnorm-fix baseline  
**Then:** v23 panel (warmup=150k, eval_freq=25k)

## CRITICAL ADVISOR FINDING (2026-09-05)

Independent advisor (opus) raised: the `results/` files (which we've been using as the
v18 baseline at -38.78pp) are from the INITIAL REPO COMMIT (2026-04-29). The vecnorm fix
(91e620d, 2026-06-11) reportedly only re-ran RELIANCE. So:

- RELIANCE: post-fix (-41.47pp) ✓
- ITC: PRE-FIX (+40.10pp) — unconfirmed with current code
- ADANIENT: PRE-FIX (+66.83pp) — unconfirmed with current code
- Others: pre-fix data

**If ITC and ADANIENT don't reproduce with post-fix code, v18 may have 0 genuine B&H-beats.**
This retroactively recontextualizes all v19/v20/v21 rejections.

**Tonight's priority: run clean v18 panel → results_v18/**

## Completed Experiments Summary

| Variant | Mean outperf | Beats B&H | vs v18 (-38.78pp) | READOUT |
|---------|-------------|-----------|-------------------|---------|
| v19 | -72.38pp | 0/10 | -33.6pp worse | results_v19/READOUT.md (run-a) |
| v21 | -73.16pp | 1/10 (degen) | -34.4pp worse | results_v21/READOUT.md |
| v20 | -71.58pp | 0/10 (degen) | -32.8pp worse | results_v20/READOUT.md ✓ WRITTEN |
| v23 | TBD | TBD | TBD | NOT STARTED |

Note: All three "vs v18" deltas cluster at -32 to -34pp. Advisor suspects biased
denominator (v18 baseline inflated by pre-fix ITC/ADANIENT data).

## Progress Tonight (2026-09-05)

### v18 clean panel (results_v18/)
- [x] RELIANCE — RUNNING (started ~21:18 UTC)
- [ ] INFY
- [ ] TATAMOTORS
- [ ] ITC
- [ ] ADANIENT
- [ ] HDFCBANK
- [ ] TCS
- [ ] SBIN
- [ ] AXISBANK
- [ ] HINDALCO

### v23 panel (results_v23/) — start AFTER v18 panel
- [ ] All 10 stocks

## Setup Commands (CRITICAL for fresh session)

```bash
# Install stable-baselines and friends:
pip install stable-baselines3 sb3-contrib finrl gymnasium scikit-learn matplotlib tensorboard tqdm rich -q

# Install pandas_ta (NOT normally available in Python 3.11):
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

## Running v18 panel (per stock):

```bash
python -c "
import os
os.environ['RESULTS_DIR'] = 'results_v18'
os.environ['TRAINED_MODEL_DIR'] = 'models_v18'
os.environ['CONSOLIDATED_REPORT'] = 'consolidated_report_v18.txt'
from Rl_v18 import process_stock, NIFTY50_PATH
process_stock(os.path.join(NIFTY50_PATH, 'STOCK_daily.csv'))
"
```

Or all at once:
```bash
python run_panel.py v18
```

## Running v23 panel:

```bash
python run_panel.py v23
```

## Gotchas
- ~10-15 min per stock on CPU
- Resume guard: if results_vNN/{SYMBOL}/{SYMBOL}_report.txt exists, stock is skipped
- Commit after each stock to preserve progress
- models_v18/ and models_v23/ are gitignored — only results committed
- Watch for degenerate cash-holds (< 20 trades)

## Advisor Recommendations (act on these next session if time runs out)
1. v27: turnover penalty (reward -= λ * traded_value/equity). Advisor estimated costs
   eat 20.1% of log-equity on average; 5/10 stocks would beat B&H GROSS. Highest
   single-variable lever available.
2. v28: exposure floor. Policy is in market 44.5% of time, capturing 14.8% of B&H move.
3. Consider median outperformance + gross-of-cost as reporting metric.

## Key Diagnostics to Look For in v18 Clean Run
- Does ITC still beat B&H? (+40pp in pre-fix data)
- Does ADANIENT still beat B&H? (+67pp in pre-fix data)
- If neither reproduces, entire rejection record needs recontextualization

## Next after v18 + v23
- Write READOUT for both with v18-clean as correct baseline
- If v23 beats clean-v18, declare NEW CHAMPION
- Update PR with both READOUTs
- Plan v27 design and write Rl_v27.py
