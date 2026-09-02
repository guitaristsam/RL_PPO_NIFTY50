# HANDOFF — auto-run-A

Last updated: 2026-09-02T21:22 UTC

## Current task
RUNNING: v19 full 10-stock panel (B&H-relative reward). PID 2658.
Target: results_v19/

## Progress
- 0/10 stocks complete (started at 21:21 UTC)
- Expected time: ~3-4 hours total (~20-24 min per stock)
- Stocks: RELIANCE, INFY, TATAMOTORS, ITC, ADANIENT, HDFCBANK, TCS, SBIN, AXISBANK, HINDALCO

## Why v19 (not v22 as FRONTIER says)
Advisor consultation at session start: v22 is variance reduction on a systematically-biased policy;
v22 also lacks report-writing glue in ensemble_predict.py so can't produce a comparable readout.
v19 attacks the root cause (reward mismatch: agent optimizes absolute P&L, not alpha vs B&H).
v26 READOUT also explicitly recommends v19 next.

## Context
- v26 complete: -51.49pp mean outperf (bookkeeping champion, inactivity artifact)
- v18 is the real champion: -63.2pp mean outperf
- Dependencies all installed fresh this session (pandas_ta wheel + patch, SB3, finrl, etc.)
- test_variant_envs.py: 2/2 PASSED before starting panel

## pandas-ta install for fresh sessions (CRITICAL)
```bash
curl -sL -o /tmp/pt.whl "https://files.pythonhosted.org/packages/be/2f/c67d49afd31c3b02a02ecb5dd07399ed35298042e1b50d166efe2068bb0e/pandas_ta-0.4.71b0-py3-none-any.whl"
cp /tmp/pt.whl "/tmp/pandas_ta-0.4.71b0-py3-none-any.whl"
pip install --no-deps --ignore-requires-python "/tmp/pandas_ta-0.4.71b0-py3-none-any.whl"
# Then patch Python 3.11 syntax:
python - << 'PATCH'
path = '/usr/local/lib/python3.11/dist-packages/pandas_ta/overlap/hma.py'
with open(path) as f: content = f.read()
old = '    hma.name = f"HMA{"" if mamode == "wma" else mamode[0]}_{length}"'
new = '    _mm = "" if mamode == "wma" else mamode[0]\n    hma.name = f"HMA{_mm}_{length}"'
if old in content:
    content = content.replace(old, new)
    with open(path, 'w') as f: f.write(content)
    print('patch OK')
PATCH
```

## Also needed (pip install)
pip install stable-baselines3 sb3-contrib gymnasium finrl matplotlib scikit-learn tensorboard scipy tqdm alpaca-trade-api exchange-calendars wrds yfinance pytz stockstats rich "numpy==2.2.6"

## Next session work
When v19 panel finishes:
1. Run summarize_results.py results_v19
2. Run significance.py results_v19
3. Run baselines.py results_v19
4. Write results_v19/READOUT.md
5. Open/update PR (advisor consultation first)
6. Update handoff
