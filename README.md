# RL_PPO_NIFTY50

PPO + LSTM trading agent on NIFTY50 daily bars. One model per stock, 70/15/15 chronological train/val/test, validation-based early stopping. 200k timesteps each, ~12 minutes on a single CPU core.

## Results across the 50-stock universe

| | |
|---|---|
| Beats Buy & Hold | 7 / 50 |
| Positive Sharpe | 31 / 50 |
| Average Sharpe | +0.279 |
| Average max drawdown | -24.6% |
| Degenerate runs (< 5 trades) | 1 / 50 |

Top 5 stocks by outperformance vs Buy & Hold (test windows ≈ 3.5 years):

| Stock | PPO | B&H | Outperf | Sharpe | Max DD | Trades |
|---|---|---|---|---|---|---|
| ADANIENT | +45.21% | -21.61% | +66.83pp | 0.64 | -17.0% | 94 |
| ITC | +145.97% | +105.88% | +40.09pp | 1.36 | -15.1% | 161 |
| ETERNAL | +10.72% | -9.13% | +19.85pp | 0.34 | -28.2% | 24 |
| ONGC | +57.21% | +43.92% | +13.29pp | 0.77 | -32.9% | 63 |
| INDUSINDBK | +12.51% | 0.00% | +12.51pp | -0.03 | -34.3% | 69 |

ITC has Sharpe 1.36 with max DD only -15% over a 3.5-year out-of-sample window. ADANIENT held through the 2023 Hindenburg crash (B&H -22%) and ended at +45%.

Per-stock reports, account value series, and trade logs are under `results/`. Run `python summarize_results.py` for the full sorted table.

## Bugs that mattered

The first version produced +1946% returns and Sharpe 6.58 on ADANIPORTS. None of it was real. Each fix was isolated to one variable.

| Bug | Symptom | Cause |
|---|---|---|
| Lookahead indicators | Sharpe 6+ across the board | pandas-ta's DPO, AMATe, AOBV, PSARr, STC default to `lookahead=True` or use centered windows |
| State-layout swap | Budget clamp was a no-op; trade log reported "1646 shares" | The `IntegerTradingEnv` override read `state[1]` thinking it was holdings. In FinRL's layout `state[1]` is price; holdings are at `state[1+stock_dim]`. |
| Action scaling | Policy std stuck at 0.97; agent could only output {-2,-1,0,1,2} after rounding | Override rounded the [-1,1] action to int *before* `super().step()` multiplied by `hmax`. |
| bfill across split | Future indicator values bled into past bars | `fillna(method='bfill')` ran on the union frame after the chronological split. |

After v8 the numbers became honest. v9 swapped to RecurrentPPO with a log-return reward (RELIANCE went from -40% to +68% on this change alone). v12 added a drawdown penalty (+21pp average across 8 stocks). v16 introduced the validation callback (first PPO-beats-B&H result on ITC). v18 added a 100k-step warmup before the first val eval, which fixed the "lucky early checkpoint" failure mode and produced the second B&H-beating stock (ADANIENT).

Several variants regressed and were rolled back: differential-Sharpe reward (v10), lighter regularization (v10/v11), deepening-only DD penalty (v13/v14), 5x longer training (v15). Each one is on disk; CLAUDE.md has the diff and reasoning.

## Architecture

- `IntegerTradingEnv` extends `FinRL.StockTradingEnv`. Integer share quantities, budget-clamped, no shorting.
- `RecurrentPPO("MlpLstmPolicy")` from `sb3-contrib`. Hidden size 128, separate actor and critic LSTMs.
- Observation: cash + price + holdings + 98 lookahead-audited pandas-ta indicators, all wrapped in `VecNormalize`.
- Action: continuous `[-1, 1]`, scaled by `hmax = floor(10000 / median_train_close)` clamped to `[2, 200]`.
- Reward: `clip(log(eq_t / eq_{t-1}) * 100, -10, 10) - max(0, drawdown - 0.1)`.
- Costs: 0.25% per side.
- Validation callback evaluates every 50k steps after a 100k warmup, runs the deterministic policy through the val window, and saves the best-val checkpoint.

## Quick start

Python 3.10+. The 50 daily OHLCV CSVs ship under `data/` (~23 MB).

```bash
pip install -r requirements.txt

# full 50-stock sweep (~10 hours on CPU)
python Rl_v18.py

# one stock for fast iteration
python -c "from Rl_v18 import process_stock, NIFTY50_PATH; import os; \
  process_stock(os.path.join(NIFTY50_PATH, 'RELIANCE_daily.csv'))"

python summarize_results.py        # post-run aggregation
python test_indicator_audit.py     # static leakage check
```

To use your own data instead of the bundled CSVs, set `NIFTY50_PATH` to a directory of `{SYMBOL}_daily.csv` files with columns `datetime, open, high, low, close, volume`.

## Layout

```
Rl_v18.py                 current baseline
Rl_v6.py … Rl_v17.py      version history (frozen)
Rl_v19.py … Rl_v23.py     unrun forks of v18 — see variants.md
v9_batch.py … v18_batch.py   curated stock subsets
ensemble_predict.py       averages N v22 seeds at test time
summarize_results.py      portfolio-level aggregation
test_indicator_audit.py   regression test for leakage names
data/                     50 NIFTY50 daily OHLCV CSVs
results/                  reports + trade logs from the latest sweep
CLAUDE.md                 version diary, bug history, hyperparameters
variants.md               v19–v23 hypotheses, run commands, diagnostics
```

## Limitations

Single-stock environment per agent (no portfolio context, no cross-asset signals). Daily bars only. Long-only. Public TA features only, no fundamentals or alternative data. Fixed transaction costs at 0.25% per side; no market-impact or slippage modeling. Backtest only. NIFTY50 universe; no claim of generalization to other markets.

## License

MIT.
