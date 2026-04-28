"""
summarize_results.py — aggregate per-stock reports into a portfolio-level table.

Reads `results/{SYMBOL}/{SYMBOL}_report.txt` for every completed stock, parses
PPO return / B&H return / Sharpe / max DD / trade count, prints a sorted
table by outperformance (PPO − B&H), and prints summary statistics:
  - count beating B&H
  - average outperformance
  - average Sharpe
  - average max DD
  - count with degenerate trade count (< 0.01 × test bars ≈ < 5 trades)

Run AFTER `python Rl_v18.py` (or any Rl_vN.py / *_batch.py) has finished:

    python summarize_results.py

Optionally pass a results dir override:

    python summarize_results.py results_v19/

Output is plain text — easy to paste into a CV bullet or a README.
"""

import os
import re
import sys
from collections import namedtuple

Row = namedtuple("Row", "stock ppo bh outperf sharpe dd trades win")


def parse_report(path):
    if not os.path.isfile(path):
        return None
    text = open(path, encoding="utf-8").read()
    m1 = re.search(
        r"PPO STRATEGY PERFORMANCE.*?Total Return: (-?[\d.]+)%"
        r".*?Sharpe Ratio: (-?[\d.]+)"
        r".*?Maximum Drawdown: (-?[\d.]+)%",
        text,
        re.DOTALL,
    )
    m2 = re.search(r"BUY & HOLD.*?Total Return: (-?[\d.]+)%", text, re.DOTALL)
    m3 = re.search(r"Total Trades: (\d+).*?Win Rate: (-?[\d.]+)%", text, re.DOTALL)
    if not (m1 and m2):
        return None
    ppo = float(m1.group(1))
    bh = float(m2.group(1))
    return Row(
        stock=os.path.basename(os.path.dirname(path)),
        ppo=ppo,
        bh=bh,
        outperf=ppo - bh,
        sharpe=float(m1.group(2)),
        dd=float(m1.group(3)),
        trades=int(m3.group(1)) if m3 else 0,
        win=float(m3.group(2)) if m3 else 0.0,
    )


def main():
    results_dir = sys.argv[1] if len(sys.argv) > 1 else "results"
    if not os.path.isdir(results_dir):
        print(f"results directory '{results_dir}' not found.")
        sys.exit(1)

    rows = []
    for d in sorted(os.listdir(results_dir)):
        full = os.path.join(results_dir, d)
        if not os.path.isdir(full):
            continue
        report_path = os.path.join(full, f"{d}_report.txt")
        row = parse_report(report_path)
        if row is not None:
            rows.append(row)

    if not rows:
        print(f"No parseable per-stock reports found under {results_dir}/.")
        sys.exit(1)

    rows.sort(key=lambda r: -r.outperf)

    # Per-stock table, sorted best-to-worst by outperformance
    print(
        f"{'stock':<12} {'ppo%':>8} {'bh%':>8} {'outperf':>10} "
        f"{'sharpe':>7} {'dd%':>7} {'trades':>7} {'win%':>6}"
    )
    print("-" * 75)
    for r in rows:
        win_flag = "  WIN" if r.outperf > 0 else ""
        print(
            f"{r.stock:<12} {r.ppo:>+8.2f} {r.bh:>+8.2f} {r.outperf:>+9.2f}pp "
            f"{r.sharpe:>+7.3f} {r.dd:>+7.2f} {r.trades:>7d} {r.win:>5.1f}%{win_flag}"
        )

    # Summary statistics
    n = len(rows)
    n_wins = sum(1 for r in rows if r.outperf > 0)
    n_pos_sharpe = sum(1 for r in rows if r.sharpe > 0)
    n_degen = sum(1 for r in rows if r.trades < 5)
    avg_outperf = sum(r.outperf for r in rows) / n
    avg_sharpe = sum(r.sharpe for r in rows) / n
    avg_dd = sum(r.dd for r in rows) / n
    avg_trades = sum(r.trades for r in rows) / n

    print("-" * 75)
    print(f"Summary across {n} stocks:")
    print(f"  PPO beats B&H:          {n_wins}/{n} ({n_wins / n * 100:.1f}%)")
    print(f"  Positive Sharpe:        {n_pos_sharpe}/{n} ({n_pos_sharpe / n * 100:.1f}%)")
    print(f"  Degenerate (<5 trades): {n_degen}/{n}")
    print(f"  Average outperformance: {avg_outperf:+.2f}pp")
    print(f"  Average Sharpe:         {avg_sharpe:+.3f}")
    print(f"  Average max DD:         {avg_dd:+.2f}%")
    print(f"  Average trade count:    {avg_trades:.1f}")

    # Top 5 wins by outperformance
    if n_wins > 0:
        print()
        print("Top winners by outperformance vs B&H:")
        for r in rows[: min(5, n_wins)]:
            if r.outperf <= 0:
                break
            print(
                f"  {r.stock:<12} +{r.outperf:>6.2f}pp   Sharpe {r.sharpe:+.3f}   "
                f"DD {r.dd:+.2f}%   trades {r.trades}"
            )


if __name__ == "__main__":
    main()
