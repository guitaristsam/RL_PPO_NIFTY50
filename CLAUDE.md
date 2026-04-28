# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project state

Single-file PPO-based stock trading system for NIFTY50 Indian equities. The codebase has evolved through several versions; **`Rl_v9.py` is the current active version**. Earlier versions are kept on disk as immutable history of the bug-hunt and should not be edited.

| File | Status | Notes |
|---|---|---|
| `Rl_v6.py` / `Rl_v6.ipynb` | frozen | original, multiple bugs documented below |
| `Rl_v7.py` | frozen | v6 + memory caps + price-aware hmax + VecNormalize |
| `Rl_v8.py` | frozen | v7 + indicator-leakage pruning + state-layout fix + action-scaling fix + B&H benchmark fix |
| `Rl_v9.py` | frozen | v8 + RecurrentPPO (LSTM) + log-return reward |
| `Rl_v10.py` | frozen | v9 + DSR reward + regularization. **Failed** — VL=85, clip_frac=1e-4. |
| `Rl_v11.py` | frozen | v9 + log-return reward + DD penalty + regularization. **Failed** — std grew, clip_frac=7e-4. |
| `Rl_v12.py` | frozen | v9 + DD penalty only. 6/8 stock-level wins vs v9. |
| `Rl_v13.py` | frozen | v12 + deepening-only DD (λ=20). **Failed** — RELIANCE +16% vs v12 +85%. |
| `Rl_v14.py` | frozen | v13 with λ=5. Better than v13 but still −40pp behind v12. |
| `Rl_v15.py` | frozen | v12 + 1M timesteps (5×). **Failed** — RELIANCE +74% vs v12 +85%; direct overfit evidence (std halved, EV pegged 0.99, test return dropped). |
| `Rl_v16.py` | frozen | v12 + 70/15/15 split + custom `ValidationCallback` (eval_freq=50k). **First stock to beat B&H (ITC +40pp, Sharpe 1.36).** Failure modes: HDFCBANK degenerate "do nothing" saved at val@50k; INFY late-training overfit at val@200k. |
| `Rl_v17.py` | frozen | v16 + min_val_trades=5 filter on val checkpoints. **No effect** — HDFCBANK's val@50k had 29 val trades (eligible), the degeneracy was test-side. |
| `Rl_v18.py` | **current** | v17 + warmup_steps=100k (skip first val eval). Targets the "lucky early checkpoint" failure mode from v16/v17. **Second stock to beat B&H (ADANIENT +66.8pp, Sharpe 0.64).** |
| `Rl_v19.py` | unrun queue | v18 + B&H-relative reward. Subtracts `log(close_t/close_{t-1})` from agent's log-return inside `IntegerTradingEnv.step()`. Hypothesis: explicit alpha gradient. Highest *a priori* leverage on B&H gap. |
| `Rl_v20.py` | unrun queue | v18 + best-by-Sharpe in `ValidationCallback`. Computes Sharpe from per-step portfolio-value series; saves best Sharpe checkpoint instead of best-return. Targets INFY-style high-variance overfit. |
| `Rl_v21.py` | unrun queue | v18 + target-exposure action. Action `(a+1)/2 ∈ [0,1]` is target capital fraction; env computes share-delta. Decouples credit assignment from price level. |
| `Rl_v22.py` | unrun queue | v18 + `seed_offset` parameter for ensemble training. Each seed saves to `{stock}_seed{N}_*.zip/csv/txt`. Companion `ensemble_predict.py` averages N continuous actions per step. |
| `Rl_v23.py` | unrun queue | v18 + warmup=150k, eval_freq=25k. Eligible evals at 150k/175k/200k. Pushes all checkpoints into the converged-policy region. |
| `ensemble_predict.py` | helper | Loads N v22-style saved models for one stock, averages continuous actions on a shared eval env. ~110 lines. Depends on SB3's `VecNormalize.normalize_obs`/`unnormalize_obs`. |
| `variants.md` | docs | One section per v19–v23 with hypothesis + code change summary + run command + diagnostic to look for. Also a `DESIGN ONLY` v24 proposal (DD-deepening-from-max, smarter than v13/v14's deepening-from-prev-bar). |
| `summarize_results.py` | helper | After a run finishes, parses every `results/{SYMBOL}/{SYMBOL}_report.txt` and prints a sorted outperformance table + summary stats (count beating B&H, avg Sharpe, avg DD, degenerate count). Run with `python summarize_results.py`. |
| `test_indicator_audit.py` | test | Unittest that fails if any of `Rl_v8.py` … `Rl_v23.py`'s `list_of_indicators` includes a known-leakage name (DPO_20, AMATe_*, AOBV_*, PSARr, TTM_TRND_6, STC_*, etc.). Run with `python test_indicator_audit.py`. v6/v7 are exempt (frozen history). |
| `v9_batch.py` / `v12_batch.py` / `v16_batch.py` / `v18_batch.py` | helper | run `process_stock` on a curated subset of NIFTY50 names |

## Running

```bash
# full 50-stock alphabetical sweep (v18 is current)
python Rl_v18.py

# small batch (faster — 5 stocks targeted at v16's failure modes)
python v18_batch.py

# one-stock ad-hoc — bypass the main loop, useful for iterating
python -c "from Rl_v18 import process_stock, NIFTY50_PATH; import os; \
  process_stock(os.path.join(NIFTY50_PATH, 'RELIANCE_daily.csv'))"
```

No `requirements.txt`. Required:
```
numpy pandas pandas-ta torch scikit-learn stable-baselines3 sb3-contrib gymnasium finrl matplotlib tqdm tensorboard
```
`sb3-contrib` is new in v9 and supplies `RecurrentPPO`.

Each `process_stock` call has a **resume guard**: if `results/{SYMBOL}/{SYMBOL}_report.txt` already exists, the stock is skipped. To force a re-run, delete that file (or the whole `results/{SYMBOL}/` directory).

## Pipeline (per stock, in `process_stock()`)

1. Load `{SYMBOL}_daily.csv` from `NIFTY50_PATH`.
2. Compute ~300 indicators via `df.ta.study(ta.AllStudy, cores=0)`, filter down to `list_of_indicators` (~98 names in v9 — pruned from v6's ~118 to remove lookahead leakage).
3. `handle_nan_per_stock()` — trims to the first row where all indicators are non-null; **ffill only** on prices and indicators (no bfill — that was a leak vector across the train/test boundary).
4. `prepare_data_for_finrl(..., skip_scaling=True)` — format conversion only.
5. 80/20 chronological train/test split by date.
6. `prepare_data_for_finrl(train, scalers=None)` then `(test, scalers=fitted)` — `RobustScaler` fit on train only.
7. `train_ppo_model()` — wraps env in `DummyVecEnv`→`VecNormalize(norm_obs=True)` to scale the *full* state (cash, positions, prices, indicators) — RobustScaler alone only handles indicators. v9 uses `RecurrentPPO("MlpLstmPolicy", ...)` for 200 000 timesteps.
8. `test_ppo_model()` — runs deterministic inference, threads `lstm_states` and `episode_starts` through `predict()` for the recurrent policy. Loads saved `VecNormalize` stats with `training=False`.
9. `create_comprehensive_report()` — writes per-stock `.txt` report (UTF-8), `account_value.csv`, `trades.csv` under `results/{SYMBOL}/`.
10. `generate_consolidated_report()` — aggregates into `consolidated_report.txt`.

## Critical bug history — DO NOT regress these

These are the bugs we already paid to find. Re-introducing any one of them will silently invalidate every result.

### 1. `IntegerTradingEnv` state layout (v6→v8 fix)

FinRL's `StockTradingEnv` state layout is:
```
state[0]                            = cash
state[1 : 1 + stock_dim]            = prices
state[1 + stock_dim : 1 + 2*stock_dim] = shares
state[1 + 2*stock_dim : ...]        = tech-indicator block
```
v6 and v7 used `state[1:1+stock_dim]` thinking it was *positions* (it's prices) and computed a `price_index` via a tech-indicator stride that happened to land on the *shares* slot. Net effect: every "near-zero price" warning was firing because we were reading the shares value (=0 at reset), our budget clamp was a no-op, and trade logs reported next-day close prices as if they were share counts. v8's `IntegerTradingEnv` caches `_price_slice` and `_shares_slice` from FinRL's true layout — keep using those. `test_ppo_model` reads positions from `state[1+stock_dim : 1+2*stock_dim]` for the same reason.

### 2. Action scaling (v6/v7 → v8 fix)

FinRL's parent `step()` does `actions = actions * self.hmax; actions = actions.astype(int)` (line 303 of `env_stocktrading.py`). v6/v7's override rounded the raw `[-1, 1]` action to int **before** that scaling, collapsing every action into `{-2, -1, 0, 1, 2}` pre-scaling, which then became `{-2*hmax, …, 2*hmax}` post-scaling. The smoking gun was v6's policy std stuck at 0.97 forever — there was no gradient benefit to producing a fine-grained action.

The v8 fix is in `IntegerTradingEnv._process_action`:
1. Scale to integer shares first: `action_shares = round(raw_action * hmax).astype(int)`.
2. Validate budget and position constraints in shares-space.
3. In `step()`, divide by `hmax` so `super().step()`'s internal `*hmax` recovers our exact integer share count.

### 3. Lookahead-leakage indicators (v7 → v8 fix)

v6/v7 included indicators with `lookahead=True` defaults or center-aligned smoothing. With these, ADANIPORTS showed a 1946% return and Sharpe 6.58 over a 3.5-year test — pure leakage. **Indicators removed in v8 (do not put them back without auditing pandas-ta source):**
`DPO_20`, `AMATe_LR_8_21_2`, `AMATe_SR_8_21_2`, `AOBV_LR_2`, `AOBV_SR_2`, `PSARr_0.02_0.2`, `TTM_TRND_6`, `DEC_1`, `INC_1`, `STC_10_12_26_0.5`, `STCmacd_10_12_26_0.5`, `STCstoch_10_12_26_0.5`, `FISHERTs_9_1`, `EBSW_40_10`, `COPC_11_14_10`.

### 4. NaN handling (v7 → v8 fix)

`bfill` across the train/test split propagates future values backward. v8 uses **`ffill` only** in three places (handle_nan_per_stock prices, prepare_data tech indicators, prepare_data OHLCV); residual NaN gets filled with 0 (RobustScaler median) for indicators or per-split median for prices.

### 5. Buy-and-hold benchmark (v7 → v8 fix)

v6/v7 computed B&H with **fractional shares and no transaction costs**, giving B&H a structural edge over PPO (which is integer-only with 0.25%/side fees). v8's `calculate_buy_and_hold` uses integer shares, applies buy/sell costs, keeps residual cash. Apples-to-apples now.

### 6. Reward function (v8 → v9 → v12 evolution)

- v8 used FinRL's default raw rupee ΔP&L scaled by `reward_scaling` — fragile across price regimes.
- v9 changed to **log return × 100, clipped to [−10, 10]** in `IntegerTradingEnv.step()`. Scale-invariant. Single biggest improvement of the project: RELIANCE went from −40% → +68% (108pp swing).
- v12 keeps v9's primary reward and **subtracts a mild drawdown penalty**: `reward = primary − 1.0 × max(0, drawdown − 0.10)`. Discourages deep underwater positions. Net win across 7 stocks (avg +21pp swing).
- v10 (Moody-Saffell DSR) and v11 (DD + regularization) **regressed** vs v9. The DSR formula spikes the reward in low-vol windows (denominator `(B−A²)^(3/2)` collapses) — value_loss exploded to 85, clip_fraction collapsed to 1e-4. The regularization (smaller LSTM, higher entropy, fewer epochs) helped EV (0.99 → 0.80) but **hurt policy decisiveness**: std grew, clip_fraction near zero. **Lesson: change one thing at a time.** When two changes go in together and the result regresses, you have to roll back to a single-variable test to isolate the cause. v12 was that single-variable test (only DD penalty added) and confirmed regularization was the offender.

### 7. Date alignment in `test_ppo_model` (v7 → v8 fix)

FinRL's `step()` advances `self.day` and updates state to the *new* day's price after the trade settles. v6/v7 paired the post-step `total_asset` with `unique_dates[step_count]` (= old day) — off by one. v8 records the initial value at `unique_dates[0]` before the loop and pairs each post-step value with `unique_dates[step_count]` after incrementing.

### Other fixes you'll see in v8/v9
- Global RNG seeding (`random`, `np.random`, `torch.manual_seed`) at start of every `process_stock` — v6/v7 only seeded PPO.
- Memory caps at top of file: `OMP/MKL/OPENBLAS/NUMEXPR_NUM_THREADS=1`, `torch.set_num_threads(1)`, `df.ta.cores = 0`. The Windows page file blew up when pandas-ta multiprocessed and each worker re-imported numpy + TF.
- `print_verbosity=1000` on the env (v6 was 5 → 75 spam lines per stock).
- Report files opened with `encoding='utf-8'` — emojis like 📊 crashed default cp1252.
- `_near_zero_warned` flag — print the price-clamp warning at most once per env.

## Key classes (v9)

- **`IntegerTradingEnv`** (extends FinRL's `StockTradingEnv`) — enforces integer share quantities, budget constraints, non-negative positions. Cached `_price_slice` and `_shares_slice` for the FinRL state layout. Overrides `step()` to compute log-return reward.
- **`TradeLogger`** — detects buy/sell from position deltas, tracks weighted-avg buy price per symbol, computes win rate on sell trades only.

## Constants

| Constant | Value | Notes |
|---|---|---|
| `NIFTY50_PATH` | `C:\Users\sambh\OneDrive\Desktop\Nifty50OHLCV\` | Windows native path |
| `MIN_DATA_ROWS` | 252 | Stocks skipped below this after cleaning |
| `hmax` | price-aware: `floor(initial_amount / median_train_price)`, clamped `[2, 200]` | v6 used fixed `hmax=10` which collapsed action resolution on high-priced stocks |
| `buy/sell_cost_pct` | 0.0025 | 0.25% per side |
| `initial_amount` | ₹10 000 per stock |  |
| `total_timesteps` | 200 000 | likely too few for RecurrentPPO; 1M+ recommended next |

## v9 hyperparameters (RecurrentPPO)

`learning_rate=3e-4`, `n_steps=512`, `batch_size=64` (must divide `n_steps * n_envs`), `n_epochs=5`, `gamma=0.99`, `gae_lambda=0.95`, `clip_range=0.2`, `ent_coef=0.01`, `vf_coef=0.5`, `max_grad_norm=0.5`, `seed=42`. `policy_kwargs={"lstm_hidden_size": 128, "n_lstm_layers": 1, "shared_lstm": False, "enable_critic_lstm": True, "net_arch": [128], "activation_fn": Tanh}`.

## Empirical baselines (200k timesteps)

### v18 small batch (5 stocks; ITC is the control)

| Stock | v18 PPO | v18 B&H | v18 Outperf | v16 Outperf | Δ vs v16 | v18 Sharpe | v18 DD | Trades |
|---|---|---|---|---|---|---|---|---|
| **ADANIENT** | **+45.21%** | −21.61% | **+66.83pp** | −2.91pp | **+69.7pp** | **+0.64** | −17.0% | 94 |
| **ITC** (ctrl) | **+145.97%** | +105.88% | **+40.09pp** | +40.09pp | 0 | **+1.36** | −15.1% | 161 |
| TCS | −3.72% | +4.81% | −8.53pp | −11.02pp | +2.5pp | −0.14 | −11.2% | 90 |
| ADANIPORTS | −2.05% | +62.06% | −64.11pp | −73.23pp | +9.1pp | −0.04 | −42.4% | 72 |
| HDFCBANK | −24.58% | +30.62% | −55.20pp | −30.62pp | −24.6pp | −0.86 | −31.2% | 90 |

**Two stocks beat B&H now: ITC (Sharpe 1.36) and ADANIENT (Sharpe 0.64).** v18 average outperformance across these 5 stocks: −4.2pp vs v16's −15.5pp — a +11.4pp lift. ITC control reproduced exactly (same checkpoint timing 150k > warmup 100k), confirming v18 is bit-exact on stocks unaffected by warmup gating. HDFCBANK regressed because v16 was a fake "lucky cash" win; v18 reveals the underlying policy is genuinely bad.

### v16 (prior baseline) — 8 stocks tested

Note: v16 uses a 70/15/15 train/val/test chronological split; v12 used 80/20 train/test. The val slice carves out the middle 15% so the test period in v16 is shorter and starts later than in v12 — direct return comparisons aren't apples-to-apples. Compare via **outperformance** (PPO − B&H) instead, which is robust to test-window shifts.

| Stock | v16 PPO | v16 B&H | Outperf | v12 Outperf | Δ outperf | v16 Sharpe | v16 DD | Trades | Notes |
|---|---|---|---|---|---|---|---|---|---|
| RELIANCE | +31.58% | +68.47% | −36.89pp | −62.88pp | **+26pp** | +0.54 | −21.9% | 113 | clean win |
| **ITC** | **+145.97%** | +105.88% | **+40.09pp** | −73.60pp | **+114pp** | **+1.36** | −15.1% | 161 | ✅ **PPO BEATS B&H** |
| **TATAMOTORS** | **+229.57%** | +253.67% | −24.10pp | −356.43pp | **+332pp** | **+0.94** | −38.9% | 78 | huge improvement |
| TCS | −6.21% | +4.81% | −11.02pp | −7.56pp | −3pp | −0.23 | −14.0% | 67 | flat |
| ADANIENT | −24.52% | −21.61% | −2.91pp | −0.55pp | −2pp | −0.39 | −46.1% | 55 | flat (v12 was degenerate B&H mimic) |
| ADANIPORTS | −11.17% | +62.06% | −73.23pp | −80.81pp | +8pp | −0.35 | −17.1% | 55 | small win |
| HDFCBANK | 0.00% | +30.62% | −30.62pp | −42.59pp | +12pp | 0.00 | **−1.5%** ⚠ | 11 | **DEGENERATE** — val saved a "do nothing" policy at 50k |
| INFY | −39.84% | +22.06% | −61.90pp | −119.97pp | +58pp | −0.66 | −48.8% | 206 | val@200k overfit; worse than v12 absolute return but better outperformance |

**6/8 stocks improve in outperformance vs v12. ITC is the first PPO-beats-B&H stock in the project. Average max drawdown halved (v16 −25% vs v12 −46%). Average Sharpe ~3× higher (v16 +0.15 vs v12 +0.05).**

### v16 / v18 mechanism

The val callback fires every 50k steps, runs a deterministic policy through the validation slice, records final portfolio return, and saves the model when val return improves. After training, the best-val checkpoint is restored.

v18 adds `warmup_steps=100000`: evals before that step are explicitly skipped. This was added after v17 (a min-val-trades=5 filter) failed to fix HDFCBANK — v17 revealed the val@50k checkpoint actually had 29 val trades (eligible) but was an under-trained "lucky long" capturing a transient val rally rather than skill. The warmup gate forces the first eligible checkpoint to be at val@100k or later.

Validation curves observed across batches:
- RELIANCE peak at val@100k (+105%), training kept getting worse after — overfit confirmed.
- TATAMOTORS val crossed −60% → +0.5% between iter 50k and 150k.
- ITC val was *negative* throughout (−7%, then −6.86%); the saved policy then made +146% on test. Hard val period selected for discipline.
- ADANIENT val@50k was +191% (lucky-long during 2020 bull); v18 skipped that, saved val@100k at +96%, which beat B&H by 67pp on test (B&H lost 22% post-Hindenburg).

### v16 / v18 known failure modes

- **HDFCBANK is feature-untrainable.** v16 saved a "do nothing" policy at val@50k that produced 11 test trades and 0% return — looked OK because the test period drifted up modestly while the policy held cash. v17 (min-val-trades) didn't change anything because val@50k had 29 val trades. v18 (warmup=100k) forced val@100k to be saved instead, producing a real but actively-losing policy (−24.58% test, 90 trades). Net interpretation: there is no winning policy on HDFCBANK with the current feature set + reward; v16 was a false win. Real fix would be feature-side (cross-asset signals, fundamentals) or reward-side (B&H-relative reward).
- **Late-training overfit (INFY in v16 batch)**: val@200k looked best but didn't generalize. Untouched by v17/v18 — would need a held-out "early test" slice or more diverse val signal (e.g. val Sharpe instead of val return).

## Training-curve diagnostics (batch run of 7 stocks at 391 iterations each)

| Stock | std₀ → std_T | EV₀ → EV_T | VL₀ → VL_T | clip_avg |
|---|---|---|---|---|
| ADANIENT | 1.00 → 0.88 | 0.00 → **0.99** | 49.7 → 1.3 | 0.10 |
| ADANIPORTS | 1.00 → 0.76 | −0.01 → **0.95** | 29.7 → 1.4 | 0.11 |
| TCS | 1.01 → 0.76 | 0.01 → **0.96** | 8.3 → 0.3 | 0.13 |
| HDFCBANK | 1.00 → 0.89 | −0.03 → **0.99** | 2.3 → 0.5 | 0.10 |
| INFY | 1.00 → 0.95 | −0.19 → **0.98** | 0.9 → 1.4 | 0.08 |
| ITC | 0.99 → 0.77 | 0.00 → **0.97** | 18.8 → 1.1 | 0.12 |
| TATAMOTORS | 1.01 → **1.04** | 0.03 → 0.95 | 12.6 → **3.4** | 0.08 |

**Critical observation:** `explained_variance` finishes at **0.95–0.99 on every stock** — the critic *perfectly* explains training returns, yet test performance is poor. That's a textbook generalization gap, i.e. **the critic is overfitting hard**.

## Open issues / next levers

Ordered by expected impact. Several v9-era levers were tested in v10/v11/v12; results below.

### Tested

- **DD penalty alone (v12)** ✅ — Net win, +21pp avg across 8 stocks vs v9.
- **Validation split + early stopping (v16/v18)** ✅ — First two PPO-beats-B&H stocks (ITC, ADANIENT) came from this lever combined with the warmup gate.
- **Differential Sharpe ratio reward (v10)** ❌ — VL spiked to 85, clip_fraction collapsed. DSR has a `(B−A²)^(3/2)` denominator that detonates in low-vol windows.
- **Lighter regularization (v10/v11)** ❌ — EV did improve (0.99 → 0.80) but std grew, clip_fraction collapsed, returns regressed. Critic overfit isn't the dominant problem.
- **Deepening-only DD penalty `max(0, dd_t − dd_{t-1})` (v13/v14)** ❌ — Both λ=20 and λ=5 underperformed v12 on RELIANCE. The signal is too sparse; the persistent v12 penalty was doing useful work. (Note: v24 design proposal in `variants.md` revisits this with a smarter "deepening-from-max" formulation.)
- **More compute (v15, 1M timesteps)** ❌ — Direct overfit evidence: std halved, EV pegged at 0.99, test return dropped 11pp.
- **min-val-trades filter (v17)** ❌ — No effect on HDFCBANK; the val@50k checkpoint had 29 val trades (eligible) but became degenerate only on test.

### Designed (in `Rl_v19.py`–`Rl_v23.py`, syntax-clean, **not yet run**)

Single-variable forks of v18. Each has a hypothesis, target stock, and diagnostic in `variants.md`. Recommended run order:

1. **v19 — B&H-relative reward.** Reward = `(log(eq_t/eq_{t-1}) − log(close_t/close_{t-1})) × 100`, clipped, minus DD. Highest *a priori* leverage on the v18 problem of agent making money in absolute terms while losing to bull-trending B&H.
2. **v22 — ensemble seeds.** 3-seed ensemble cuts variance ~1/√3. Cheap, can be applied on top of any other variant.
3. **v20 — best-by-Sharpe in ValidationCallback.** Targets INFY-style high-variance overfit by filtering val winners on risk-adjusted return.
4. **v21 — target-exposure action.** Action ∈ [0, 1] = target capital fraction. Decouples credit assignment from price level.
5. **v23 — warmup=150k, eval_freq=25k.** Forces all eligible evals into 150k–200k range. Speculative; only run if v17/v18 warmup ideas need refinement.

### Designed (DESIGN ONLY in `variants.md`, not implemented)

- **v24 — DD-from-max-seen penalty.** Penalize only when the current DD reaches a NEW low-water mark. Smarter than v13/v14's deepening-from-prev-bar (which over-penalized normal volatility). Should *not* be implemented until v19/v20 results clarify how the reward landscape is shaped — combining DD-shape changes with reward-shape changes is the v10/v11 trap.

### Untested, partial implementation

- **Indicator audit** — `test_indicator_audit.py` is a static check against a hardcoded known-leakage list. Stronger version (compute each indicator on `train_raw` alone vs full series, assert equality on the train slice) is still TODO.
- **Per-split indicator computation** — currently safe because all kept indicators are audited causal. The static test above is a defensive line; a true per-split recompute would be belt-and-suspenders.
- **Degeneracy diagnostic in `create_comprehensive_report`** — TODO. Should warn if `total_trades < 0.01 * len(test_df)`. Caught HDFCBANK v16 only by reading trades.csv manually.

### Lesson learned (process)

When a multi-change version regresses, **isolate**. v10 changed DSR + regularization simultaneously and lost; v11 changed DD + regularization and lost; v12 changed only DD and won. Two changes can both be net-positive individually but offset each other when combined. Always have a single-variable test before stacking interventions.

This lesson is the reason `Rl_v19.py`–`Rl_v23.py` are **parallel** forks of v18, not stacked. Run each independently, then layer winners.

## Input / Output

- **Input**: `{SYMBOL}_daily.csv` with columns `datetime, open, high, low, close, volume`.
- **Output**:
  - `models/{SYMBOL}_ppo.zip` — trained model
  - `models/{SYMBOL}_vecnorm.pkl` — saved `VecNormalize` running stats (v7+)
  - `results/{SYMBOL}/{SYMBOL}_report.txt` — performance vs buy-and-hold
  - `results/{SYMBOL}/account_value.csv`
  - `results/{SYMBOL}/trades.csv`
  - `consolidated_report.txt` — portfolio-level summary
  - `runs/{SYMBOL}_{TIMESTAMP}/` — TensorBoard training logs
