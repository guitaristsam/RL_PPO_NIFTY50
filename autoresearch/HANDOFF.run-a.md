# HANDOFF — auto-run-A

Last updated: 2026-09-04T21:20 UTC

## Current task
RUNNING: v19 full 10-stock panel (B&H-relative reward). Resuming from 3/10 done.
Target: results_v19/

## Progress
- 3/10 stocks complete: RELIANCE, INFY, TATAMOTORS
- Running now: ITC (background PID via Bash background)
- Remaining: ADANIENT, HDFCBANK, TCS, SBIN, AXISBANK, HINDALCO
- Expected time: ~2.5h for remaining 7 stocks

## Why v19 (FRONTIER item #4)
Advisor confirmed: v19 is the correct target. It attacks reward mismatch (absolute P&L vs alpha).

## v18 CORRECT 10-stock panel baseline
**Mean outperf: -38.78pp** (NOT -63.2pp in FRONTIER which is wrong)
Per stock:
- RELIANCE: -41.47pp
- INFY: -61.90pp  
- TATAMOTORS: -24.10pp
- ITC: +40.10pp
- ADANIENT: +66.83pp
- HDFCBANK: -55.20pp
- TCS: -8.53pp
- SBIN: -110.02pp
- AXISBANK: -5.35pp
- HINDALCO: -188.18pp

## v19 existing results (3/10)
- RELIANCE: -31.97pp outperf (v18: -41.47pp, +9.5pp improvement)
- INFY: -28.22pp outperf (v18: -61.90pp, +33.68pp improvement)
- TATAMOTORS: -152.09pp outperf (v18: -24.10pp, -127.99pp DISASTER)

TATAMOTORS is a massive regression. v19 needs massive wins elsewhere to overcome it.

## pandas-ta install for fresh sessions (CRITICAL)
```bash
curl --proxy "$HTTPS_PROXY" -sL -o /tmp/pandas_ta-0.4.71b0-py3-none-any.whl "https://files.pythonhosted.org/packages/be/2f/c67d49afd31c3b02a02ecb5dd07399ed35298042e1b50d166efe2068bb0e/pandas_ta-0.4.71b0-py3-none-any.whl"
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

## Full pip install needed each session
```bash
pip install stable-baselines3 sb3-contrib gymnasium finrl matplotlib scikit-learn tensorboard scipy tqdm "numpy==2.2.6"
pip install alpaca-trade-api --timeout 300
pip install exchange-calendars --timeout 300
pip install pytz stockstats rich wrds yfinance --timeout 300
```
(Then pandas_ta above separately)

## How to run remaining stocks
```bash
RESULTS_DIR="results_v19" TRAINED_MODEL_DIR="models_v19" CONSOLIDATED_REPORT="consolidated_report_v19.txt" python -c "
from Rl_v19 import process_stock, NIFTY50_PATH
import os
for stock in ['ADANIENT', 'HDFCBANK', 'TCS', 'SBIN', 'AXISBANK', 'HINDALCO']:
    path = os.path.join(NIFTY50_PATH, f'{stock}_daily.csv')
    result = process_stock(path)
    print(f'Done: {stock}')
"
```
(Resume guard will skip already-done ones)

## After panel completes
1. Run summarize_results.py results_v19
2. Run significance.py results_v19
3. Run baselines.py results_v19
4. Write results_v19/READOUT.md
5. Advisor consultation (pre-PR boundary)
6. Open PR to main

## FRONTIER corrections needed
- v18 baseline should be -38.78pp (not -63.2pp)
- Put this in READOUT.md
