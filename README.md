# PPO Trading on NIFTY50 — Out-of-Sample, Leakage-Audited

A single-stock RL trading system trained with **RecurrentPPO (LSTM)** on every NIFTY50 equity, evaluated out-of-sample on a 70/15/15 train/val/test chronological split. The interesting part isn't the algorithm — it's the bug-hunt that shipped it.

## Headline results (50 stocks, 200k timesteps each)

| Metric | Value | What it means |
|---|---|---|
| **PPO beats Buy&Hold** | **7 / 50** (14%) | comparable to honest RL-trading papers |
| **Positive Sharpe** | **31 / 50** (62%) | majority of stocks are risk-adjusted profitable |
| **Average Sharpe** | **+0.279** | positive on the universe |
| **Average max drawdown** | **−24.6%** | roughly half of B&H's typical −40% to −70% on these stocks |
| **Degenerate runs** | **1 / 50** | resume-guard + warmup gate caught the rest |

**Top 5 winners by outperformance vs Buy & Hold (out-of-sample, ~3.5-yr test windows):**

| Stock | PPO Return | B&H Return | Outperf | Sharpe | Max DD | Trades |
|---|---|---|---|---|---|---|
| ADANIENT | +45.21% | −21.61% | **+66.83pp** | +0.638 | −17.0% | 94 |
| ITC | +145.97% | +105.88% | **+40.09pp** | **+1.359** | −15.1% | 161 |
| ETERNAL | +10.72% | −9.13% | +19.85pp | +0.343 | −28.2% | 24 |
| ONGC | +57.21% | +43.92% | +13.29pp | +0.768 | −32.9% | 63 |
| INDUSINDBK | +12.51% | 0.00% | +12.51pp | −0.028 | −34.3% | 69 |

ITC — Sharpe **1.36** with a **−15% max drawdown** over a 3.5-year out-of-sample window — is institutional-grade.
ADANIENT navigated the 2023 Hindenburg crash (B&H **−22%**) and ended the test window at **+45%**.

## Why this project is interesting

**The bug-hunt is the story.** v6's first results were +1946% returns and Sharpe 6.58 — too good to be true. They were. Tracking down the fakes took 13 systematic single-variable iterations:

| Bug | Versions | Symptom | Root cause |
|---|---|---|---|
| **Lookahead-leakage indicators** | v6→v8 | +1946% returns, Sharpe 6.58 | `pandas-ta`'s `DPO_20`, `AMATe_*`, `AOBV_*`, `PSARr`, `STC_*`, etc. default to `lookahead=True` or use centered moving averages |
| **State-layout swap** | v6→v8 | budget clamp was a no-op; trade log reported "1646 shares" of next-day close prices | `IntegerTradingEnv` read `state[1]` thinking it was holdings, but in `FinRL`'s layout that's *price*. Holdings are at `state[1+stock_dim]`. |
| **Action-scaling collapse** | v6→v8 | policy `std` stuck at 0.97 forever; agent had no fine-grained action | Override rounded the raw `[-1, 1]` action to int **before** `super().step()`'s `*hmax` scaling, collapsing every action into `{−2, −1, 0, 1, 2}` |
| **bfill across train/test boundary** | v7→v8 | minor leakage of future indicator values into past bars | `df.fillna(method='bfill')` after the chronological split |

After fixing those (v8) the numbers became honest. Subsequent versions (v9–v18) added **only one variable at a time** — RecurrentPPO, log-return reward, drawdown penalty, validation split with early stopping, warmup gate. Several of those (v10 DSR, v11 regularization, v13/v14 deepening DD, v15 longer training) regressed and got rolled back. The version diary documents exactly which ones and why.

The full version-by-version history is in [`CLAUDE.md`](CLAUDE.md).

## Architecture

