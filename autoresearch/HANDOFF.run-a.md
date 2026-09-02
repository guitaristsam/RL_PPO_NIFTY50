# HANDOFF — auto-run-A

Last updated: 2026-09-02T01:20 UTC

## Current task
COMPLETED: v26 full 10-stock panel done. READOUT written. PR being created.

## Progress
- 10/10 stocks complete (RELIANCE, INFY, TATAMOTORS, ITC, ADANIENT, HDFCBANK, TCS, SBIN, AXISBANK, HINDALCO)
- Results in: results_v26/
- READOUT at: results_v26/READOUT.md
- v26 mean outperf: -51.49pp (vs v18 champion -63.2pp)
- v26 beats B&H: 2/10 (ADANIENT degenerate 0 trades, HDFCBANK borderline 5 trades)
- NEW CHAMPION declared (ratchet rule) but flagged as bookkeeping/artifact

## Ratchet flag
v26 takes the champion slot on mean outperf but the improvement is an inactivity artifact.
auto-tinker should update FRONTIER.md with this caveat.

## Next session work
- v22 (ensemble seeds) is next in queue, but advisor recommends v19 (B&H-relative reward) first
- Note: the FRONTIER queue has v26, v22, v20, v21, v23 (v19 not listed, unclear why)
- Consider running v19 if it's not listed in FRONTIER (may need to add to queue or check with tinker)

## pandas-ta install for fresh sessions (CRITICAL)
```bash
WHEEL_URL="https://files.pythonhosted.org/packages/be/2f/c67d49afd31c3b02a02ecb5dd07399ed35298042e1b50d166efe2068bb0e/pandas_ta-0.4.71b0-py3-none-any.whl"
curl -sL -o /tmp/pandas_ta.whl "$WHEEL_URL"
pip install --ignore-requires-python /tmp/pandas_ta.whl
# Then patch Python 3.11 syntax:
python - << 'PATCH'
path = '/usr/local/lib/python3.11/dist-packages/pandas_ta/overlap/hma.py'
with open(path) as f: content = f.read()
old = '    hma.name = f"HMA{"" if mamode == "wma" else mamode[0]}_{length}"'
new = '    _mm = "" if mamode == "wma" else mamode[0]\n    hma.name = f"HMA{_mm}_{length}"'
content = content.replace(old, new)
with open(path, 'w') as f: f.write(content)
print('pandas-ta patch OK')
PATCH
```

## Also needed (pip install)
pip install stable-baselines3 sb3-contrib gymnasium finrl alpaca-trade-api exchange-calendars yfinance wrds pytz stockstats rich numpy==2.2.6
