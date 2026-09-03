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

---

## Rl_v35.py — explicit per-step turnover penalty (attacks over-trading)

**Hypothesis.** INFY's documented failure is *over-trading into losses* (206
test trades, whipsaw); several other stocks trade 90–160 times. The 0.25%/side
cost model already penalizes turnover, but only **implicitly and with delay** —
each trade's cost lands in `eq_t` and reaches the policy through the log-return
reward one step later, a weak/late credit-assignment signal for "you trade too
much." An **explicit, immediate** per-step turnover penalty sharpens that signal
without changing the primary reward's shape. This is mechanistically distinct
from every rejected reward experiment: it is not DSR (no volatility
denominator), not weight regularization (acts on the reward, not parameters),
not the deepening-DD penalty (penalizes trading frequency, not drawdown), and
not B&H-relative (no benchmark term). It targets a *different* pathology
(churn), so it can stack with them later.

**Code change.** (single variable vs v26: turnover coefficient `τ`, `0 → 0.02`)
- In `IntegerTradingEnv.step()`, after computing the primary log-return reward
  and the existing DD penalty, subtract
  `τ * (abs(shares_traded_this_step) / hmax)` where `shares_traded_this_step`
  is the integer share delta the env just executed and `hmax` normalizes it to
  ~[0,1]. Start `τ = 0.02` (small relative to the ±10 reward clip). Reward at
  eval/test is report-only, so this affects training incentives only.
- Everything else byte-identical to v26.

**How to run.** `python run_panel.py v35`

**Diagnostic to look for.**
- **Trade count must drop** vs v26 on INFY (the primary read). If it doesn't,
  `τ` is too small; if it drops to near-zero (degenerate cash-hold caught by the
  `min_val_trades` / degeneracy guard), `τ` is too large — sweep `τ ∈
  {0.01, 0.02, 0.05}` in follow-ups (each a single-variable step).
- Watch that per-trade *quality* (win rate) doesn't fall as count drops — the
  goal is fewer, better trades, not just fewer trades.
- Honest flag: this partly double-counts the cost model; if it regresses on
  low-turnover stocks (TCS, 90 trades), the implicit cost signal was already
  sufficient there and the penalty only helps the churn cases.
- **Target stock:** INFY (206 trades), then HDFCBANK / ADANIPORTS.

---

## DESIGN ONLY — v36: stack the two positive capacity-reduction levers (n_steps=256 + lstm_hidden=64)

**(answers FRONTIER NEXT-ACTION #2; do NOT implement until the single-variable
screens confirm — this is deliberately a two-variable change and must wait.)**

The auto-tinker screen found `n_steps 512→256` (+17.4pp) and `lstm_hidden
128→64` (+9pp) as the two largest *positive* single-variable moves off v26, both
under the (unreachable-on-this-panel) 60.4pp gate. The open question the
frontier raises: **do they stack?** Both are capacity/variance reducers acting
on different axes — rollout length vs model width — so they are *a priori* more
likely to be complementary than the v10/v11 reward+reg pair that offset. But the
project's hard-won process rule is "isolate before stacking" (v10/v11
regressed exactly because two individually-plausible changes offset each other).

**Why DESIGN ONLY / the discipline.** Stacking two changes at once forfeits
causal attribution if the result is ambiguous. Correct sequence: (1) confirm
`n_steps=256` alone on the full panel (not just the 3-stock proxy); (2) confirm
`lstm_hidden=64` alone on the full panel; (3) *only if both hold* build
`v36 = v26 + n_steps=256 + lstm_hidden=64` and check for super-additivity
(combined > max of the two) vs mere redundancy (combined ≈ the better single).
If a run-routine has already confirmed one of the two on the full panel, the
*other* becomes a legitimate single-variable fork from that new baseline — chase
the frontier, don't re-fork from v26. Target reads: RELIANCE (LSTM=64 gave
+11pp in the proxy) and HDFCBANK.

