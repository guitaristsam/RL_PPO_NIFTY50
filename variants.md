# Variants v19–v23 — single-variable experiments off v18

All five files are forks of `Rl_v18.py`. Each makes ONE focused change. They
are **parallel** experiments, NOT sequential — `v23` is not `v22 + something`.
The cumulative-stacking approach gave us v10/v11 regressions; we are
deliberately keeping each variant isolated so causation is identifiable.

The active baseline `Rl_v18.py` is **untouched**. Do not edit any of v6–v18.

---

## Rl_v19.py — B&H-relative reward

**Hypothesis.** v18's reward (`log(eq_t / eq_{t-1}) * 100` clipped, minus DD
penalty) tells the agent to make money in absolute terms but says nothing
about beating buy-and-hold. On strong-trend stocks (RELIANCE B&H +147%,
TATAMOTORS B&H +338%) v18 can be making money while losing badly to B&H, and
PPO's loss has no idea. Subtracting the per-bar B&H log-return from the
agent's log-return gives an explicit alpha gradient.

**Code change.**
- `Rl_v19.py` lines ~487–495: snapshot `prev_bh_price` from `prev_prices[0]`
  before super().step().
- `Rl_v19.py` lines ~530–545: replace primary reward computation. The reward
  is now `clip((log(eq_t/eq_{t-1}) - log(close_t/close_{t-1})) * 100, -10, 10)`.
- v12 DD penalty preserved (still subtracted) — single-variable swap.

**How to run.**
```bash
python -c "from Rl_v19 import process_stock, NIFTY50_PATH; import os; \
  process_stock(os.path.join(NIFTY50_PATH, 'RELIANCE_daily.csv'))"
```

**Diagnostic to look for.**
- Training-curve `clip_fraction` should stay > v18's typical ~0.06. If it
  collapses to ~1e-3 (v10 DSR pattern), the relative reward is producing
  near-zero gradients.
- Trade count must exceed `min_val_trades` — if the agent learns "sit in cash
  during the benchmark drawdown", val will be filtered out as degenerate
  (good — system catches it).
- Compare on RELIANCE / INFY / TATAMOTORS — those are the canonical
  high-trend stocks where v18 underperformed B&H.

---

## Rl_v20.py — best-by-Sharpe in ValidationCallback

**Hypothesis.** v18 picks the best-val checkpoint by **total return**. That
metric rewards lucky-long val winners that don't generalise (canonical:
INFY @200k in v18). Sharpe = `mean(daily_returns) / std(daily_returns) *
sqrt(252)` is risk-adjusted: a smoother equity curve scores better than a
volatile one with the same end-of-window return.

**Code change.**
- `Rl_v20.py` `ValidationCallback.__init__` (~line 615): `best_return` →
  `best_sharpe`.
- `Rl_v20.py` `_on_step` (~line 632): `_eval_on_val()` now returns
  `(val_return, val_sharpe, val_trades)`; comparison uses Sharpe; print
  shows both.
- `Rl_v20.py` `_eval_on_val` (~line 700): records `portfolio_values` per
  step, computes Sharpe from `np.diff(pv) / pv[:-1]`. Returns 0 if std is 0.
- `Rl_v20.py` `train_ppo_model` (~line 815): post-train print shows
  `val_sharpe` not `val_return`.

**How to run.**
```bash
python -c "from Rl_v20 import process_stock, NIFTY50_PATH; import os; \
  process_stock(os.path.join(NIFTY50_PATH, 'INFY_daily.csv'))"
```

**Diagnostic to look for.**
- The callback's `eval_history` list (in-memory; print or pickle if needed)
  shows `(timestep, val_return, val_sharpe, val_trades)` quadruples. If
  Sharpe-best and return-best disagree on which timestep to save, the
  hypothesis is in play.
- INFY and TATAMOTORS are the highest-priority test cases — both had test
  regressions in v18 traceable to high-variance val winners.

---

## Rl_v21.py — target-exposure action

**Hypothesis.** v18's action is share-delta: `raw_action ∈ [-1,1] × hmax`
shares to buy/sell. That couples credit-assignment to the price level. The
agent must learn target-exposure AND the share count to get there
simultaneously. Target-exposure decouples the two: action ∈ [0, 1] is the
fraction of capital to hold; env handles the bookkeeping.

