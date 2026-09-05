# HANDOFF — auto-run-A

Last updated: 2026-09-05T21:14 UTC

## Current task
v20 full 10-stock panel — IN PROGRESS

Advisor (session-start, 2026-09-05) recommended v20 over v22:
- v22 (ensemble) reduces variance but not bias; 2/10 win rate is bias-limited
- v20 (val Sharpe selection) directly targets the documented failure mode (INFY/TATAMOTORS overfit)
- v20 ~3h vs v22 ~10h

## v19 Panel Result (previous session — COMPLETE)
v18 PRODUCTION CHAMPION at -38.78pp mean outperf.
v19 = -72.38pp mean outperf. CLEAR LOSS. 0/10 beats B&H.
See results_v19/READOUT.md for full analysis.

## Progress (v20 panel)
- [ ] RELIANCE
- [ ] INFY
- [ ] TATAMOTORS
- [ ] ITC
- [ ] ADANIENT
- [ ] HDFCBANK
- [ ] TCS
- [ ] SBIN
- [ ] AXISBANK
- [ ] HINDALCO

Resume guard: results_v20/{STOCK}/{STOCK}_report.txt — delete to re-run

## Next session task (if v20 incomplete)
Resume: `python run_panel.py v20` (resume guard handles already-done stocks)
Or use wrapper: run_v20_with_commits.sh in scratchpad

## Critical install steps (fresh session)
```bash
pip install stable-baselines3 sb3-contrib gymnasium finrl matplotlib scikit-learn tensorboard scipy tqdm "numpy==2.2.6"
pip install alpaca-trade-api --timeout 300
pip install exchange-calendars --timeout 300
pip install pytz stockstats rich wrds yfinance --timeout 300
pip install numba
curl --proxy "$HTTPS_PROXY" -sL -o /tmp/pandas_ta.whl "https://files.pythonhosted.org/packages/be/2f/c67d49afd31c3b02a02ecb5dd07399ed35298042e1b50d166efe2068bb0e/pandas_ta-0.4.71b0-py3-none-any.whl"
pip install --no-deps --ignore-requires-python /tmp/pandas_ta.whl
python -c "
path = '/usr/local/lib/python3.11/dist-packages/pandas_ta/overlap/hma.py'
with open(path) as f: content = f.read()
old = '    hma.name = f\"HMA{\"\" if mamode == \"wma\" else mamode[0]}_{length}\"'
new = '    _mm = \"\" if mamode == \"wma\" else mamode[0]\n    hma.name = f\"HMA{_mm}_{length}\"'
if old in content:
    content = content.replace(old, new)
    with open(path, 'w') as f: f.write(content)
    print('patch OK')
"
```

## After v20 panel completes
1. python summarize_results.py results_v20
2. python significance.py results_v20
3. python baselines.py results_v20
4. Write results_v20/READOUT.md with verdict vs v18 (-38.78pp baseline)
5. ADVISOR STEP (pre-PR boundary)
6. Open PR to main