**Also considered and deliberately NOT proposed** (to avoid low-value padding):
*entropy-coefficient decay schedule* — too close in spirit to v31's LR decay and
to the already-screened constant `ent_coef=0.05`, low marginal information;
*observation frame-stacking* (`VecFrameStack`) — the recurrent `MlpLstmPolicy`
already supplies temporal memory, so stacked frames are largely redundant with
the LSTM hidden state. Both are logged here as evaluated-and-deprioritized so a
later session doesn't spend a slot rediscovering that.

---

# Variants v37–v41 — single-variable forks from the v18 PRODUCTION CHAMPION

**Re-anchoring note (2026-09-03, auto-research).** The FRONTIER now records that
**v26 (feature reduction 98→22) was a degenerate artifact**, not a win: both of
its "B&H-beating" stocks were near-inactive cash-holds (ADANIENT 0 trades,
HDFCBANK 5 trades) that beat B&H only because those windows were bear markets,
while ITC regressed +40pp→−61pp. The auto-tinker 3-stock proxy champion was the
same TATAMOTORS cash-hold artifact (+177pp val while B&H = −55.75%). **Feature
reduction is an invalidated direction, and the previous session's v27–v34 forks
(anchored to v26) are built on an invalidated baseline.** These new proposals are
therefore anchored to **v18**, the restored production champion, and every one is
constrained by the frontier's hard requirement: *the next challenger must beat
v18 with GENUINE ACTIVE policies (≥20 trades/stock)* — a cash-hold that wins a
bear window does not count.

**Dominant failure mode this batch attacks.** The board has now proven the
failure is largely **selection-side, not just the generalization gap**. The
`ValidationCallback` selects `best-by-val-RETURN`; in a bear val window a
do-nothing cash-hold posts the highest raw return and gets locked in as "best".
The literature calls this out directly: a single validation period is easily
biased by a market up/down-trend, so best-by-raw-return over one window is not a
sound selector (López de Prado, *Advances in Financial Machine Learning*; the
walk-forward-overfitting and CPCV line of work below). v37/v38 fix the *selector*;
v39 attacks the same degeneracy from the *reward* side; v40/v41 are orthogonal
generalization levers. Each changes exactly one variable vs v18.

**Blocker ranking (advisor pass, 2026-09-03) — read before picking what to run.**
An independent advisor reordered the levers by how *fundamental* the blocker is,
and the project's own evidence backs it: `significance.py` → 0/49 stocks survive
FDR; `baselines.py` → PPO ≈ a coin flip vs SMA/momentum and its mean outperformance
is *worse* than a dumb SMA rule. That is the efficient-markets null holding on
daily single-stock TA features. Ranking:
1. **Features / signal (the real ceiling).** Daily pandas-ta indicators are lagging
   and collinear; they carry little out-of-sample *timing* alpha, which is exactly
   what beats a bull-trending B&H. No reward or selector change extracts alpha that
   is not in the inputs. The only two levers that raise this ceiling are **pooled
   cross-asset training (the existing v24 — ~50× the data, the single most credible
   fix for the EV=0.99 memorization)** and **exogenous regime/cross-asset features
   (v40, and its richer forms below)**. These two should get the compute.
2. **Selection (loop integrity — a *precondition*, not a competitor).** v37/v38 fix
   the harness so results stop being fooled. Mandatory before trusting ANY
   challenger, but they pick from the policies training produces — they cannot
   create edge.
3. **Reward (least likely the blocker).** v18's `clip(log(eq_t/eq_{t-1})*100)` is
   already a correct, dense, scale-invariant, alpha-aligned objective. Reward forks
   (v19 B&H-relative, v25 DD, v39 inaction) mostly reshape the reward's mean/variance,
   not the argmax policy. v39 is included as the reward-side anti-degeneracy option
   but is explicitly deprioritized vs the selector fix and the feature levers.

So the honest priority order for RUN routines: **v37 (fix the harness) → v24 pooled
+ v40/richer features (raise the ceiling) → v41/v22 ensembling (variance) →
v38 (robust selector) → v39 (reward, only if v37 alone doesn't yield active policies).**

**Sources.**
- Combinatorial Purged Cross-Validation & Deflated/Probabilistic Sharpe for model
  selection under backtest overfitting — de Prado / Bailey & de Prado, summarized
  at https://github.com/eslazarev/purged-cross-validation/blob/main/paper/paper.md
  and https://www.garp.org/hubfs/Whitepapers/a1Z1W0000054x6lUAA.pdf
- Walk-forward overfitting: single validation window biased by a trend —
  https://arxiv.org/abs/2512.12924 (walk-forward validation framework, 34 rolling
  test periods) and https://arxiv.org/pdf/2209.05559 (DRL crypto, addressing
  backtest overfitting).