**Code change.**
- `Rl_v21.py` `_process_action` (~line 446): full rewrite. Maps
  `raw_action ∈ [-1,1]` to `target_frac ∈ [0,1]` via `(a+1)/2`. Computes
  `desired_shares = (target_frac × portfolio_value) // price`. Delta from
  current shares to desired, clipped to ±hmax per step. Same budget /
  position validation as v18.
- `step()` and reward unchanged — single-variable swap.

**How to run.**
```bash
python -c "from Rl_v21 import process_stock, NIFTY50_PATH; import os; \
  process_stock(os.path.join(NIFTY50_PATH, 'TCS_daily.csv'))"
```

**Diagnostic to look for.**
- Policy `std` trajectory should converge faster (the agent has a simpler
  problem to learn).
- Trade count may DROP — fewer "fix-up" trades to maintain the same target
  exposure as price moves.
- TCS and RELIANCE are the highest-priced stocks in the cohort, so price
  coupling was worst there. Look for them to improve relative to v18.

---

## Rl_v22.py — ensemble-friendly seeds + `ensemble_predict.py`

**Hypothesis.** Cross-stock variance is high in the v9-batch and v18-batch
results (TATAMOTORS swings ±20pp on seed). At 200k timesteps the optimization
landscape has many shallow minima; different seeds find different policies.
A 3-seed ensemble that averages continuous actions before the env step should
cut variance ~1/√3.

**Code change.**
- `Rl_v22.py` `train_ppo_model` signature: adds `seed_offset=0`. Effective
  seed = `42 + seed_offset`. Best-checkpoint path becomes
  `{stock}_seed{N}_best.zip`. Returns now include `effective_seed`.
- `Rl_v22.py` `process_stock` signature: adds `seed_offset=0`. MODEL and
  vecnorm save paths are ALWAYS suffixed `{stock}_seed{N}_ppo.zip` /
  `_seed{N}_vecnorm.pkl` (N = 42 + offset, so even offset 0 gives
  `_seed42_`); `ensemble_predict.py` depends on that suffix. Only the report
  filename and per-stock CSVs drop the suffix at offset 0 (so a single
  offset-0 run still writes `{stock}_report.txt` like v18). RNG seeding and
  the resume guard also key off the effective seed.
- `ensemble_predict.py` (~110 lines): loads N saved models for one stock,
  steps a shared eval env using the **average of the N continuous actions**
  per timestep. Each model sees obs from its own VecNormalize stats; the
  averaging happens BEFORE the env step. Final value, account-value series,
  and B&H comparison are returned and printed.

**How to run.**
```bash
# train three seeds for one stock (sequential — no parallel-process glue here)
python -c "from Rl_v22 import process_stock, NIFTY50_PATH; import os; \
  [process_stock(os.path.join(NIFTY50_PATH, 'RELIANCE_daily.csv'), seed_offset=k) for k in (0,1,2)]"

# then evaluate the ensemble
python -c "from ensemble_predict import ensemble_test; \
  ensemble_test('RELIANCE', seed_offsets=[0, 1, 2])"
```

**Diagnostic to look for.**
- Compare per-seed test return (printed at end of each `process_stock` run)
  to ensemble test return (printed by `ensemble_test`). If
  `var(per_seed) >> var(ensemble)` the variance-reduction story holds.
- TATAMOTORS / INFY are highest-priority — those are the volatile-return
  stocks v18 struggled on.

---

## Rl_v23.py — longer warmup + smaller eval_freq

**Hypothesis.** v18 had `warmup_steps=100k`, `eval_freq=50k` → eligible evals
at 100k, 150k, 200k. The 100k checkpoint was a v17-fix concern but is still
under-trained relative to 150k/175k/200k. v23 sets warmup_steps=150k,
eval_freq=25k → evals at 150k, 175k, 200k. Same eligible-eval count but
pushed entirely into the converged region.

**Code change.**
- `Rl_v23.py` `ValidationCallback.__init__` (~line 600): defaults
  `eval_freq=25000`, `warmup_steps=150000`.
- `Rl_v23.py` `train_ppo_model` (~line 790): explicit construction kwargs
  `eval_freq=25000`, `warmup_steps=150000`. Print updated.

**How to run.**
```bash
python -c "from Rl_v23 import process_stock, NIFTY50_PATH; import os; \
  process_stock(os.path.join(NIFTY50_PATH, 'HDFCBANK_daily.csv'))"
```

