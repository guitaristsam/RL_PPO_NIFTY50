# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Working notes on the RL_PPO_NIFTY50 codebase. Useful when picking up the project after a break or when bringing a new tool/agent up to speed.

## Project state

Single-file PPO trading system for NIFTY50 daily bars. The codebase has gone through 18 versions; **`Rl_v18.py` is the current baseline**. Earlier versions stay on disk so the bug-hunt is auditable. Don't edit them.

| File | Status | Notes |
|---|---|---|
| `Rl_v6.py` / `Rl_v6.ipynb` | frozen | original, multiple bugs documented below |
| `Rl_v7.py` | frozen | v6 + memory caps + price-aware hmax + VecNormalize |
| `Rl_v8.py` | frozen | v7 + indicator-leakage pruning + state-layout fix + action-scaling fix + B&H benchmark fix |
| `Rl_v9.py` | frozen | v8 + RecurrentPPO (LSTM) + log-return reward |
| `Rl_v10.py` | frozen | v9 + DSR reward + regularization. Failed: VL=85, clip_frac=1e-4. |
| `Rl_v11.py` | frozen | v9 + log-return reward + DD penalty + regularization. Failed: std grew, clip_frac=7e-4. |
| `Rl_v12.py` | frozen | v9 + DD penalty only. 6/8 stock-level wins vs v9. |
| `Rl_v13.py` | frozen | v12 + deepening-only DD (λ=20). Failed: RELIANCE +16% vs v12 +85%. |
| `Rl_v14.py` | frozen | v13 with λ=5. Better than v13, still 40pp behind v12. |
| `Rl_v15.py` | frozen | v12 + 1M timesteps (5×). Failed: RELIANCE +74% vs v12 +85%. Direct overfit (std halved, EV pegged at 0.99, test return dropped). |
| `Rl_v16.py` | frozen | v12 + 70/15/15 split + custom `ValidationCallback` (eval_freq=50k). First PPO-beats-B&H result (ITC +40pp, Sharpe 1.36). Failure modes: HDFCBANK degenerate at val@50k; INFY late-training overfit at val@200k. |
| `Rl_v17.py` | frozen | v16 + min_val_trades=5 on val checkpoints. No effect on HDFCBANK. The val@50k checkpoint had 29 val trades; degeneracy was test-side. |
| `Rl_v18.py` | **current** | v17 + warmup_steps=100k. Skips the first val eval to avoid lucky early checkpoints. Second PPO-beats-B&H stock (ADANIENT +66.8pp, Sharpe 0.64). |
| `Rl_v19.py` | unrun queue | v18 + B&H-relative reward (`reward -= log(close_t/close_{t-1})`). Hypothesis: explicit alpha gradient. |
| `Rl_v20.py` | unrun queue | v18 + best-by-Sharpe in `ValidationCallback`. Targets high-variance lucky-long val winners (INFY-style). |
| `Rl_v21.py` | unrun queue | v18 + target-exposure action. Action `(a+1)/2 ∈ [0,1]` is target capital fraction; env computes share-delta. |
| `Rl_v22.py` | unrun queue | v18 + `seed_offset` parameter. Each seed saves to `{stock}_seed{N}_*`. Companion `ensemble_predict.py` averages N continuous actions per step. |
| `Rl_v23.py` | unrun queue | v18 + warmup=150k, eval_freq=25k. All eligible evals at 150k/175k/200k. |
| `ensemble_predict.py` | helper | Loads N v22-style models for one stock, averages continuous actions on a shared eval env. ~110 lines. Depends on SB3's `VecNormalize.normalize_obs/unnormalize_obs`. |
| `Rl_v24.py` | unrun queue (smoke-tested) | Pooled cross-stock training: one policy over all NIFTY50 stocks, random 252-bar episode windows, `PooledValidationCallback` scoring mean val return over the 10-stock panel. 2M timesteps. Outputs to `results_v24/` / `models_v24/`. 3-stock/20k-step smoke run passed end-to-end 2026-06-11. |
| `run_panel.py` | helper | Runs one `Rl_vN` variant over the fixed 10-stock comparison panel; redirects outputs to `results_<ver>/`, `models_<ver>/` via env vars. |
| `variants.md` | docs | One section per v19–v24. Hypothesis, code change summary, run command, diagnostic. Plus a DESIGN ONLY v25 proposal (DD-deepening-from-max). |
| `summarize_results.py` | helper | After a run, parses every `results/{SYMBOL}/{SYMBOL}_report.txt` and prints a sorted outperformance table. |
| `significance.py` | helper | Statistical significance of daily active returns (PPO − B&H) per stock: Newey-West t-test, circular block bootstrap (p + 95% CI), Probabilistic Sharpe Ratio, then Benjamini-Hochberg FDR across stocks. On the pre-fix 50-stock sweep: 1/49 nominal p<0.05 (~2.5 expected by chance), 0/49 survive FDR — no statistically demonstrable edge yet. Does NOT correct for the ~20 versions tried (would need Deflated Sharpe with the full trial record). |
| `test_indicator_audit.py` | test | Unittest. Fails if any of v8–v24's `list_of_indicators` includes a known-leakage name. v6/v7 are exempt. |
| `test_indicator_causality.py` | test | Dynamic leakage audit: computes kept indicators on the train prefix alone vs the full series and asserts prefix equality (causal indicators can't change when future rows are appended). One stock (RELIANCE, `CAUSALITY_SYMBOL` to override). Run when bumping pandas-ta or editing the indicator list. |
| `test_variant_envs.py` | test | Env-level math checks, no training: v19's B&H-relative reward recomputed from env internals at every step; v21's target-exposure mapping (a=+1 full-in, a=−1 liquidate, a=0 half). ~25 s. |
| `v9_batch.py` / `v12_batch.py` / `v16_batch.py` / `v18_batch.py` | helper | run `process_stock` on a curated subset |

## Running

```bash
# full 50-stock alphabetical sweep
python Rl_v18.py

# small batch (5 stocks targeted at v16's failure modes)
python v18_batch.py

# one-stock ad-hoc
python -c "from Rl_v18 import process_stock, NIFTY50_PATH; import os; \
  process_stock(os.path.join(NIFTY50_PATH, 'RELIANCE_daily.csv'))"

# fixed 10-stock comparison panel for any variant; outputs go to
# results_<ver>/ models_<ver>/ so runs never collide with the baseline
python run_panel.py v18
python run_panel.py v22 --seeds 3      # v22 only: trains seed offsets 0..2

# v24 (pooled) runs standalone — run_panel refuses it by design
python Rl_v24.py
# v24 smoke test (~5 min): 3 stocks, 20k steps
V24_STOCKS="RELIANCE,INFY,ITC" TOTAL_TIMESTEPS=20000 V24_WARMUP=0 \
  V24_EVAL_FREQ=10000 python Rl_v24.py
```

Aggregation and comparison:

```bash
python summarize_results.py                          # sorted table for results/
python summarize_results.py results_v18              # ...or any results dir
python summarize_results.py results_v18 results_v19  # per-stock outperformance deltas
python significance.py results_v18                   # p-values, CIs, PSR, FDR across stocks
```

Tests (no test runner config; each file runs directly):

```bash
python test_indicator_audit.py       # static leakage check, ~1 min (imports all versions)
python test_indicator_causality.py   # dynamic leakage audit, ~30 s, one stock
python test_variant_envs.py          # v19 reward / v21 action math vs env internals, ~25 s
```

`requirements.txt` has the pinned versions. `sb3-contrib` is what supplies `RecurrentPPO`.

Each `process_stock` call has a resume guard: if `results/{SYMBOL}/{SYMBOL}_report.txt` already exists, the stock is skipped (the run still parses the existing report so consolidation includes it). Delete that file to force a re-run.

## Pipeline (per stock, in `process_stock`)

1. Load `{SYMBOL}_daily.csv` from `NIFTY50_PATH`.
2. Compute ~300 pandas-ta indicators via `df.ta.study(ta.AllStudy, cores=0)` and filter to `list_of_indicators` (~98 names, pruned from v6's 118 to remove lookahead leakage).
3. `handle_nan_per_stock()`. Trim to the first row where all indicators are non-null. ffill only on prices and indicators (no bfill, that was a leak vector across the train/test boundary).
4. `prepare_data_for_finrl(..., skip_scaling=True)`. Format conversion only.
5. 70/15/15 chronological train/val/test split by date.
6. `prepare_data_for_finrl(train, scalers=None)` then `(test, scalers=fitted)`. RobustScaler fit on train.
7. `train_ppo_model()`. Wraps env in `DummyVecEnv` then `VecNormalize(norm_obs=True)` so the full state (cash, positions, prices, indicators) gets scaled, not just the indicators. Trains `RecurrentPPO("MlpLstmPolicy")` for 200k timesteps. The `ValidationCallback` runs the deterministic policy through the val window every 50k steps after a 100k warmup, saves the best-val checkpoint, and restores it at the end.
8. `test_ppo_model()`. Deterministic inference, threading `lstm_states` and `episode_starts` through `predict()`. Loads saved `VecNormalize` stats with `training=False`.
9. `create_comprehensive_report()`. Writes per-stock report (UTF-8), `account_value.csv`, `trades.csv` under `results/{SYMBOL}/`.
10. `generate_consolidated_report()`. Aggregates into `consolidated_report.txt`.

## Bugs already paid for, do not regress

### IntegerTradingEnv state layout

FinRL's `StockTradingEnv` lays out the state as:
```
state[0]                                = cash
state[1 : 1 + stock_dim]                = prices
state[1 + stock_dim : 1 + 2*stock_dim]  = shares
state[1 + 2*stock_dim : ...]            = indicator block
```

v6 and v7 read `state[1 : 1+stock_dim]` thinking it was holdings (it's prices) and computed a `price_index` via a tech-indicator stride that landed on the shares slot. The "near-zero price" warning fired on every reset because we were reading shares (=0). Our budget clamp was a no-op. Trade logs reported next-day close prices as if they were share counts. v8's `IntegerTradingEnv` caches `_price_slice` and `_shares_slice` from FinRL's true layout. Use those slices in any new code; `test_ppo_model` reads positions from `state[1+stock_dim : 1+2*stock_dim]` for the same reason.

### Action scaling

FinRL's parent `step()` does `actions = actions * self.hmax; actions = actions.astype(int)` (env_stocktrading.py:303). v6/v7's override rounded the raw `[-1, 1]` action to int *before* that scaling, collapsing every action into `{-2, -1, 0, 1, 2}` pre-scaling and `{-2*hmax, ..., 2*hmax}` post-scaling. Smoking gun: v6's policy std stuck at 0.97 forever, no gradient benefit to producing fine-grained actions.

v8's `IntegerTradingEnv._process_action` scales to integer shares first (`action_shares = round(raw_action * hmax).astype(int)`), validates budget and position constraints in shares-space, then `step()` divides by `hmax` so `super().step()`'s internal `*hmax` recovers the exact integer share count.

**Known residual wart (found 2026-06-11, present in v8–v24, NOT yet fixed):** the recovery is not always exact. FinRL truncates with `astype(int)`, and the float32 round-trip `n/hmax*hmax` lands just below `n` for ~4% of (hmax, n) pairs (e.g. hmax=23, n=7 executes 6; measured by census over hmax 2–200). Effect: occasional trades 1 share smaller than intended. No accounting corruption, but it violates the exact-recovery invariant. Fix when next re-baselining (changing it mid-experiment would contaminate v19-vs-v18 comparisons): nudge the rescaled action away from the truncation edge, `rescaled = (action_shares + 0.49 * np.sign(action_shares)) / hmax` — truncation toward zero then lands on the intended integer for both signs (verified: 0 mismatches over the same 40,397-pair census).

### Lookahead-leakage indicators

v6/v7 included indicators with `lookahead=True` defaults or center-aligned smoothing. ADANIPORTS reported 1946% return and Sharpe 6.58 over a 3.5-year test, all leakage. Names removed in v8: `DPO_20`, `AMATe_LR_8_21_2`, `AMATe_SR_8_21_2`, `AOBV_LR_2`, `AOBV_SR_2`, `PSARr_0.02_0.2`, `TTM_TRND_6`, `DEC_1`, `INC_1`, `STC_10_12_26_0.5`, `STCmacd_10_12_26_0.5`, `STCstoch_10_12_26_0.5`, `FISHERTs_9_1`, `EBSW_40_10`, `COPC_11_14_10`. `test_indicator_audit.py` enforces this for v8 onward.

### NaN handling

bfill across the train/test split propagates future values backward. v8 uses ffill only in three places (`handle_nan_per_stock` prices, `prepare_data_for_finrl` tech indicators, `prepare_data_for_finrl` OHLCV). Residual NaN gets filled with 0 for indicators (RobustScaler median) or per-split median for prices.

### Buy-and-hold benchmark

v6/v7 computed B&H with fractional shares and no transaction costs, giving B&H a structural edge over PPO. v8's `calculate_buy_and_hold` uses integer shares, applies buy/sell costs, keeps residual cash.

### Reward function

v8 used FinRL's default rupee-ΔP&L scaled by `reward_scaling`. Fragile across price regimes.

v9 replaced it with `clip(log(eq_t/eq_{t-1}) * 100, -10, 10)`. Scale-invariant. Single biggest improvement of the project: RELIANCE went from -40% to +68% on this change alone (108pp swing).

v12 keeps v9's primary reward and subtracts a mild drawdown penalty: `reward = primary - 1.0 * max(0, drawdown - 0.10)`. Net win, +21pp average across 7 stocks.

v10 (Moody-Saffell DSR) regressed. The `(B - A²)^(3/2)` denominator detonates in low-vol windows; value_loss exploded to 85, clip_fraction collapsed to 1e-4. v11 added regularization to v10's reward and also regressed: explained_variance dropped from 0.99 to 0.80 (better) but std grew and clip_fraction collapsed (worse). The regularization on its own is what hurt; v12 confirmed by isolating only the DD penalty change.

### Date alignment in `test_ppo_model`

FinRL's `step()` advances `self.day` and updates state to the new day's price after the trade settles. v6/v7 paired the post-step `total_asset` with `unique_dates[step_count]` (which was already the old day at that point). Off by one. v8 records the initial value at `unique_dates[0]` before the loop and pairs each post-step value with `unique_dates[step_count]` after incrementing.

### Other small things

- Global RNG seeding (`random`, `np.random`, `torch.manual_seed`) at the start of every `process_stock`. v6/v7 only seeded PPO.
- Memory caps at top of file (`OMP/MKL/OPENBLAS/NUMEXPR_NUM_THREADS=1`, `torch.set_num_threads(1)`, `df.ta.cores = 0`). The Windows page file blew up when pandas-ta multiprocessed and each worker re-imported numpy + TF.
- `print_verbosity=1000` on the env. v6 was 5, which produced ~75 spam lines per stock.
- Report files opened with `encoding='utf-8'`; emojis like 📊 crash the default cp1252 codec.
- `_near_zero_warned` flag: print the price-clamp warning at most once per env.

## Key classes (v18)

- `IntegerTradingEnv` extends `StockTradingEnv`. Integer share quantities, budget constraints, non-negative positions. Caches `_price_slice` and `_shares_slice` for the FinRL state layout. Overrides `step()` to compute the log-return reward minus the drawdown penalty.
- `ValidationCallback`. Periodic deterministic eval on the val window. Saves best-val checkpoint, applies `min_val_trades` and `warmup_steps` filters.
- `TradeLogger`. Detects buy/sell from position deltas, tracks weighted-average buy price per symbol, computes win rate on sell trades.

## Constants

| Constant | Value | Notes |
|---|---|---|
| `NIFTY50_PATH` | `<repo>/data/` | Override via env var. v18 onward; older versions had it hardcoded. |
| `MIN_DATA_ROWS` | 252 | Stocks below this are skipped after cleaning. |
| `hmax` | `floor(initial_amount / median_train_close)`, clamped to `[2, 200]` | v6 used a fixed `hmax=10` which collapsed action resolution on high-priced stocks. |
| `buy/sell_cost_pct` | 0.0025 | 0.25% per side. |
| `initial_amount` | ₹10,000 per stock |  |
| `total_timesteps` | 200,000 | v15 (1M) showed direct overfit; 200k is what the val callback can early-stop within. |

## Hyperparameters (RecurrentPPO)

`learning_rate=3e-4`, `n_steps=512`, `batch_size=64` (must divide `n_steps * n_envs`), `n_epochs=5`, `gamma=0.99`, `gae_lambda=0.95`, `clip_range=0.2`, `ent_coef=0.01`, `vf_coef=0.5`, `max_grad_norm=0.5`, `seed=42`. `policy_kwargs={"lstm_hidden_size": 128, "n_lstm_layers": 1, "shared_lstm": False, "enable_critic_lstm": True, "net_arch": [128], "activation_fn": Tanh}`.

## Empirical baselines (200k timesteps)

### v18 small batch (5 stocks; ITC is the control)

| Stock | v18 PPO | v18 B&H | v18 Outperf | v16 Outperf | Δ vs v16 | v18 Sharpe | v18 DD | Trades |
|---|---|---|---|---|---|---|---|---|
| ADANIENT | +45.21% | -21.61% | +66.83pp | -2.91pp | +69.7pp | +0.64 | -17.0% | 94 |
| ITC (ctrl) | +145.97% | +105.88% | +40.09pp | +40.09pp | 0 | +1.36 | -15.1% | 161 |
| TCS | -3.72% | +4.81% | -8.53pp | -11.02pp | +2.5pp | -0.14 | -11.2% | 90 |
| ADANIPORTS | -2.05% | +62.06% | -64.11pp | -73.23pp | +9.1pp | -0.04 | -42.4% | 72 |
| HDFCBANK | -24.58% | +30.62% | -55.20pp | -30.62pp | -24.6pp | -0.86 | -31.2% | 90 |

ITC and ADANIENT both beat B&H. v18 average outperformance across these 5 is -4.2pp vs v16's -15.5pp (a +11.4pp lift). ITC reproduced exactly because its v16 checkpoint was saved at 150k, past the v18 warmup of 100k. HDFCBANK looks worse because v16 was a fake "lucky cash" win (do-nothing policy held cash through a flat val period); v18 reveals the underlying policy is genuinely losing.

### v16 prior baseline, 8 stocks

v16 uses a 70/15/15 split. v12 used 80/20 train/test. The val slice carves out the middle 15% so the test period in v16 is shorter and starts later than in v12. Direct return comparisons aren't apples-to-apples; compare via outperformance (PPO − B&H) instead.

| Stock | v16 PPO | v16 B&H | Outperf | v12 Outperf | Δ outperf | v16 Sharpe | v16 DD | Trades | Notes |
|---|---|---|---|---|---|---|---|---|---|
| RELIANCE | +31.58% | +68.47% | -36.89pp | -62.88pp | +26pp | +0.54 | -21.9% | 113 | clean win |
| ITC | +145.97% | +105.88% | +40.09pp | -73.60pp | +114pp | +1.36 | -15.1% | 161 | first PPO-beats-B&H |
| TATAMOTORS | +229.57% | +253.67% | -24.10pp | -356.43pp | +332pp | +0.94 | -38.9% | 78 | huge improvement |
| TCS | -6.21% | +4.81% | -11.02pp | -7.56pp | -3pp | -0.23 | -14.0% | 67 | flat |
| ADANIENT | -24.52% | -21.61% | -2.91pp | -0.55pp | -2pp | -0.39 | -46.1% | 55 | flat (v12 was a degenerate B&H mimic) |
| ADANIPORTS | -11.17% | +62.06% | -73.23pp | -80.81pp | +8pp | -0.35 | -17.1% | 55 | small win |
| HDFCBANK | 0.00% | +30.62% | -30.62pp | -42.59pp | +12pp | 0.00 | -1.5% | 11 | DEGENERATE: val saved a "do nothing" policy at 50k |
| INFY | -39.84% | +22.06% | -61.90pp | -119.97pp | +58pp | -0.66 | -48.8% | 206 | val@200k overfit; worse than v12 absolute return but better outperformance |

6/8 improve in outperformance vs v12. ITC is the first PPO-beats-B&H stock. Average max drawdown halved (v16 -25% vs v12 -46%). Average Sharpe roughly 3× higher (v16 +0.15 vs v12 +0.05).

### How the val callback works

Every 50k steps the callback runs the deterministic policy through the validation slice, records final portfolio return, and saves the model when val return improves. After training, the best-val checkpoint is restored and used for test.

v18 adds `warmup_steps=100000`. Evals before that step are skipped. Added after v17 (a min-val-trades=5 filter) failed to fix HDFCBANK: the val@50k checkpoint had 29 val trades (eligible) but was an under-trained "lucky long" capturing a transient val rally rather than skill. The warmup gate forces the first eligible checkpoint to be at val@100k or later.

Validation curves observed across batches:

- RELIANCE peaked at val@100k (+105%); training kept getting worse. Overfit confirmed.
- TATAMOTORS val crossed -60% to +0.5% between 50k and 150k.
- ITC val was negative throughout (-7%, then -6.86%); the saved policy then made +146% on test. Hard val period selected for discipline.
- ADANIENT val@50k was +191% (lucky-long during the 2020 bull). v18 skipped that and saved val@100k at +96%, which beat B&H by 67pp on test (B&H lost 22% post-Hindenburg).

### Known failure modes

- HDFCBANK looks feature-untrainable. v16 saved a "do nothing" policy at val@50k that produced 11 test trades and 0% return. It looked OK because the test period drifted up modestly while the policy held cash. v17 (min-val-trades) didn't change anything because val@50k had 29 val trades. v18 (warmup=100k) forced val@100k to be saved instead, producing a real but actively-losing policy (-24.58% test, 90 trades). The interpretation: there is no winning policy on HDFCBANK with the current feature set + reward; v16 was a false win. A real fix is feature-side (cross-asset signals, fundamentals) or reward-side (B&H-relative reward, see v19).
- Late-training overfit (INFY in the v16 batch): val@200k looked best but didn't generalize. Untouched by v17/v18. Would need a held-out "early test" slice or a different val signal (e.g. val Sharpe instead of val return, see v20).

## Training-curve diagnostics (batch run of 7 stocks at 391 iterations each)

| Stock | std₀ → std_T | EV₀ → EV_T | VL₀ → VL_T | clip_avg |
|---|---|---|---|---|
| ADANIENT | 1.00 → 0.88 | 0.00 → 0.99 | 49.7 → 1.3 | 0.10 |
| ADANIPORTS | 1.00 → 0.76 | -0.01 → 0.95 | 29.7 → 1.4 | 0.11 |
| TCS | 1.01 → 0.76 | 0.01 → 0.96 | 8.3 → 0.3 | 0.13 |
| HDFCBANK | 1.00 → 0.89 | -0.03 → 0.99 | 2.3 → 0.5 | 0.10 |
| INFY | 1.00 → 0.95 | -0.19 → 0.98 | 0.9 → 1.4 | 0.08 |
| ITC | 0.99 → 0.77 | 0.00 → 0.97 | 18.8 → 1.1 | 0.12 |
| TATAMOTORS | 1.01 → 1.04 | 0.03 → 0.95 | 12.6 → 3.4 | 0.08 |

Explained variance finishes at 0.95–0.99 on every stock. The critic perfectly explains training returns yet test performance is poor. Textbook generalization gap; the critic is overfitting hard.

## Open issues, ranked

### Tested

- DD penalty alone (v12). Net win, +21pp avg across 8 stocks vs v9.
- Validation split + early stopping (v16/v18). The two PPO-beats-B&H stocks (ITC, ADANIENT) came from this lever combined with the warmup gate.
- Differential Sharpe ratio reward (v10). VL spiked to 85, clip_fraction collapsed. The DSR `(B - A²)^(3/2)` denominator detonates in low-vol windows.
- Lighter regularization (v10/v11). EV did improve (0.99 → 0.80) but std grew, clip_fraction collapsed, returns regressed. Critic overfit isn't the dominant problem.
- Deepening-only DD penalty `max(0, dd_t - dd_{t-1})` (v13/v14). λ=20 and λ=5 both underperformed v12 on RELIANCE. The signal is too sparse; v12's persistent penalty was doing useful work. v25 (in `variants.md`, design-only) revisits this with a "deepening-from-max" formulation.
- More compute (v15, 1M timesteps). Direct overfit evidence: std halved, EV pegged at 0.99, test return dropped 11pp.
- min-val-trades filter (v17). No effect on HDFCBANK; the val@50k checkpoint had 29 val trades and the degeneracy was test-side.

### Designed (in `Rl_v19.py`–`Rl_v23.py`, syntax-clean, not yet run)

Single-variable forks of v18. Hypothesis, target stock, and diagnostic for each are in `variants.md`. Suggested run order:

1. v19, B&H-relative reward. `reward = (log(eq_t/eq_{t-1}) - log(close_t/close_{t-1})) * 100`, clipped, minus DD. Highest a-priori leverage on the v18 problem of making absolute money but losing to bull-trending B&H.
2. v22, ensemble seeds. 3-seed ensemble cuts variance roughly 1/√3. Cheap and stackable.
3. v20, best-by-Sharpe in `ValidationCallback`. Targets INFY-style high-variance overfit by filtering val winners on risk-adjusted return.
4. v21, target-exposure action. Action ∈ [0, 1] = target capital fraction. Decouples credit assignment from price level.
5. v23, warmup=150k, eval_freq=25k. Forces all eligible evals into the 150k–200k range. Speculative; only worth running if v17/v18's warmup ideas need refinement.

### Designed (DESIGN ONLY in `variants.md`, not implemented)

- v25, DD-from-max-seen penalty. Penalize only when the current drawdown reaches a new low-water mark. Smarter than v13/v14's deepening-from-prev-bar (which over-penalized normal volatility). Worth holding off until v19/v20 results clarify the reward landscape; combining DD-shape changes with reward-shape changes is the v10/v11 trap.

### Untested, partial implementation

- ~~Indicator audit~~. DONE: `test_indicator_causality.py` computes each kept indicator on the train prefix alone vs the full series and asserts prefix equality. Passing as of 2026-06-11 (98 indicators, RELIANCE). `test_indicator_audit.py` remains as the fast static check.
- Per-split indicator computation. Currently safe because all kept indicators are audited causal. The static test above is a defensive line; a true per-split recompute would be belt-and-suspenders.
- ~~Degeneracy diagnostic in `create_comprehensive_report`~~. DONE (v18–v24): warns in the report and on stdout when `total_trades < 0.01 * len(test_df)`. HDFCBANK v16 was caught only by reading `trades.csv` manually.

## Process notes

When a multi-change version regresses, isolate. v10 changed DSR + regularization simultaneously and lost. v11 changed DD + regularization and lost. v12 changed only DD and won. Two changes can both be net-positive individually but offset each other when combined. Have a single-variable test before stacking.

This is why v19–v23 are parallel forks of v18, not stacked. Run each independently, then layer winners.

## Input / Output

Input: `{SYMBOL}_daily.csv` with columns `datetime, open, high, low, close, volume`.

Output:

- `models/{SYMBOL}_ppo.zip` — trained model
- `models/{SYMBOL}_vecnorm.pkl` — saved `VecNormalize` running stats
- `models/{SYMBOL}_best.zip` — best-val checkpoint (v16+)
- `results/{SYMBOL}/{SYMBOL}_report.txt` — performance vs B&H
- `results/{SYMBOL}/account_value.csv`
- `results/{SYMBOL}/trades.csv`
- `consolidated_report.txt` — portfolio-level summary
- `runs/{SYMBOL}_{TIMESTAMP}/` — TensorBoard logs