- Alpha-reward for *active* DRL trading (reward the agent for active alpha vs a
  passive benchmark) — https://arxiv.org/html/2607.16028v1 (CLaC @ FinMMEval 2026
  Task 3, "Alpha-Reward Approach").
- Inaction / missed-opportunity penalty (penalize holding cash as a foregone
  risk-free return) — pattern documented in DRL-trade reward designs,
  https://github.com/ebrahimpichka/DeepRL-trade and the FinRL ensemble line,
  https://arxiv.org/pdf/2511.12120.
- Regime / cross-asset conditioning (VIX-style volatility state, index trend) —
  https://arxiv.org/pdf/2605.27848 (regime + RL) and the regime-detection review
  https://arxiv.org/pdf/2108.05801.
- Stochastic Weight Averaging for flatter minima / better generalization —
  Izmailov et al., https://arxiv.org/abs/1803.05407.

---

## Rl_v37.py — exposure-adjusted-alpha validation selector (fix the degenerate selector) — MEASUREMENT-INTEGRITY PREREQUISITE

**Hypothesis.** The single change that would have prevented the v26 / proxy-champion
artifacts is in the *selector*, not the model. v18 saves `best-by-val-RETURN` with
only a weak `min_val_trades=5` gate. In a bear val window the do-nothing cash-hold
posts the top raw return AND can clear 5 trades by chance, so it is selected; on
test it then holds cash (loses in a normal/bull window) or was never a skilled
policy. Change the *score the callback maximizes* to an **exposure-adjusted active
return** (exposure-matched Jensen's alpha) and raise the activity gate to the
frontier's genuineness bar. A bear-window cash-hold has exposure ≈ 0, so its
benchmark is cash and its active return ≈ 0 → score ≈ 0 *by construction*; it can
no longer win the checkpoint race, and an inactive policy is hard-rejected outright.

**Critical design correction (advisor pass, 2026-09-03).** The naive score
"alpha-over-B&H information ratio" = `(policy_ret − bh_ret)/std` has a HOLE: a
cash-hold in a *bear* window has positive, low-variance active return vs a
*falling* B&H → a **high** IR. Raw return (v18), raw Sharpe (v20), and naive
IR-over-B&H all reward the degenerate cash-hold. The fix is to benchmark against
*the agent's own realized exposure*, not full B&H:
```
active_t = policy_ret_t − exposure_t · bh_ret_t          # exposure_t = invested fraction at step t
score    = mean(active_t) / (std(active_t)·√252 + eps)   # annualized info ratio of exposure-adjusted active return
```
When the agent holds cash (`exposure_t≈0`) its per-step benchmark is cash, so
`active_t ≈ policy_ret_t ≈ 0` and the score collapses to ≈0. Only a policy that is
genuinely *invested* AND beats the return of that same invested exposure scores
well. This is materially different from v17's `min_val_trades` gate (which left the
raw-return SCORE intact) and from v20's raw Sharpe.

**Code change (single variable: the val selection objective).**
- `Rl_v37.py` `ValidationCallback.__init__` (~line 623): `self.best_return` →
  `self.best_score`; raise `self.min_val_trades` to **20** (frontier genuineness),
  and add a **churn ceiling** `self.max_val_trades` (e.g. `len(val_bars)` — reject
  a policy that trades essentially every bar, which bleeds cost). Dual gate.
- `Rl_v37.py` `_eval_on_val` (~lines 688–711): each step, record the portfolio
  value `pv_t` AND the invested fraction `exposure_t = (shares·price)/total_asset`
  from the cached `_price_slice`/`_shares_slice`. After the loop, compute the
  per-step B&H return `bh_ret_t` from the val close series, form
  `active_t = pv_ret_t − exposure_t·bh_ret_t`, and `score = mean/std·√252` per the
  formula above. Return `(val_return_pct, exposure_adj_score, trade_count)`.
