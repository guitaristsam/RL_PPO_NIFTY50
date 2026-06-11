"""
baselines.py — dumb-strategy battery on the same test windows as PPO.

A PPO+LSTM stack is only justified if it beats strategies a person could
write in two lines. For every stock with a completed PPO run, this evaluates
on the IDENTICAL test dates (taken from that stock's account_value.csv),
with the project's cost model (integer shares, 0.25% per side, all-in /
all-out):

  BH       buy & hold (reference; matches calculate_buy_and_hold)
  SMA      long while SMA20 > SMA50, else cash (SMAs warm up on history
           before the test window — causal)
  MOM126   long while close > close 126 trading days ago, else cash

Prints per-stock outperformance vs B&H for each strategy next to PPO's, and
a summary: which strategies beat B&H how often, and whether PPO beats the
dumb baselines per stock.

Usage:
    python baselines.py                 # results/
    python baselines.py results_v18
"""

import argparse
import os
import sys

import numpy as np
import pandas as pd

DATA_DIR = os.environ.get(
    "NIFTY50_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"),
)
COST = 0.0025
INITIAL = 10000.0


def run_signal_strategy(closes, signal):
    """All-in/all-out integer-share strategy. signal[t] True = want exposure
    on day t (decision applied at close t). Returns final equity."""
    cash, shares = INITIAL, 0
    for t in range(len(closes)):
        price = closes[t]
        if signal[t] and shares == 0:
            shares = int(cash // (price * (1 + COST)))
            cash -= shares * price * (1 + COST)
        elif not signal[t] and shares > 0:
            cash += shares * price * (1 - COST)
            shares = 0
    if shares > 0:
        cash += shares * closes[-1] * (1 - COST)
    return cash


def evaluate_stock(results_dir, symbol):
    av_path = os.path.join(results_dir, symbol, "account_value.csv")
    px_path = os.path.join(DATA_DIR, f"{symbol}_daily.csv")
    if not (os.path.isfile(av_path) and os.path.isfile(px_path)):
        return None
    av = pd.read_csv(av_path)
    if len(av) < 60:
        return None
    test_dates = pd.to_datetime(av["date"]).dt.normalize()

    px = pd.read_csv(px_path)
    px["datetime"] = pd.to_datetime(px["datetime"]).dt.normalize()
    px = px.set_index("datetime").sort_index()
    full_close = px["close"]

    # Indicators on the full history (causal), then sliced to test dates.
    sma_sig = full_close.rolling(20).mean() > full_close.rolling(50).mean()
    mom_sig = full_close > full_close.shift(126)

    closes = full_close.reindex(test_dates.values)
    if closes.isna().any():
        return None
    c = closes.to_numpy(dtype=np.float64)

    ppo_ret = (av["account_value"].iloc[-1] / av["account_value"].iloc[0] - 1) * 100
    bh_ret = (run_signal_strategy(c, np.ones(len(c), dtype=bool)) / INITIAL - 1) * 100
    sma_ret = (run_signal_strategy(
        c, sma_sig.reindex(test_dates.values).fillna(False).to_numpy()) / INITIAL - 1) * 100
    mom_ret = (run_signal_strategy(
        c, mom_sig.reindex(test_dates.values).fillna(False).to_numpy()) / INITIAL - 1) * 100

    return {
        "stock": symbol,
        "ppo": ppo_ret - bh_ret,
        "sma": sma_ret - bh_ret,
        "mom": mom_ret - bh_ret,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results_dir", nargs="?", default="results")
    args = ap.parse_args()
    if not os.path.isdir(args.results_dir):
        sys.exit(f"results directory '{args.results_dir}' not found.")

    rows = []
    for sym in sorted(os.listdir(args.results_dir)):
        if not os.path.isdir(os.path.join(args.results_dir, sym)):
            continue
        r = evaluate_stock(args.results_dir, sym)
        if r is not None:
            rows.append(r)
    if not rows:
        sys.exit("No usable stocks found.")

    rows.sort(key=lambda r: -r["ppo"])
    print(f"{'stock':<12} {'PPO-BH':>9} {'SMA-BH':>9} {'MOM-BH':>9}   PPO beats")
    print("-" * 58)
    for r in rows:
        beats = []
        if r["ppo"] > r["sma"]:
            beats.append("SMA")
        if r["ppo"] > r["mom"]:
            beats.append("MOM")
        print(f"{r['stock']:<12} {r['ppo']:>+8.1f}p {r['sma']:>+8.1f}p "
              f"{r['mom']:>+8.1f}p   {','.join(beats) or '-'}")

    n = len(rows)
    print("-" * 58)
    for key, label in (("ppo", "PPO"), ("sma", "SMA20/50"), ("mom", "MOM126")):
        v = np.array([r[key] for r in rows])
        print(f"{label:<10} beats B&H {int(np.sum(v > 0)):>2}/{n}   "
              f"mean outperf {v.mean():>+7.2f}pp   median {np.median(v):>+7.2f}pp")
    n_vs_sma = int(np.sum([r["ppo"] > r["sma"] for r in rows]))
    n_vs_mom = int(np.sum([r["ppo"] > r["mom"] for r in rows]))
    print(f"\nPPO beats SMA20/50 on {n_vs_sma}/{n} stocks; "
          f"beats MOM126 on {n_vs_mom}/{n}.")


if __name__ == "__main__":
    main()
