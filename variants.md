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

## Rl_v26.py — feature reduction (98 → 22 indicators)

**Hypothesis.** Explained variance pegs at 0.95–0.99 on every stock while test
returns lag — textbook critic overfit — and a 101-dim observation against
~2,500 train bars per stock is data-starved. Cutting to 22 curated indicators
(25-dim observation) attacks the overfit at the source. Cheapest untested
anti-overfit lever; complements v24 (which attacks the same problem from the
data side).

**Code change.** (single-variable vs v18: the indicator list only)
- `list_of_indicators` cut from 98 to 22 names, all a subset of v18's
  audited-causal list: trend (ADX/DM, MACD, AroonOsc, SuperTrend direction),
  momentum (RSI, ROC, MOM, CMO, Stoch %K, Williams %R, TSI), volatility
  (ATR, NATR, BB%, STDEV), volume (MFI, CMF, EFI), LOGRET_1.
- Everything else byte-identical to v18 (env, reward, callback, splits).

**How to run.**
```bash
python run_panel.py v26
```

**Diagnostic to look for.**
- Validation-curve shape: if val returns stop decaying after their 100k peak
  (v18's overfit signature), the reduction is working.
- Training EV: should end BELOW v18's 0.95–0.99. If still pegged, the critic
  is overfitting time-of-episode structure, not feature noise.
- INFY / HDFCBANK are priority reads — the two clearest overfit casualties.

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

---

# Variants v27–v34 — single-variable forks off the v26 CHAMPION (2026-09-02, auto/research)

**Champion shift.** The auto-tinker fast-proxy screen (3 stocks
RELIANCE/TATAMOTORS/HDFCBANK, 60k steps, seed 42, objective =
`mean_val_outperf_pp`) moved the champion from *v18 defaults (106 indicators,
-75.6pp)* to **v26 = 22 curated indicators, every other param at v18 defaults
(-7.9pp)**. Cutting ~80% of the features bought **+67.7pp** — the single
biggest lever the screen has found. Under-the-noise-gate but consistently
*positive* single-variable screens from that champion were **all
capacity-reduction**: `n_steps 512→256` (+17.4pp), `gamma 0.99→0.95`
(+13.4pp), `lstm_hidden 128→64` (+9pp), `ent_coef 0.01→0.05` (+3.1pp). The
frontier direction is unambiguous: **less capacity / less overfit generalizes
better on this data.** Everything below is a single-variable fork *from v26*
(copy `Rl_v26.py`, change one thing), not from v18.

**Why 22 indicators beat 106 (answers FRONTIER NEXT-ACTION #3).** This is
textbook *observational overfitting* (Song et al., "Observational Overfitting
in Reinforcement Learning", ICLR 2020, https://arxiv.org/abs/1912.02975): when
the observation carries many features that are irrelevant or redundant to the
optimal action, an over-parameterized policy/critic *implicitly memorizes*
those features to fit the training trajectory, and the memorized mapping does
not transfer. Their headline result — generalization degrades as you add
uninformative observation dimensions even when the reward-relevant signal is
unchanged — is exactly what v26 exploited: 101→25 obs dims, EV should now stop
pegging at 0.99, the critic having less nuisance structure to overfit. It also
explains the screen's val/test divergence (6 indicators → near-perfect **test**
+0.4pp but poor **val** -47pp; `n_steps=1024` → -75 val but **all 3 stocks beat
B&H on test**, +26pp): the tiny single val window is itself a noisy, regime-
specific selector — which is what v29/v33 below attack directly.

**Ranked by expected value** (advisor-reviewed 2026-09-02): **v29 > v33 > v28
> v34 > v27 > v31 > v30 > v32.** Fix the val selector first (v29/v33) — a
broken oracle caps the value of every regularizer underneath it.

---

## Rl_v27.py — input feature-masking during training (data-space regularization)

**Hypothesis.** v26 proved fewer features generalize better. Feature *masking*
is the stochastic, per-rollout version of the same lever: randomly zero a
fraction `p` of the observation's indicator block on each **training** step
(never at val/test). The policy cannot lean on any single indicator, so it is
forced onto a lower-effective-dimension representation — "stochastic feature
reduction" — attacking observational overfitting in data-space, not parameter-
space. This is mechanistically **distinct from the rejected weight
regularization** (which acts on parameters and collapsed clip_fraction): it is
input-space augmentation, the RL analogue of input dropout / cutout
(Laskin et al., RAD, https://arxiv.org/abs/2004.14990). Masking is preferred
over additive Gaussian noise because it is closer to the v26 win and because
naive additive obs-noise degrades PPO gradients (Igl et al., "Selective Noise
Injection", https://arxiv.org/abs/1910.12911) — masking a subset each step
leaves most of the gradient path clean.

**Code change.** (single variable vs v26: mask probability `p`, `0 → 0.10`)
- Add a thin `VecEnvWrapper` `FeatureMaskWrapper(p=0.10)` applied **after**
  `VecNormalize` in `train_ppo_model` only. In `reset()`/`step_wait()` it draws
  a Bernoulli(1-p) mask over the indicator slots of the observation
  (`state[1 + 2*stock_dim :]`, leave cash/price/shares untouched) and zeroes
  the masked entries. Not applied in `ValidationCallback`'s eval env or
  `test_ppo_model` (mask off ⇒ deterministic, full-observation inference).
- **Semantics (advisor — do not mislabel).** Because the mask is applied *after*
  `VecNormalize`, a masked entry is set to 0 in normalized space, i.e. to the
  feature's **running mean** — this is training-mean *imputation*, not a true
  "drop" of the feature. That is a defensible (arguably better-behaved)
  regularizer, but describe it as mean-imputation, not absence. Note also there
  is no `1/(1-p)` survivor rescale, so the expected activation magnitude of the
  indicator block shifts slightly at `p=0.10`; either add the rescale (classic
  inverted-dropout) or accept the small shift and note it. Single variable
  either way = the mask probability `p`.
- Everything else byte-identical to v26.

**How to run.** `python run_panel.py v27`

**Diagnostic to look for.**
- **Guardrail (advisor):** watch `clip_fraction` and policy `std` in the
  training log. If clip_fraction collapses toward ~1e-3 or std grows, masking
  is degrading gradients like the rejected reg did — back off `p` to 0.05.
- Training EV should finish **below** v26's; val curve should decay less past
  100k.
- **Target stock:** INFY (late-training overfit), HDFCBANK (feature-untrainable
  under the current set).

---

## Rl_v28.py — random episode-start offset (temporal data augmentation)

**Hypothesis.** v26's own diagnostic flags the open question: is the residual
overfit *feature-side* or *time-of-episode structure*? A single-stock env that
always starts the training episode at day 0 lets the LSTM memorize one fixed
trajectory (the same calendar path every rollout). Starting each **training**
episode at a random day breaks that: the agent sees many market contexts and
cannot memorize a single time-indexed path. This is standard RL data
augmentation / a 1-D domain randomization (Lee et al., "A Simple Randomization
Technique for Generalization in Deep RL", https://arxiv.org/abs/1910.05396;
and the FinRL data-augmentation line, https://doi.org/10.1109/ICDMW51313.2020.00093).

**Code change.** (single variable vs v26: train episode start, `fixed → random`)
- In `IntegerTradingEnv.reset()`, **for the training env only**, set
  `self.day = np.random.randint(0, len(self.df.index.unique()) - MIN_EPISODE_LEN)`
  and run to end-of-series (or a fixed 252-bar window from that start).
  Recompute the initial `state` from `self.day`. Gate with a constructor flag
  `random_start=True` passed only when building the training env; val/test envs
  keep `random_start=False` (deterministic day-0 start, full window).
- Everything else byte-identical to v26. *(Optional stacked knob: also randomize
  episode length — hold for a follow-up so this stays single-variable.)*

**How to run.** `python run_panel.py v28`

**Diagnostic to look for.**
- If training EV drops and val stops decaying past 100k → temporal overfit was
  real and this is the fix. If EV **stays** 0.99 → the residual overfit is
  feature-side (favor v27), not temporal. Either outcome is informative.
- **Target stock:** all; RELIANCE/TATAMOTORS (long trends the fixed-start LSTM
  can memorize) are the clearest reads.

---

## Rl_v29.py — multi-subwindow validation selection (fix the broken oracle) — HIGHEST PRIORITY

**Hypothesis.** The screen already *proved* the val signal is misaligned, not
merely noisy: 6-indicators → perfect test / -47 val; `n_steps=1024` → +26 test
/ -75 val. A single short contiguous val window is one regime draw; picking
`argmax` of a single val return over-fits the *selector* to that regime. Score
each checkpoint on the **mean outperformance across K disjoint val
sub-windows** instead — a poor-man's combinatorial-purged-CV (López de Prado,
*Advances in Financial ML*, ch. 7; https://en.wikipedia.org/wiki/Purged_cross-validation)
— so the saved policy must generalize across several regimes, not luck into
one. **This caps the value of every regularizer above; do it first.**

**Code change.** (single variable vs v26: val score = single-window return →
mean over K sub-windows)
- In `ValidationCallback`, split the val slice into `K=3` contiguous, disjoint
  sub-windows. On each eval, run the deterministic policy through each
  sub-window, compute per-window outperformance vs its own B&H, and set
  `val_score = mean(outperf_k)`. Save the best-`val_score` checkpoint (keep the
  existing `min_val_trades` gate, applied **per sub-window** — see caveat — and
  the 100k warmup).
- **Sub-window length / variance caveat (advisor).** The val slice is only ~15%
  of a few-thousand-bar series (~300 bars), so `K=3` gives ~100-bar sub-windows.
  Outperformance over ~100 bars can rest on a handful of trades, so each
  per-window number is itself high-variance — the mean-of-3 is only clearly
  more stable than the single window if each sub-window clears a **per-window
  min-trades guard** (e.g. ≥3 trades); windows below that are dropped from the
  mean rather than counted as 0. If most sub-windows fail the guard, `K=3` is too
  fine for this val length — fall back to `K=2`. State the realized sub-window
  length in the run log so this is auditable.
- Everything else byte-identical to v26. *(Sharpe/return-vol-blend scoring is a
  separate one-variable fork — see v20 for the Sharpe version; keep them
  distinct.)*

**How to run.** `python run_panel.py v29`

**Diagnostic to look for.**
- Does the selected-checkpoint **step** stabilize across seeds 42/43/44 (the
  argmax selector currently jumps around)? Lower seed-variance of the *selected
  step* is the primary success signal.
- HDFCBANK and INFY (the lucky-checkpoint and late-decay casualties) are the
  priority reads. Test-outperf variance across seeds should shrink even if the
  mean barely moves.
- **Target stock:** HDFCBANK, INFY.

---

## Rl_v30.py — coarse cross-asset regime bit (market up/down vs 200-DMA)

**Hypothesis.** CLAUDE.md attributes the HDFCBANK failure to missing
*cross-asset* context. But a raw continuous index log-return is ~beta-collinear
with the stock's own return on daily bars — little orthogonal signal, mostly
new overfit surface, and against the "less capacity" grain (advisor). A
**single low-dimensional, orthogonal** regime feature threads that needle: a
binary bit = *is the market above its 200-day moving average?* One dim of new,
non-redundant information (broad regime), not 22nd redundant TA indicator.

**Code change.** (single variable vs v26: +1 regime-bit feature)
- Build a market proxy = the cross-sectional **mean daily close** across all
  NIFTY50 names already in `data/` (self-contained; no external index file
  needed). Compute its 200-day SMA. Add one observation column
  `MKT_REGIME ∈ {0,1}` = `1[proxy_close > proxy_SMA200]`, aligned by date,
  causal (same-day close vs a *trailing* SMA200 — no look-ahead). Indicator
  list 22 → 23.
- **Proxy-construction caveat (advisor).** A cross-sectional mean over "names in
  `data/`" is composition/survivorship-sensitive: which tickers exist early in
  the sample biases the proxy, and each date must be aligned before averaging.
  Require a full 200-bar burn-in before the SMA is valid, and hold the proxy's
  constituent set fixed across the whole sample (don't let names appear/drop
  mid-series) so the regime bit isn't secretly tracking universe composition.
- Everything else byte-identical to v26. *(Honest caveat: this ADDS a feature,
  cutting against the champion direction; it earns its keep only if the bit is
  genuinely orthogonal. If it regresses, that confirms cross-asset info at daily
  resolution is subsumed by within-asset trend features.)*

**How to run.** `python run_panel.py v30`

**Diagnostic to look for.**
- Split test performance by regime bit: does the policy trade *differently*
  (lower exposure in bit=0)? If the action distribution is invariant to the
  bit, the feature is ignored and this is dead weight.
- **Target stock:** HDFCBANK, and high-beta names (TATAMOTORS, ADANIENT).

---

## Rl_v31.py — linear learning-rate decay schedule

**Hypothesis.** Val peaks ~100k then decays — the classic signature of a policy
that keeps churning into the training set late in training. A constant LR keeps
taking full-size steps at 200k. A **linear LR decay to 0** shrinks late-training
updates, freezing the policy near its best-generalizing point. This is distinct
from the already-screened *constant*-LR changes (1e-4 and 1e-3 both regressed):
a schedule, not a level. Standard PPO practice (the SB3 default examples use
linear LR schedules for exactly this).

**Code change.** (single variable vs v26: `learning_rate` const → linear schedule)
- In `train_ppo_model`, replace `"learning_rate": 3e-4` with a callable
  `"learning_rate": lambda progress_remaining: 3e-4 * progress_remaining`
  (SB3 passes `progress_remaining` 1→0 over training).
- Everything else byte-identical to v26.

**How to run.** `python run_panel.py v31`

**Diagnostic to look for.**
- Val curve past 100k should flatten instead of decaying; policy `std` should
  not collapse to near-0 (over-freezing).
- **Target stock:** INFY (late-training overfit is its documented failure mode).

---

## Rl_v32.py — target_kl trust-region early-epoch stop

**Hypothesis.** PPO's `target_kl` aborts the per-rollout epoch loop once the
policy has moved more than a KL budget from the behavior policy, preventing the
occasional over-large update that memorizes a rollout. Cheap, untried, a pure
trust-region stabilizer. **Honest flag (advisor):** this stabilizes *training*,
not *generalization* directly — lowest expected effect of the credible forks;
worth it only as cheap insurance / a stacker under a real anti-overfit win.

**Code change.** (single variable vs v26: `target_kl` `None → 0.02`)
- Add `"target_kl": 0.02` to the `RecurrentPPO` kwargs.
- Everything else byte-identical to v26.

**How to run.** `python run_panel.py v32`

**Diagnostic to look for.**
- `approx_kl` in the log should cap near 0.02; effective `n_epochs` drops late
  in training. If it never triggers, updates were already within budget → no-op.
- **Target stock:** any; general stabilizer.

---

## Rl_v33.py — train/val/test purge-embargo gap

**Hypothesis.** The splits are chronological and the kept indicators are
audited-causal, but daily bars are serially correlated: rows straddling the
train→val and val→test boundaries share overlapping indicator lookback windows
and autocorrelated returns, so a policy can score well on the first val bars for
reasons that don't generalize — inflating the selector. **Embargoing** a small
gap of `E` bars after each split boundary (drop them from training/eval) is the
López de Prado fix for exactly this leakage
(https://en.wikipedia.org/wiki/Purged_cross-validation). Pairs with v29 — v29
makes the val score multi-regime, v33 makes each region clean at its edges.

**Code change.** (single variable vs v26: embargo gap `E`, `0 → 30` bars)
- After the 70/15/15 chronological split, drop the first `E=30` bars of the val
  slice and the first `E=30` bars of the test slice (equivalently, insert a
  30-bar gap at each boundary). **`E` must be ≥ the longest indicator lookback**
  (`STDEV_30` = 30 bars): with a smaller gap the first eval bars' indicators are
  still computed from rows adjacent to (or inside) train, so the leakage is not
  actually killed. `E=30` (round to 30–35) is therefore the *minimum* correct
  value, not a "conservative" one — an earlier draft's `E=10` was under-sized and
  would have left boundary leakage intact.
- Everything else byte-identical to v26.

**How to run.** `python run_panel.py v33`

**Diagnostic to look for.**
- Val-vs-test gap should shrink if boundary leakage was inflating val. If it
  doesn't move, leakage was already negligible (the causal-indicator audit was
  sufficient) — a useful null result.
- **Target stock:** all; measured at the panel level via the val/test spread.

---

## Rl_v34.py — gSDE exploration (generalized State-Dependent Exploration)

**Hypothesis.** The action space is continuous `Box[-1,1]` (scaled to integer
shares), so SB3's **gSDE** (`use_sde=True`) applies. gSDE replaces
independent-per-step Gaussian action noise with smooth, *state-dependent*
exploration noise that is consistent within a rollout; it was introduced
specifically to improve robustness/generalization in continuous control
(Raffin et al., "Smooth Exploration for Robotic RL",
https://arxiv.org/abs/2005.05719). One-flag, mechanistically new to this
project, no interaction with the reward or the val signal — a clean
single-variable fork and a cheap high-information probe.

**Code change.** ("enable gSDE" = two coupled knobs, one conceptual variable vs
v26: `use_sde` `False → True`, `sde_sample_freq` `-1 → 4`)
- Add `"use_sde": True` and `"sde_sample_freq": 4` to the `RecurrentPPO` kwargs.
- **Acceptance confirmed (not deferred).** `RecurrentPPO.__init__` in
  `sb3-contrib` exposes `use_sde: bool = False` and `sde_sample_freq: int = -1`
  (verified against the sb3-contrib source, and `requirements.txt` pins
  `sb3-contrib>=2.2.0`), so this is a real fork, not a silently-ignored no-op.
  The residual risk is *behavioral*: gSDE on the recurrent `MlpLstmPolicy` — watch
  entropy/`std` and confirm exploration doesn't collapse. `sde_sample_freq=4`
  resamples the exploration matrix every 4 steps (`-1` = once per rollout).

**How to run.** `python run_panel.py v34`

**Diagnostic to look for.**
- Smoother action trajectories (fewer whipsaw trades); trade count should drop
  vs v26. Entropy/std behavior differs from the default Gaussian head.
- **Target stock:** INFY (over-traded 206 trades into losses — the smooth-
  exploration case), and RELIANCE/TATAMOTORS (hold-through-trend cases).

---

## Note on already-designed high-value forks (do NOT duplicate)

Two existing unrun designs remain high-value and should be run before inventing
more forks — flagged here so future research sessions don't re-propose them:

- **v19 (B&H-relative reward)** — *unrun, NOT rejected.* Directly targets the
  system's actual loss (making absolute money while losing to bull-trending
  B&H). Advisor ranks this above v30–v32. Re-baseline it onto the v26 22-
  indicator set when run.
- **v22 (multi-seed ensemble)** — the most literature-robust variance killer
  (ensembling ~cuts variance 1/√N). Cheap, stackable, and likely beats the
  small regularizers here. Re-baseline onto v26.

Both predate the v26 champion; when run, fork them **from v26** (22 indicators),
not from v18.