- `Rl_v37.py` `_on_step` (~lines 638–658): eligibility = `min_val_trades ≤
  val_trades ≤ max_val_trades`; compare `score > self.best_score`; print score +
  mean exposure so degeneracy is visible in the log.
- Everything else (env, reward, warmup=100k, eval cadence) byte-identical to v18.

**Framing (advisor).** This is a *measurement-integrity precondition*, not an
alpha source. The cash-hold artifact has now corrupted three things — the v26
verdict, the fast proxy panel, and the selector — i.e. ONE measurement-validity
failure contaminating the whole loop. A fixed selector stops the loop being
*fooled*; it cannot *manufacture* edge (if training produces no genuine active-alpha
policy, a correct selector honestly reports "no eligible checkpoint"). Run v37
FIRST and treat `significance.py` + `baselines.py` as a re-run gate on every
challenger downstream.

**How to run.**
```bash
python run_panel.py v37
# or one stock:
python -c "from Rl_v37 import process_stock, NIFTY50_PATH; import os; \
  process_stock(os.path.join(NIFTY50_PATH, 'HDFCBANK_daily.csv'))"
```

**Diagnostic to look for.**
- `eval_history` should now store `(timestep, val_return, val_bh, alpha, score,
  trades)`. On a stock where v18 saved a cash-hold, v37 should save a *different*,
  active checkpoint (trade count ≥20) and the saved-checkpoint alpha should be >0.
- Panel check: the two frontier "artifact" stocks (ADANIENT, HDFCBANK) must now
  either produce ≥20-trade active policies or be reported as *no eligible
  checkpoint* (honest null) — never a 0/5-trade cash-hold masquerading as a win.
- **Target stocks:** HDFCBANK and ADANIENT (the confirmed cash-hold artifacts);
  ITC as control (v18 already beats B&H there — v37 must not regress it).

**Honest caveat.** If NO checkpoint on a stock ever clears the ≥20-trade + positive
alpha bar, v37 will legitimately refuse to pick one (fall back to last policy or
report null). That is the correct behavior — it surfaces "no genuine edge here"
instead of laundering a cash-hold into a fake win — but it means v37's headline
"beats-B&H count" may *drop* while its *genuineness* rises. Judge v37 on genuine
active wins, not raw count.

---

## Rl_v38.py — multi-window (CPCV-style) robust validation selector

**Hypothesis.** Even an alpha-scored selector over a *single* val window is
hostage to that one window's regime. de Prado's Combinatorial Purged
Cross-Validation and the walk-forward-overfitting literature show the fix:
evaluate each candidate over *many* disjoint sub-paths and select on the
*distribution* of outcomes, not one draw. Split the 15% val slice into **K=3
contiguous, non-overlapping sub-windows** (with a small purge/embargo gap between
each and vs train/test to kill leakage), score alpha on each, and select the
checkpoint that maximizes **`mean(alpha_k) − 1.0·std(alpha_k)`** (a
worst-case-leaning, robustness-penalized score). A policy that only wins because
one sub-window was a lucky bear/bull draw is penalized by the std term and loses
to a policy that is positive across all three. This directly attacks BOTH
degeneracy modes on record: the cash-hold-in-one-bear-window artifact (v26) *and*
the active-but-overfit-to-one-window collapse (HDFCBANK/INFY on test).

