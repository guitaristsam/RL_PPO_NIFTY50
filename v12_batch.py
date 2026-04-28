"""
v9 batch runner. Imports process_stock from Rl_v9 and runs a curated subset
covering different sectors / trend profiles, so we can study training-curve
behaviour without paying for the full 50-stock alphabetical sweep.

Picks:
  ADANIENT     — mid-cap, volatile, large bull run in test (v8 lost 67%)
  ADANIPORTS   — port operator, large-cap (v8 lost 16%)
  TCS          — IT, steady uptrend
  HDFCBANK     — financials, sideways/down in test
  INFY         — IT, steady uptrend (cross-check vs TCS)
  ITC          — FMCG, recent breakout
  TATAMOTORS   — auto, very volatile
  RELIANCE already done in the prior v9 run — skipped here.
"""
import os
import time
from Rl_v12 import process_stock, NIFTY50_PATH, generate_consolidated_report

STOCKS = [
    "ADANIENT", "ADANIPORTS", "TCS", "HDFCBANK", "INFY", "ITC", "TATAMOTORS"
]

results = []
t0 = time.time()
for sym in STOCKS:
    fp = os.path.join(NIFTY50_PATH, f"{sym}_daily.csv")
    if not os.path.exists(fp):
        print(f"SKIP {sym}: file not found at {fp}")
        continue
    print(f"\n{'#'*60}\n# {sym}\n{'#'*60}")
    r = process_stock(fp)
    if r is not None:
        results.append(r)
    print(f"  Cumulative wall: {(time.time()-t0)/60:.1f} min")

# Aggregate
print(f"\n{'='*60}\nBATCH DONE — {len(results)}/{len(STOCKS)} processed in "
      f"{(time.time()-t0)/60:.1f} min\n{'='*60}")
for r in results:
    print(f"  {r['stock']:12s} final ₹{r['final_value']:>10,.0f}  "
          f"B&H ₹{r['buy_hold_value']:>10,.0f}  "
          f"win {r['win_rate']:5.1f}%  trades {r['total_trades']:>4d}")
