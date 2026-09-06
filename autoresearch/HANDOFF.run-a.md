# HANDOFF — auto-run-A

Last updated: 2026-09-06T21:14 UTC

## Current task
v22 full 10-stock panel — STARTING NOW (ensemble seeds, 3 per stock)

## Previous completed tasks
- v19 panel: COMPLETE — CLEAR LOSS (-72.38pp vs v18 -38.78pp). See results_v19/READOUT.md
- v20 panel: COMPLETE — CLEAR LOSS (-69.10pp vs v18 -38.78pp). See results_v20/READOUT.md
  - ADANIENT win = degenerate (6 trades)
  - Lost ITC (+40pp→-91pp) and TATAMOTORS (-24pp→-213pp)
  - Val-Sharpe selection picks inactivity optima

## v18 PRODUCTION CHAMPION baseline (10-stock panel)
- Mean outperf: **-38.78pp** (computed from results/)
- Note: FRONTIER.md says -63.2pp but that's the 50-stock sweep. 10-stock = -38.78pp.
- Beats B&H: 2/10 (ITC +40pp, ADANIENT +67pp)

## Progress (v22 panel)
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

Command: `python run_panel.py v22 --seeds 3`
(3 seeds per stock, saves to results_v22/, models_v22/)
Resume guard: results_v22/{STOCK}/{STOCK}_report.txt — delete to re-run

## Next session task (if v22 incomplete)
Resume: `python run_panel.py v22 --seeds 3` (resume guard handles already-done stocks)

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

## After v22 panel completes
1. python summarize_results.py results_v22
2. python significance.py results_v22
3. python baselines.py results_v22
4. Write results_v22/READOUT.md with verdict vs v18 (-38.78pp baseline)
5. ADVISOR STEP (pre-PR boundary)
6. Open/update PR to main

## PR status
- PR to main: open (check with mcp__github__list_pull_requests)
- Branch: auto/run-a
