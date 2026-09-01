# HANDOFF — auto-run-A

Last updated: 2026-09-01T23:26 UTC

## Current task
Running v26 full 10-stock panel (feature reduction: 98→22 indicators, obs 101→25 dims).

## Progress
- Panel run started at 23:26 UTC, PID 4440 (nohup python run_panel.py v26 > /tmp/v26_panel.log 2>&1)
- RELIANCE: in progress (first stock)
- Results go to results_v26/, models_v26/

## Environment setup (CRITICAL for next session)
- Python 3.11.15 on bare system
- pandas-ta 0.4.71b0 force-installed from PyPI whl + patched overlap/hma.py (1 SyntaxError fixed)
- All other deps installed: stable-baselines3, sb3-contrib, finrl, yfinance, wrds, etc.
- numpy 2.2.6 (within >=1.24,<2.3 requirement)

## If session ended mid-run:
- Check which stocks completed: ls results_v26/*/
- The resume guard in run_panel.py will skip completed stocks
- Re-run: `python run_panel.py v26 > /tmp/v26_panel.log 2>&1 &`
- NOTE: pandas-ta patch to /usr/local/lib/python3.11/dist-packages/pandas_ta/overlap/hma.py
  is NOT persistent across sessions — must be re-applied:
  `sed -i 's/hma.name = f"HMA{"" if mamode == "wma" else mamode\[0\]}_/.../' /usr/.../hma.py`
  See setup section above.

## pandas-ta install for fresh sessions:
```bash
pip install -r requirements.txt 2>&1 || true
WHEEL_URL="https://files.pythonhosted.org/packages/be/2f/c67d49afd31c3b02a02ecb5dd07399ed35298042e1b50d166efe2068bb0e/pandas_ta-0.4.71b0-py3-none-any.whl"
curl -sL -o /tmp/pandas_ta.whl "$WHEEL_URL"
pip install --ignore-requires-python /tmp/pandas_ta.whl
# Fix Python 3.11 syntax error:
python -c "
import re
path = '/usr/local/lib/python3.11/dist-packages/pandas_ta/overlap/hma.py'
with open(path) as f: content = f.read()
content = content.replace(
    'hma.name = f\"HMA{\"\" if mamode == \"wma\" else mamode[0]}_{length}\"',
    '_mm = \"\" if mamode == \"wma\" else mamode[0]\n    hma.name = f\"HMA{_mm}_{length}\"'
)
with open(path, 'w') as f: f.write(content)
print('patch applied')
"
```

## Gotchas
- run_panel.py PANEL order: RELIANCE, INFY, TATAMOTORS, ITC, ADANIENT, HDFCBANK, TCS, SBIN, AXISBANK, HINDALCO
- Resume guard: if results_v26/{SYMBOL}/{SYMBOL}_report.txt exists, stock is skipped
- models_v26/ is in .gitignore already; only commit results_v26/

## Next after panel completes
1. Run: python summarize_results.py results_v26 results/ (delta vs v18)
2. Run: python significance.py results_v26
3. Run: python baselines.py results_v26
4. Write results_v26/READOUT.md with verdict vs FRONTIER champion (-63.2pp mean, 1/10 B&H wins)
5. Open PR to main