- **Environment**: `IntegerTradingEnv` (subclass of FinRL's `StockTradingEnv`) — integer share quantities, budget-clamped, non-negative positions.
- **Policy**: `RecurrentPPO("MlpLstmPolicy")` from `sb3-contrib`. Separate actor/critic LSTMs, hidden size 128, 1 layer.
- **Observation**: 1 cash + 1 price + 1 holdings + 98 technical indicators (lookahead-audited subset of pandas-ta), wrapped in `VecNormalize` for full-state scaling.
- **Action**: continuous in `[−1, 1]`, scaled by per-stock `hmax = floor(10000 / median_train_price)` clamped to `[2, 200]`.
- **Reward**: `clip(log(equity_t / equity_{t-1}) × 100, −10, 10) − DD_penalty`, where `DD_penalty = max(0, drawdown − 0.10)`.
- **Costs**: 0.25% per side.
- **Split**: 70% train, 15% validation, 15% test — chronological per stock.
- **Early stopping**: custom `ValidationCallback` evaluates every 50k steps (after a 100k warmup), runs the deterministic policy through the val window, saves the best checkpoint by val-portfolio-return; restores it for test.

## Quick start

Requires Python 3.10+ on Windows / Linux / Mac. NIFTY50 OHLCV daily CSVs are not in this repo (they're proprietary); set the `NIFTY50_PATH` constant in `Rl_v18.py` to point to your own directory of `{SYMBOL}_daily.csv` files with columns `datetime, open, high, low, close, volume`.

```bash
# 1. install
pip install -r requirements.txt

# 2. run all 50 stocks (~10 hours of compute)
python Rl_v18.py

# 3. or one stock for fast iteration (~12 minutes)
python -c "from Rl_v18 import process_stock, NIFTY50_PATH; import os; \
  process_stock(os.path.join(NIFTY50_PATH, 'RELIANCE_daily.csv'))"

# 4. summarize results (after step 2 or 3)
python summarize_results.py

# 5. static leakage audit (always passes if the indicator list is clean)
python test_indicator_audit.py
```

## Repository layout

```
Rl_v18.py                  current best baseline (run this)
Rl_v6.py … Rl_v17.py       version diary — frozen, kept for the story
Rl_v19.py … Rl_v23.py      designed but unrun variants (B&H-relative reward,
                           val-Sharpe, target-exposure action, ensemble seeds,
                           finer warmup) — see variants.md
v9_batch.py … v18_batch.py curated 5–7 stock subsets for fast iteration
ensemble_predict.py        averages N v22-style trained seeds at test time
summarize_results.py       post-run portfolio-level aggregation
test_indicator_audit.py    static unittest preventing leakage regressions
CLAUDE.md                  full version diary (v6 → v18) + bug history
variants.md                v19–v23 hypotheses + run commands + diagnostics
README.md                  this file
```

## Limitations

- **Single-stock environment.** Each PPO is trained per ticker. Cross-asset signals, sector context, and portfolio-level position sizing are out of scope.
- **Daily bars only.** No intraday data, no market microstructure.
- **Public TA features only.** No fundamentals, alternative data, news, sentiment, or order-book features.
- **Long-only.** No shorts.
- **Fixed costs.** 0.25% per side; doesn't model market impact or slippage on illiquid names.
- **Backtest, not paper-trading.** The gap from backtest to live execution is large; this is a research artifact, not a deployable strategy.
- **NIFTY50 universe specifically.** Generalization to other markets / timeframes is not claimed.

## What this project demonstrates

For a CV/portfolio context, the explicit signal is:

- **Quantitative discipline** — chronological splits, lookahead audits, single-variable A/B testing, validation-set early stopping.
- **Honest reporting** — losing stocks shown alongside winning ones; sweep average is reported even though it's negative.
- **Systems debugging** — finding the FinRL state-layout bug, the action-scaling double-multiply, the pandas-ta default-`lookahead=True` traps.
- **Reproducibility** — every saved model has its corresponding `VecNormalize` stats serialized; resume guard means partial runs can be continued without reprocessing.
- **Iterative engineering** — 13 versions, each isolated to one variable; failed variants kept on disk so the reasoning is auditable.

Most public RL-trading repos quietly contain leakage. This one was built to find it.

## License

MIT — see [`LICENSE`](LICENSE).

## Acknowledgements

- [`stable-baselines3`](https://github.com/DLR-RM/stable-baselines3) and [`sb3-contrib`](https://github.com/Stable-Baselines-Team/stable-baselines3-contrib) for PPO and RecurrentPPO.
- [`FinRL`](https://github.com/AI4Finance-Foundation/FinRL) for `StockTradingEnv` (subclassed and patched here).
- [`pandas-ta`](https://github.com/twopirllc/pandas-ta) for the indicator universe — and for the `lookahead=True` defaults that caused the original leakage hunt.
