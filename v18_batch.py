"""
v18 small batch — focus on stocks where v18's warmup-skip will actually change
the saved val checkpoint vs v16.

v16 best-val checkpoint timestep per stock:
  HDFCBANK   @ 50k   ← changes in v18 (warmup=100k forces later)
  ADANIENT   @ 50k   ← changes in v18
  ADANIPORTS @ 50k   ← changes in v18
  TCS        @ 50k   ← changes in v18
  ITC        @ 150k  — unaffected, used as control to confirm no regression
  RELIANCE   @ 100k  — unaffected, skipped to save time
  TATAMOTORS @ 150k  — unaffected
  INFY       @ 200k  — unaffected
"""
import os
import time
from Rl_v18 import process_stock, NIFTY50_PATH

STOCKS = ["HDFCBANK", "ADANIENT", "ADANIPORTS", "TCS", "ITC"]

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

print(f"\n{'='*60}\nBATCH DONE — {len(results)}/{len(STOCKS)} processed in "
      f"{(time.time()-t0)/60:.1f} min\n{'='*60}")
for r in results:
    print(f"  {r['stock']:12s} final ₹{r['final_value']:>10,.0f}  "
          f"B&H ₹{r['buy_hold_value']:>10,.0f}  "
          f"win {r['win_rate']:5.1f}%  trades {r['total_trades']:>4d}")