**Code change (single variable vs v18: val window → K purged sub-windows + robust
score).** Note: to keep this a *clean* single-variable comparison vs v37, the
per-window score reuses raw val return (v18's metric), NOT v37's alpha — so v38
isolates the *multi-window robustness* variable alone. (An alpha×multi-window
combination is deliberately deferred to a DESIGN-ONLY stack, below, to avoid the
v10/v11 two-changes-at-once trap.)
- `Rl_v38.py` `ValidationCallback.__init__`: add `n_val_windows=3`,
  `embargo_bars=5`; precompute the K sub-slices of `val_df` by date with an
  `embargo_bars` gap dropped between adjacent windows; `self.best_score` replaces
  `best_return`.
- `Rl_v38.py` `_eval_on_val`: loop the existing single-window eval over each
  sub-slice, collect `returns_k` and `trades_k`; require *every* window to clear
  `min_val_trades` (else ineligible); `score = mean(returns_k) - 1.0*std(returns_k)`.
- `_on_step`: select on `score`. Everything else identical to v18.

**How to run.** `python run_panel.py v38`  (targets INFY, HDFCBANK, TATAMOTORS —
the single-window overfit casualties).

**Diagnostic to look for.**
- Per-window returns printed at each eval. The winning checkpoint should have a
  *low std* across windows, not the highest single-window return. If v38 selects a
  different (steadier) checkpoint than v18/v37 and it generalizes better on test,
  the robustness variable is doing work.
- **Trap to watch:** K=3 over a 15% val slice leaves each sub-window short (~1
  year of daily bars); if a window is too short the std term is dominated by
  sampling noise and over-penalizes. If every stock goes ineligible, K is too
  large for the slice — fall back to K=2. Log the per-window bar counts.

---

## Rl_v39.py — inaction / missed-opportunity reward penalty (reward-side anti-degeneracy)

**Hypothesis.** Attack the cash-hold degeneracy from the *reward* side instead of
the selector. v18's reward is `clip(log(eq_t/eq_{t-1})*100, -10,10) − DD_penalty`;
holding 100% cash yields reward ≈ 0 every step, which in a falling market is the
single best action — so the *optimal* policy on a bear window genuinely is to do
nothing, and the agent correctly learns cash-holding. Add a small **inaction
penalty**: each step the agent holds less than a threshold exposure `x*` of its
capital in the stock, subtract `κ` from the reward — the standard "foregone
risk-free/opportunity cost of sitting out" term from DRL-trade reward designs.
This makes pure cash-holding strictly costly, forcing the agent to take genuine
positions (≥20 trades naturally) and learn *when* to be in vs out rather than
defaulting to out.

**Code change (single variable vs v18: one added reward term).**
- `Rl_v39.py` `IntegerTradingEnv.__init__` (~line 422): add `self._inaction_kappa
  = 0.02`, `self._min_exposure = 0.10`.
- `Rl_v39.py` `step()` (~lines 511–527): after `reward = primary - dd_penalty`,
  compute `exposure = position_value / total_asset` from the cached `_price_slice`
  / `_shares_slice`, and `reward -= self._inaction_kappa * max(0.0, self._min_exposure
  - exposure)`... i.e. penalize proportionally to *how far below* the min exposure
  the agent is (full cash = full `κ*_min_exposure` penalty; ≥10% invested = 0).
- Nothing else changes (selector, features, hyperparams identical to v18).

**How to run.** `python run_panel.py v39`  (target ADANIENT/HDFCBANK — the
cash-hold artifacts — and ITC as the "don't break a working active policy" control).

**Diagnostic to look for.**
- Trade count on the previously-degenerate stocks must rise to ≥20 and the val
  curve must show the agent taking positions. If `κ` is too high the agent
  over-trades into costs (watch for a turnover explosion / test return collapse) —
  that's the v35 turnover-penalty regime in reverse, so `κ=0.02` is deliberately
  small (≈0.02 reward units vs a typical clipped log-return of ±1–3).
- **Honest risk (flag).** This is a *reward-shaping* change, and the board's track
  record on reward shaping is poor (DSR, deepening-DD both regressed; B&H-relative
  is unrun). The distinction: those changed the *primary* return signal; v39 adds a
  *bounded, tiny, one-sided* penalty that only bites at ≈0 exposure, so it should
  not distort the return gradient the way DSR's exploding denominator did. Still —
  run v37 (selector fix) FIRST; if the selector fix alone produces genuine active
  policies, v39 is unnecessary and its reward-distortion risk isn't worth taking.

---

## Rl_v40.py — market-regime conditioning feature (index trend state)

**Hypothesis.** Every v18 policy sees only its own stock's indicators; it has no
idea whether the *broad market* is in a risk-on or risk-off regime. The
regime-detection literature (VIX-thresholded states; index-trend filters) shows a
single coarse regime signal materially improves out-of-sample robustness because
it lets one policy behave differently across regimes instead of averaging over
them. Add ONE feature: the sign/normalized distance of the **NIFTY50 index** from
its own 200-day moving average (a risk-on/risk-off bit), broadcast into every
stock's observation. This is a *feature ADD* (observation 101→102), the opposite
of the invalidated feature-reduction direction, and is a single new column.

**Code change (single variable vs v18: +1 regime feature column).**
- Requires a `NIFTY50_INDEX_daily.csv` (or `^NSEI`) in `NIFTY50_PATH`. In
  `process_stock`, load the index series, compute `regime = clip((index_close −
  SMA200(index_close)) / SMA200(index_close), −1, 1)`, forward-fill and
  date-align to the stock's frame (STRICT causal align — index value at date `t`
  only, no lookahead), and append as a new indicator column present in train, val,
  and test identically. Add its name to `list_of_indicators`.
