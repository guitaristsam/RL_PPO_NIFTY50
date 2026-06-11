"""
significance.py — statistical significance of PPO-vs-B&H outperformance.

A stock "beating B&H" in one backtest window says nothing by itself: with 50
stocks, ~2.5 spurious winners at p<0.05 are expected by chance alone. This
script tests, per stock, whether the strategy's DAILY ACTIVE RETURN
(r_ppo,t − r_bh,t) is significantly positive, using three complementary
methods, then applies a multiple-testing correction across the universe:

  1. Newey-West t-test. Paired t-test on daily active returns with a
     HAC (Bartlett-kernel) variance to absorb autocorrelation. One-sided
     H1: mean active return > 0.
  2. Circular block bootstrap (block = 20 trading days, B = 2000, seeded).
     Blocks preserve short-range autocorrelation that an iid bootstrap
     destroys. p = fraction of mean-centered bootstrap means >= observed.
     Also reports a 95% CI on annualized outperformance.
  3. Probabilistic Sharpe Ratio (Bailey & López de Prado 2012). Probability
     that the true Sharpe of the active-return series exceeds 0, corrected
     for skewness and kurtosis (daily P&L is fat-tailed; a plain Sharpe
     t-test overstates significance).
  4. Benjamini-Hochberg FDR across stocks on the bootstrap p-values —
     which "winners" survive when you account for having tried 50 stocks.

B&H daily returns are close-to-close on the same test dates as the PPO
account-value series. Entry/exit transaction costs shift the B&H level, not
the shape of its daily-return series, so they are irrelevant to these tests
(the project's reported B&H *returns* do include costs; see
calculate_buy_and_hold).

CAVEAT (documented, not solved here): these p-values treat each stock's
backtest as a single pre-registered trial. They do NOT correct for the ~20
strategy versions explored before settling on the current baseline; for
that you would need the Deflated Sharpe Ratio with the full trial record.
Treat surviving-FDR stocks as "worth a forward test", not as proven edge.

Usage:
    python significance.py                  # results/
    python significance.py results_v18      # any results dir
    python significance.py results_v18 --fdr 0.10
"""

import argparse
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

DATA_DIR = os.environ.get(
    "NIFTY50_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"),
)
BLOCK_LEN = 20          # ~1 trading month
N_BOOT = 2000
SEED = 42
MIN_OBS = 60            # below this the asymptotics are junk; skip stock


def load_active_returns(results_dir, symbol):
    """Daily active returns (ppo − b&h) on the stock's test dates, or None."""
    av_path = os.path.join(results_dir, symbol, "account_value.csv")
    px_path = os.path.join(DATA_DIR, f"{symbol}_daily.csv")
    if not (os.path.isfile(av_path) and os.path.isfile(px_path)):
        return None
    av = pd.read_csv(av_path)
    if not {"account_value", "date"} <= set(av.columns) or len(av) < MIN_OBS:
        return None
    av["date"] = pd.to_datetime(av["date"])

    px = pd.read_csv(px_path)
    # Raw bars carry an intraday timestamp (09:15:00); account dates are
    # midnight. Compare on calendar dates.
    px["datetime"] = pd.to_datetime(px["datetime"]).dt.normalize()
    px = px.set_index("datetime").sort_index()
    close = px["close"].reindex(pd.to_datetime(av["date"]).dt.normalize().values)
    if close.isna().any():
        # Date mismatch between account series and raw data — bail loudly.
        print(f"  {symbol}: {int(close.isna().sum())} test dates missing from "
              f"price file — skipped")
        return None

    r_ppo = av["account_value"].to_numpy(dtype=np.float64)
    r_ppo = np.diff(r_ppo) / np.maximum(r_ppo[:-1], 1e-9)
    r_bh = close.to_numpy(dtype=np.float64)
    r_bh = np.diff(r_bh) / np.maximum(r_bh[:-1], 1e-9)
    return r_ppo - r_bh


def newey_west_pvalue(d):
    """One-sided p for mean(d) > 0 with Bartlett-kernel HAC variance."""
    n = len(d)
    mu = float(np.mean(d))
    e = d - mu
    lag = int(np.floor(1.5 * n ** (1 / 3)))
    lrv = float(np.dot(e, e)) / n
    for k in range(1, lag + 1):
        w = 1.0 - k / (lag + 1.0)
        lrv += 2.0 * w * float(np.dot(e[k:], e[:-k])) / n
    if lrv <= 0:
        return mu, np.nan, np.nan
    t = mu / np.sqrt(lrv / n)
    p = float(stats.norm.sf(t))
    return mu, t, p


