"""
run_panel.py — run one Rl_vN variant over the fixed 10-stock comparison panel.

Usage:
    python run_panel.py v18            # re-baseline after the vecnorm fix
    python run_panel.py v20
    python run_panel.py v22 --seeds 3  # trains seed offsets 0..2 per stock

Outputs land in results_<ver>/ and models_<ver>/ so runs never collide.
After each run: python summarize_results.py results_<ver>/
"""
import argparse
import importlib
import os
import sys

PANEL = [
    "RELIANCE", "INFY", "TATAMOTORS", "ITC", "ADANIENT",
    "HDFCBANK", "TCS", "SBIN", "AXISBANK", "HINDALCO",
]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("version", help="e.g. v18, v20, v24")
    ap.add_argument("--seeds", type=int, default=1,
                    help="number of seed offsets (v22 only; others ignore >1)")
    args = ap.parse_args()
    ver = args.version.lower()
    if ver.startswith("rl_"):
        ver = ver[len("rl_"):]

    os.environ["RESULTS_DIR"] = f"results_{ver}"
    os.environ["TRAINED_MODEL_DIR"] = f"models_{ver}"
    os.environ["CONSOLIDATED_REPORT"] = f"consolidated_report_{ver}.txt"

    mod = importlib.import_module(f"Rl_{ver}")
    if hasattr(mod, "train_pooled"):
        sys.exit(f"{ver} is a pooled variant — its process_stock is the v18 "
                 f"per-stock path, not the pooled experiment. Run: python Rl_{ver}.py")
    results = []
    for stock in PANEL:
        path = os.path.join(mod.NIFTY50_PATH, f"{stock}_daily.csv")
        if not os.path.exists(path):
            print(f"!! missing data file for {stock}, skipping"); continue
        if ver == "v22" and args.seeds > 1:
            for k in range(args.seeds):
                results.append(mod.process_stock(path, seed_offset=k))
        else:
            results.append(mod.process_stock(path))
    mod.generate_consolidated_report(results)

if __name__ == "__main__":
    main()