- Env, reward, selector, hyperparams unchanged.

**How to run.** `python run_panel.py v40`  (target the whole panel; regime signal
should help most on stocks whose test window spans a market regime change —
ADANIPORTS, TATAMOTORS).

**Diagnostic / caveat.**
- **DATA DEPENDENCY (blocker to flag for run routines):** the repo ships per-stock
  CSVs only; a NIFTY index CSV must be sourced and placed in `NIFTY50_PATH` first.
  If unavailable, a *proxy* index can be built as the equal-weight average of the
  50 stock closes over their common date range (compute once, cache) — note this is
  survivorship-biased but adequate as a coarse regime bit. Log which source was used.
- Causality: this MUST pass `test_indicator_causality.py`-style prefix-equality
  (the regime column computed on the train prefix alone must equal its values when
  the full series is present). A 200-DMA is trailing so it is causal, but the
  date-alignment/ffill is the leak-risk — audit it.
- If the regime feature helps, it is *stackable* under v37/v38 later (feature +
  selector are orthogonal). Keep it single-variable for the first read.

---

## Rl_v41.py — Stochastic Weight Averaging over top-K val checkpoints

**Hypothesis.** v18 restores the *single* best-val checkpoint — a sharp point in
weight space that the generalization-gap diagnostics (EV pegged 0.95–0.99, val
decaying after 100k) say is overfit. Stochastic Weight Averaging (Izmailov et al.,
2018) shows that *averaging the weights* of several good checkpoints finds a flatter
minimum that generalizes better at ~zero extra training cost. Instead of keeping
only the argmax-val checkpoint, keep the **top-K=3 by val alpha** and test with
their **parameter-averaged** policy.

