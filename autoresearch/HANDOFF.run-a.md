# HANDOFF — auto-run-A

Last updated: 2026-09-04T22:50 UTC

## Current task
COMPLETE: v19 full 10-stock panel. 10/10 stocks done.
PR opened to main.

## v19 Panel Result: CLEAR LOSS

v18 remains PRODUCTION CHAMPION at -38.78pp mean outperf.
v19 = -72.38pp mean outperf (-33.6pp worse than v18).
v19 beats B&H: 0/10 (v18 was 2/10).

See results_v19/READOUT.md for full analysis.

## Key finding: FRONTIER baseline correction needed

FRONTIER.md has v18 = -63.2pp. Correct value = -38.78pp (computed from actual panel reports).
Logged in NEEDS_HUMAN.md — auto-tinker should fix FRONTIER.

## Next session task: v22 (ensemble seeds)

Per advisor at pre-PR boundary: v22 is higher priority than v20.
Reason: Per-stock swings of ±130pp on single seed — variance estimate needed before any
single-run comparison is trustworthy. v22 gives both variance estimate and reduction.

Run: `python run_panel.py v22 --seeds 3`
Expected: ~3 * 20 min * 10 stocks = 600 min (10 hours) — may need multiple sessions.

Resume guard: results_v22/{STOCK}/{STOCK}_report.txt (offset 0 = default seed).
Actually v22 saves with seed suffix: results_v22/{STOCK}_{STOCK}_seed42_report.txt (need to check).

## pandas-ta install for fresh sessions (CRITICAL)
```bash
curl --proxy "$HTTPS_PROXY" -sL -o /tmp/pandas_ta-0.4.71b0-py3-none-any.whl "https://files.pythonhosted.org/packages/be/2f/c67d49afd31c3b02a02ecb5dd07399ed35298042e1b50d166efe2068bb0e/pandas_ta-0.4.71b0-py3-none-any.whl"
pip install --no-deps --ignore-requires-python "/tmp/pandas_ta-0.4.71b0-py3-none-any.whl"
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

## Full pip install sequence
```bash
pip install stable-baselines3 sb3-contrib gymnasium finrl matplotlib scikit-learn tensorboard scipy tqdm "numpy==2.2.6"
pip install alpaca-trade-api --timeout 300
pip install exchange-calendars --timeout 300
pip install pytz stockstats rich wrds yfinance --timeout 300
# then pandas_ta above
```

## v19 per-stock summary (reference)
- RELIANCE: -31.97pp (v18: -41.47pp, +9.5pp ✓)
- INFY: -28.22pp (v18: -61.90pp, +33.7pp ✓)
- TATAMOTORS: -152.09pp (v18: -24.10pp, -128pp ✗ CATASTROPHIC)
- ITC: -94.15pp (v18: +40.10pp, -134pp ✗ CATASTROPHIC)
- ADANIENT: -14.65pp (v18: +66.83pp, -81pp ✗ CATASTROPHIC)
- HDFCBANK: -45.92pp (v18: -55.20pp, +9.3pp ✓)
- TCS: -19.34pp (v18: -8.53pp, -10.8pp ✗)
- SBIN: -98.33pp (v18: -110.02pp, +11.7pp ✓)
- AXISBANK: -60.99pp (v18: -5.35pp, -55.6pp ✗)
- HINDALCO: -178.12pp, 0 trades DEGENERATE