**Diagnostic to look for.**
- Inspect the `eval_history` list at end of training. If v23 picks @175k or
  @200k for stocks where v18 picked @100k, the cadence/warmup combination is
  doing useful work.
- HDFCBANK is highest-priority — it's the canonical "v17 saved a lucky-long
  early checkpoint" case that motivated the warmup.

---

## Rl_v24.py — pooled cross-stock training

**Hypothesis.** v18 trains one 128-hidden LSTM per stock on ~2,500 daily bars —
data-starved for a 101-dim observation, which is why 43/50 stocks lose to B&H.
Pooling all stocks into ONE policy gives ~50× the data, exposure to many
regimes, and one model instead of 50.

**Code change.** (single-variable vs v18: pooling only)
- `build_pooled_data()`: runs v18's per-stock pipeline for every stock, takes
  the INTERSECTION of indicator names so all envs share one observation shape,
  precomputes per-stock hmax.
- `PooledTradingEnv`: each `reset()` samples a random symbol + random
  contiguous 252-date window from its train slice and delegates to a fresh
  `IntegerTradingEnv` (the v18 env, reward and all). Dedicated `default_rng`.
- `PooledValidationCallback`: each eval runs the deterministic policy over the
  FULL val window of each of the 10 PANEL stocks; score = mean val return
  across panel stocks with `trades >= min_val_trades`; requires >= 6/10
  eligible, else the eval is degenerate-skipped.
- `train_pooled` / `test_pooled`: ONE global VecNormalize, ONE RecurrentPPO at
  `TOTAL_TIMESTEPS=2_000_000`; at test, the single model runs over every
  stock's test slice. Vecnorm-snapshot logic retained.

**How to run.**
```bash
python Rl_v24.py                       # full pooled run -> results_v24/

# smoke test
V24_STOCKS="RELIANCE,INFY,ITC" TOTAL_TIMESTEPS=20000 V24_WARMUP=0 \
  V24_EVAL_FREQ=10000 V24_LOG_RESETS=1 python Rl_v24.py
```

**Diagnostic to look for.**
- Per-panel val returns printed at each eval; if the pooled policy's mean panel
  val return beats the per-stock v18 val returns, pooling is adding signal.
- HDFCBANK is the key test: per-stock v18 found no winning policy; cross-stock
  features are the hypothesised fix.

**Status.** 3-stock / 20k-step smoke run passed end-to-end on 2026-06-11
(pooling → panel evals → best-checkpoint + vecnorm snapshot → restore →
per-stock test → consolidated report). Full 2M-step run not yet done.

---

## DESIGN ONLY — proposed v25 (do NOT implement without confirming results from v19–v23)

**v25: smoother DD penalty (DD-deepening only).**

v18/v12's penalty fires every step the equity is below peak by more than 10%.
That double-penalises sustained drawdowns: once you're down 15%, every
subsequent flat-but-still-down bar adds another `1.0 * 0.05 = 0.05` of
negative reward. Bias: agent prefers to exit positions during routine
pullbacks rather than ride them out — exactly the failure mode we see on
TATAMOTORS (failed to hold through the +338% bull's pullbacks) and INFY
(over-trading into losses).

**Proposed change.** Replace
```python
dd_penalty = self._dd_lambda * max(0.0, drawdown - self._dd_threshold)
```
with
```python
# Penalize only NEW drawdown depth — i.e. when the current DD just went
# deeper than it has been before in this episode.
dd_delta = max(0.0, drawdown - self._dd_max_seen)
self._dd_max_seen = max(self._dd_max_seen, drawdown)
dd_penalty = self._dd_lambda * dd_delta
```
plus `self._dd_max_seen = 0.0` initialised in `__init__` and reset in
`reset()`. Now the penalty fires once per new low-water mark, not every step
the equity is underwater. Hypothesis: should fix INFY's regression
(over-trading into losses) and TATAMOTORS (selling out of normal pullbacks
during a bull).

**Why DESIGN ONLY.** This change interacts with whatever v19/v20 conclude
about reward shaping. If v19's B&H-relative reward wins, the DD penalty's
role changes (it's now subtracting from a smaller, alpha-style primary). If
v20 wins, the val signal is already filtering high-DD policies and we may
need less DD penalty, not different DD penalty. Run v19–v23, learn, THEN
decide whether to layer v25 on top.