**Code change (single variable vs v18: restore-best → restore-SWA-of-top-K).**
- `Rl_v41.py` `ValidationCallback`: retain the top-K checkpoints (by val return, to
  stay single-variable vs v18's metric) on disk instead of only the best.
- `Rl_v41.py` `train_ppo_model` post-`.learn()`: load the K saved `state_dict`s,
  average the tensors elementwise into the policy, save as the restored model. Use
  the VecNormalize snapshot of the *median* checkpoint (or average the running
  stats).
- Env/reward/features/hyperparams identical to v18.

**How to run.** `python run_panel.py v41`  (target INFY/TATAMOTORS — highest
seed/checkpoint variance in the v18 batch).

**Diagnostic / caveat.**
- Compare test return of the SWA policy vs each of its K constituent checkpoints. If
  `SWA ≥ mean(constituents)` and variance drops, SWA is earning its keep.
- **Caveat (flag for implementer):** naive elementwise averaging of an **LSTM
  policy's** weights across checkpoints is only sound when the checkpoints are close
  in weight space (same basin); checkpoints from very different training stages
  (100k vs 200k) may not average cleanly and can degrade. Restrict K to
  *adjacent-in-time* eligible checkpoints, and verify the averaged policy still
  produces finite actions on a val rollout before trusting it. If it degrades, this
  reduces to an *action-space* ensemble (average the K policies' continuous actions
  per step, like v22's `ensemble_predict.py`) — a safe fallback that needs no weight
  averaging.

---

## DESIGN ONLY — v42: alpha-scored multi-window selector (stack v37 × v38)

Once v37 (alpha score) and v38 (multi-window robustness) each show an independent
win vs v18 on the full panel, stack them: score each checkpoint by
`mean_k(alpha_k) − 1.0·std_k(alpha_k)` over K purged val sub-windows. This is the
full CPCV-flavored selector the literature points to. **DESIGN ONLY** and gated
behind independent single-variable confirmation of BOTH v37 and v38 — combining two
selector changes before each is validated is exactly the v10/v11 two-changes-at-once
trap the project has already paid for twice. Do not implement until v37 and v38
each clear the panel gate on their own.

---

## Rl_v43.py — stationary block-bootstrap path augmentation (attack data starvation, not capacity)

**Hypothesis.** The root cause behind EV pegging at 0.95–0.99 while test lags is
**data starvation**: one 2500-bar series is far too little for a 128-hidden LSTM,
so it memorizes the single training path. Cutting capacity (v26) was invalidated;
adding compute (v15, 1M steps) directly overfit. The untried lever that raises the
*effective* sample size WITHOUT touching capacity or compute-per-path is **synthetic
training paths via the stationary block bootstrap** (Politis–Romano): resample
contiguous blocks of the training returns (geometric block length, mean ≈ 20 bars
to preserve short-horizon serial dependence) to generate many plausible alternative
histories, and train across them. This is a standard deep-RL-for-trading
regularizer (Zhang, Zohren & Roberts, 2020, *Deep Reinforcement Learning for
Trading*) and is categorically distinct from every rejected lever (DSR, weight-reg,
deepening-DD, 1M-steps, min-val-trades, feature-reduction).

**Code change (single variable vs v18: training data is bootstrapped, val/test
untouched).**
- `Rl_v43.py`: add `make_block_bootstrap_train(train_df, rng, mean_block=20)` that
  rebuilds a synthetic train frame by concatenating random contiguous blocks of the
  *scaled* train rows (bootstrap the return/indicator rows, NOT val/test — those
  stay the real, chronological slices so the selector and test remain honest).
- Each PPO training env `reset()` (or each `process_stock` call) draws a fresh
  bootstrapped train path from the SAME train slice; val and test paths are the
  real ones. VecNormalize still fits on the (bootstrapped) train stream.
- Selector, reward, features, hyperparams identical to v18.

**How to run.** `python run_panel.py v43`  (target the whole panel; the EV-vs-test
gap is the readout).

**Diagnostic / caveat.**
- Training EV should FALL below v18's 0.95–0.99 (the critic can no longer memorize
  one path); val curves should stop decaying after their 100k peak if augmentation
  is doing anti-overfit work.
- **Trap (flag):** block bootstrap can *destroy* the exact long-range serial
  dependence any timing edge relies on — if `mean_block` is too small the agent
  learns nothing (signal washed out); too large and you recover the single path.
  `mean_block≈20` (one trading month) is the starting point; it is a
  signal-washing knob, sweep it only AFTER the harness fix (v37) makes results
  trustworthy.
- **Leakage:** blocks must be drawn from the TRAIN slice only; a block straddling
  the train/val boundary re-introduces the lookahead bugs already paid for. Assert
  block source indices < train_end.

---

## DESIGN ONLY — v44: richer exogenous regime vector (extends v40)

Once v40's single index-trend bit shows signal, extend the *exogenous* feature set
(advisor's ranked-#1 lever) with a small vector of market-state inputs the policy
currently cannot see: **India-VIX level/percentile** (volatility regime),
**market breadth** (fraction of the 50-stock universe above its own 200-DMA), and a
**rate-regime proxy** if a rate series is available. Each is a single causal,
trailing column broadcast into every stock's observation. **DESIGN ONLY** and gated
behind (a) v40 confirming the index-trend bit helps and (b) sourcing India-VIX /
breadth data into `NIFTY50_PATH`. Keep it a *vector add*, not a swap — this is the
opposite of the invalidated feature-*reduction* direction. Warning (advisor): index
features can simply proxy B&H; verify the added columns change the policy's *timing*
(entry/exit vs regime) and are not just a level the critic latches onto — pair with
v24 pooled training so the thin per-stock sample doesn't just overfit the new
columns.