def block_bootstrap(d, rng):
    """Circular block bootstrap of the mean. Returns (one-sided p, ci_lo, ci_hi)
    where the CI is on the mean daily active return."""
    n = len(d)
    mu = float(np.mean(d))
    n_blocks = int(np.ceil(n / BLOCK_LEN))
    starts = rng.integers(0, n, size=(N_BOOT, n_blocks))
    idx = (starts[:, :, None] + np.arange(BLOCK_LEN)[None, None, :]) % n
    samples = d[idx.reshape(N_BOOT, -1)[:, :n]]
    means = samples.mean(axis=1)
    # Center under H0 (true mean 0): how often does a zero-mean world
    # produce an average at least as large as observed?
    p = (1.0 + float(np.sum(means - mu >= mu))) / (N_BOOT + 1.0)
    ci_lo, ci_hi = np.percentile(means, [2.5, 97.5])
    return p, float(ci_lo), float(ci_hi)


def probabilistic_sharpe(d):
    """PSR: P(true Sharpe of active returns > 0), non-normality corrected."""
    n = len(d)
    sd = float(np.std(d, ddof=1))
    if sd <= 0:
        return np.nan
    sr = float(np.mean(d)) / sd                      # daily Sharpe
    skew = float(stats.skew(d))
    kurt = float(stats.kurtosis(d, fisher=False))    # normal -> 3
    denom = 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr ** 2
    if denom <= 0:
        return np.nan
    return float(stats.norm.cdf(sr * np.sqrt(n - 1) / np.sqrt(denom)))


def benjamini_hochberg(pvals, q):
    """Indices of hypotheses rejected at FDR q."""
    order = np.argsort(pvals)
    m = len(pvals)
    keep = -1
    for rank, i in enumerate(order, start=1):
        if pvals[i] <= q * rank / m:
            keep = rank
    return set(order[:keep]) if keep > 0 else set()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results_dir", nargs="?", default="results")
    ap.add_argument("--fdr", type=float, default=0.05)
    args = ap.parse_args()
    if not os.path.isdir(args.results_dir):
        sys.exit(f"results directory '{args.results_dir}' not found.")

    rng = np.random.default_rng(SEED)
    rows = []
    for sym in sorted(os.listdir(args.results_dir)):
        if not os.path.isdir(os.path.join(args.results_dir, sym)):
            continue
        d = load_active_returns(args.results_dir, sym)
        if d is None:
            continue
        mu, t_nw, p_nw = newey_west_pvalue(d)
        p_boot, ci_lo, ci_hi = block_bootstrap(d, rng)
        psr = probabilistic_sharpe(d)
        rows.append({
            "stock": sym, "n": len(d),
            "ann_outperf_pp": mu * 252 * 100,
            "ci_lo_pp": ci_lo * 252 * 100, "ci_hi_pp": ci_hi * 252 * 100,
            "t_nw": t_nw, "p_nw": p_nw, "p_boot": p_boot, "psr": psr,
        })

    if not rows:
        sys.exit(f"No usable account_value.csv series under {args.results_dir}/.")

    rows.sort(key=lambda r: r["p_boot"])
    print(f"{'stock':<12} {'n':>5} {'annOut':>8} {'95% CI (ann pp)':>20} "
          f"{'t_NW':>6} {'p_NW':>7} {'p_boot':>7} {'PSR':>6}")
    print("-" * 80)
    for r in rows:
        print(f"{r['stock']:<12} {r['n']:>5d} {r['ann_outperf_pp']:>+7.1f}p "
              f"[{r['ci_lo_pp']:>+7.1f}, {r['ci_hi_pp']:>+7.1f}]    "
              f"{r['t_nw']:>+6.2f} {r['p_nw']:>7.3f} {r['p_boot']:>7.3f} "
              f"{r['psr']:>6.3f}")

    pvals = np.array([r["p_boot"] for r in rows])
    survivors = benjamini_hochberg(pvals, args.fdr)
    print("-" * 80)
    n_nominal = int(np.sum(pvals < 0.05))
    print(f"Nominal p_boot < 0.05:        {n_nominal}/{len(rows)} "
          f"(~{0.05 * len(rows):.1f} expected by chance)")
    names = sorted(rows[i]["stock"] for i in survivors)
    print(f"Survive BH-FDR at q={args.fdr}:    "
          f"{len(survivors)}/{len(rows)}"
          + (f"  -> {', '.join(names)}" if names else ""))
    print("\nReminder: no correction here for the ~20 strategy versions tried "
          "before this one.\nFDR survivors are candidates for a forward test, "
          "not proven edge.")


if __name__ == "__main__":
    main()
