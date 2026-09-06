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

# Variants v27–v36 — single-variable forks off the v26 CHAMPION (2026-09-02, auto/research)

> ## ⚠️ DEPRECATED BLOCK (2026-09-03) — anchored to the INVALIDATED v26 champion
> The FRONTIER has since confirmed **v26 was a degenerate cash-hold artifact**, not
> a champion, and restored **v18** as the production baseline (see the re-anchoring
> note in "Variants v37–v44" below). Every proposal in this v27–v36 block is forked
> from v26 and therefore rests on an invalidated baseline — **run routines should NOT
> queue these**; re-derive from v18 instead. Direct supersessions on the v18 baseline:
> **v29 (multi-window val) → v37/v38**; **v33 (purge/embargo) → v38** (embargo folded
> into the multi-window selector). The remaining v27/v28/v30/v31/v32/v34/v35 ideas, if
> still wanted, must be re-anchored to v18 before use. Kept on disk for auditability.

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

# Variants v37–v44 — single-variable forks from the v18 PRODUCTION CHAMPION

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
v41 and v22 are both variance-killers that overlap — run **one** first (v41 SWA is
zero extra training; v22 needs 3 seed-runs), not both in parallel.

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
  add a **churn ceiling** `self.max_val_trades` (e.g. `len(val_bars)` — reject a
  policy that trades essentially every bar, which bleeds cost), and a
  **mean-exposure FLOOR** `self.min_mean_exposure = 0.15`. **Required guard
  (advisor):** the trade-count gate counts *flips, not time in market* — a policy
  can clear ≥20 trades by churning in-and-out at ~0 net exposure (activity without
  conviction), which is still not a genuine active policy. Eligibility must AND-in
  `val_mean_exp ≥ min_mean_exposure` (the callback already computes `val_mean_exp`),
  so the gate is: `min_val_trades ≤ trades ≤ max_val_trades AND mean_exp ≥ floor`.
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

**Attribution note (advisor).** v37 bundles three sub-changes into "the selector":
the SCORE (exposure-adjusted IR), the trade floor (5→20), and the new ceiling +
exposure floor. Credit any v37 win to the **SCORE**, not the gate: `min_val_trades`
was already tested at 5 (v17) and found *inert* because that degeneracy is
test-side — so the gate change alone cannot be what makes v37 win. The gate only
enforces genuineness; the score is what stops a bear-window cash-hold from being
selected in the first place.

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
score).** v38 is a **parallel fork of v18, not of v37** (isolate-vs-champion). The
per-window score reuses **raw val return (v18's metric)**, so the ONLY delta vs v18
is the multi-window robustness aggregation — that keeps v38's acceptance run a clean
single step from the champion. (The shared v18 metric is also what later makes v42,
the alpha×multi-window stack, a clean single step from *either* v37 or v38.) The
alpha×multi-window combination is deferred to that DESIGN-ONLY v42 stack to avoid
the v10/v11 two-changes-at-once trap. **Bundled knob to disclose:** the purge/embargo
gap (`embargo_bars=5`) between sub-windows is a second small change — it is the same
idea as the deprecated v33 embargo, intrinsic to CPCV purging and therefore
acceptable as part of "the multi-window selector", but it is not literally one knob.
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

> **BLOCKED — data.** Needs a NIFTY50 index CSV that the repo does not ship. Do
> NOT queue an immediate run; first source the index file into `NIFTY50_PATH` or
> build the equal-weight proxy (see caveat). A run routine that picks this up
> without the data will fail on load.

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

---

## METHODOLOGY (not a variant) — Deflated-Sharpe challenger-acceptance gate

**Problem (advisor, 2026-09-03).** The project is ~40 configs deep (v6–v44 plus
~15 proxy experiments) with NO correction for multiple testing. Under that many
trials, a nominally-significant "win" is expected by chance — `significance.py`
already notes it does not correct for the ~20+ versions tried and would need a
Deflated Sharpe Ratio (Bailey & López de Prado) with the full trial record. Every
selector/feature fix above ADDS trials, so without this gate a v37/v40/etc. "win"
could be the same false-discovery trap that produced the v26 mirage.

**Proposed gate (extend `significance.py`, not a new Rl_vNN).** Before a challenger
is promoted on the FRONTIER, require its per-stock test Sharpe to clear the
**Deflated Sharpe Ratio** computed with `N_trials` = the count of configs tried to
date (track it in a `TRIALS.md` ledger), the observed cross-trial Sharpe variance,
and the return series' skew/kurtosis. Report PSR and DSR alongside the existing
Newey-West / block-bootstrap p-values and Benjamini-Hochberg FDR. A challenger that
beats v18 on raw outperformance but fails DSR is flagged "not distinguishable from
selection luck given the search depth" — exactly the label v26 earned in hindsight.

**Why it matters.** This does not raise the signal ceiling; it stops the loop
promoting mirages. Combined with v37's honest selector, it closes the two ways the
research loop currently fools itself (in-sample selection AND cross-trial
cherry-picking). Cheap: ~1 function in `significance.py` + a trials ledger.
Sources: Bailey & López de Prado (Deflated Sharpe / PSR);
https://www.garp.org/hubfs/Whitepapers/a1Z1W0000054x6lUAA.pdf.

---

## Rl_v45.py — stock-identity conditioning for pooled training (deepens the #1 lever, v24)

**Anchor.** Single-variable fork of **`Rl_v24.py` (pooled cross-stock training)**,
NOT v18 — because the advisor pass ranked pooled training the #1 lever that can
raise the signal ceiling (one policy over ~50 stocks ≈ 50× data, breaks the
EV=0.99 single-path memorization). This proposal is gated: run only AFTER v24
establishes a pooled baseline, so v45-vs-v24 stays a clean single-variable read.

**Hypothesis.** v24's known weakness (advisor): pooling all stocks into ONE
unconditioned policy can *wash out* per-stock structure — the shared net is forced
to average over 50 heterogeneous dynamics and may learn a bland market-beta policy.
The multi-task-RL fix is **task conditioning**: give the shared policy a per-stock
identity signal so it can specialize its behavior per stock while still sharing the
bulk of its parameters and the 50× data (Zhao et al., *Meta RL with Task Embedding
and Shared Policy*, IJCAI 2019; and multi-stock shared-policy work where the policy
"identifies overarching signals rather than memorizing a single price series"). Add
ONE conditioning input: a small fixed **stock-descriptor vector** (e.g. a
hash/one-hot-compressed stock id, or 2–3 slow cross-sectional stats like the
train-window volatility decile and median-price bucket) appended to every pooled
observation. The policy can then key its regime response on *which* stock it is
trading without a separate model per stock.

**Code change (single variable vs v24: +stock-descriptor conditioning column(s)).**
- `Rl_v45.py` `build_pooled_data()`: for each stock, precompute a small fixed
  descriptor (start simplest: a scalar `vol_decile ∈ [0,1]` = the train-window
  daily-return-vol percentile across the panel; optionally a `price_bucket`). Store
  per-stock.
- `PooledTradingEnv.reset()`: when it samples a stock+window, inject that stock's
  descriptor as (an) extra constant observation column(s) for the episode. Keep the
  intersection-of-indicators observation shape otherwise identical to v24.
- Everything else (pooled sampling, `PooledValidationCallback`, 2M timesteps, one
  global VecNormalize) byte-identical to v24.

**How to run.**
```bash
# after a v24 pooled baseline exists:
python Rl_v45.py
# smoke test (mirrors v24's):
V45_STOCKS="RELIANCE,INFY,ITC" TOTAL_TIMESTEPS=20000 V45_WARMUP=0 \
  V45_EVAL_FREQ=10000 python Rl_v45.py
```

**Diagnostic / caveat.**
- Per-panel val returns vs the v24 pooled baseline. If conditioning helps, the
  spread of per-stock behaviors should widen (the policy stops applying one
  averaged rule) and mean panel val return should rise above v24's.
- **Trap (flag):** a high-cardinality one-hot stock id is itself an overfit surface
  (the policy can memorize "stock 37 → do X in this window"). Start with the LOW-dim
  *descriptor* (vol decile / price bucket), which generalizes to unseen stocks,
  before trying a learned per-stock embedding. If a learned embedding is used, keep
  its dim ≤ 8 and verify held-out-stock generalization, not just in-panel fit.
- This is *stackable* under v37's fixed selector (the pooled `PooledValidationCallback`
  should adopt the exposure-adjusted-alpha score too) — but keep v45 single-variable
  vs v24 for the first read.

**Sources.** Zhao et al., Meta RL with Task Embedding and Shared Policy (IJCAI 2019),
https://www.ijcai.org/proceedings/2019/0387.pdf ; multi-stock shared-policy
generalization, https://arxiv.org/pdf/2506.04358 and
https://www.sciencedirect.com/science/article/abs/pii/S092523122400571X .

---

# Variants v46–v50 — single-variable forks from the v18 PRODUCTION CHAMPION (2026-09-04, auto/research)

**Anchor & framing.** All five fork the **v18 production champion** (v26 is an
invalidated cash-hold artifact — do NOT anchor to it). They target the project's
established #1 blocker: **the signal is the ceiling** (`significance.py`: 0/49 clear
Benjamini-Hochberg FDR; `baselines.py`: PPO ≈ coin-flip vs a dumb SMA rule; training
critic EV pegged 0.95–0.99 while test is poor → textbook generalization gap; val
curves peak ~100k then decay). Prior advisor blocker-ranking: **features >
selection > reward**. These five are therefore weighted toward **feature /
representation** levers (v46, v47, v48, v50) plus one **initialization** lever (v49),
because reward-side and capacity-side levers are largely exhausted (see the rejected
list in CLAUDE.md). Each is ONE variable vs v18.

**Cross-cutting requirement (applies to all five).** The FRONTIER's hard rule stands:
a challenger only counts if it beats v18 with **genuine active policies (≥20
trades/stock)** scored by **exposure-adjusted active return** (`active_t = pv_ret_t −
exposure_t·bh_ret_t`). Every proposal below MUST be validated with v37's honest
selector, not v18's raw-return selector, or it risks manufacturing another v26-style
cash-hold mirage. **The ≥20-trades/stock active-policy gate is a pass/FAIL
PRECONDITION on every fork below (advisor 2026-09-04), not merely part of the score:**
any fork that mutates the feature/representation path (v46, v47, v50, v51) can
reproduce the v26 cash-hold artifact, so a variant whose "wins" are sub-20-trade
cash-holds is FAILED outright, not ranked. Where a proposal changes the feature set,
it must also pass `test_indicator_causality.py`-style prefix-equality (train-prefix
values unchanged when future rows are appended).

**Advisor framing (2026-09-04): "gap-closers" vs "ceiling levers".** An independent
advisor pass stressed that only **more information** raises the *true* signal ceiling
— pooled data (v24/v45) or genuinely new **exogenous / cross-sectional** features.
Everything that reshapes the *same* indicator set (normalization, representation,
selection, aux losses, warm-starts) is a **generalization-gap closer**: it can
convert existing signal into more robust test performance (attacking the EV=0.99→
poor-test gap) but cannot manufacture alpha the features don't contain. Read the five
below with that expectation. The advisor's EV ranking for gap-closing on THIS system:
**v50 (rolling rank/z) > v47 (stationary representation) > v46 (train-only selection)
> v48 (aux head) > v49 (BC warm-start)**; a proposed cost-domain-randomization idea
was **dropped** (unrelated to the gap and actively cash-hold-prone). Crucially, the
advisor flagged a **ceiling lever we were missing — cross-sectional relative-strength
features (added below as v51)** — ranked above v46/v48 because it adds real
information rather than only closing the gap. Run order suggestion: **v50 first**
(cheapest, safest, causal by construction), then **v51** (the ceiling lever, buildable
from data already in the repo), then v47.

## Rl_v46.py — data-driven (train-only) feature selection by predictive importance

**Hypothesis.** v26 cut 98→22 indicators by *hand* and produced a degenerate
cash-hold — but that experiment confounded TWO things: fewer features AND an
*arbitrary* choice of which. The features-are-the-ceiling diagnosis still says the
observation is bloated (98 mostly-redundant TA columns feeding a 128-hidden LSTM on
one ~1750-bar train path is a memorization engine). The untried, principled lever is
**data-driven selection**: rank each causal indicator by its **train-only**
predictive relationship to next-day return and keep the top-K, so the cut is earned
by signal, not guessed. This is the standard anti-overfit feature-selection move in
DRL-for-trading (adaptive/importance-based selection; conditional-mutual-information
selection). Single variable vs v18 = **which features**, chosen by a fixed algorithm
rather than by hand.

**Code change (single variable vs v18: `list_of_indicators` → algorithm-selected
top-K).**
- `Rl_v46.py` `process_stock` (after the train/val/test split, using **`train_df`
  ONLY**): compute, for each column in `list_of_indicators`, a scalar importance =
  mutual information (`sklearn.feature_selection.mutual_info_regression`) between the
  scaled indicator at `t` and the next-day log-return `log(close_{t+1}/close_t)`
  restricted to the train slice. Keep the top `K=30` names; intersect with the
  columns actually present. Use that reduced list for env construction (train/val/
  test all use the SAME train-derived list).
- Env, reward, selector-metric-default, hyperparams unchanged. `K` is the only new
  constant (start 30; it is the sweep knob, not part of the first single-variable
  read — first read is fixed K=30 vs v18's 98).

**How to run.** `python run_panel.py v46` (whole panel; the readout is whether a
*principled* cut beats both v18-98-features AND avoids v26's degeneracy).

**Diagnostic / caveat.**
- **Leakage (critical, advisor):** the MI ranking MUST be computed on the train slice
  only; ranking on the full series leaks the val/test relationship into feature
  choice. Compute after the chronological split, from `train_df` alone. Also **drop
  the last train row's next-day-return label** so the label cannot peek into the first
  val bar. Then **freeze** the selected set and confirm the improvement on val —
  selecting features against the train label and reading improvement on that same
  period is circular and will flatter itself. Log the selected names per stock.
- **Degeneracy guard:** score with v37's exposure-adjusted-alpha selector and the
  ≥20-trade gate. If v46's "wins" are again low-trade cash-holds, the lever is dead
  (same failure class as v26) — report and stop, do not sweep K.
- MI is univariate (ignores redundancy); if K=30 helps, a follow-up could swap MI
  for a redundancy-aware selector (mRMR / gradient-boosted-tree importance) — but
  keep the first read single-variable (MI, K=30).
- **Distinct from v26 AND v27 (advisor):** v26 = arbitrary hand cut; v27 = learned
  *binary masking* during training; v46 = a fixed MI **ranking → static top-K
  selection** computed once on train (no learned/stochastic mask). If v46 wins where
  v26 failed, the lesson is "*which* features, not *how many*."

**Sources.** Adaptive/explainable feature selection for DRL stock trading,
https://www.sciencedirect.com/science/article/abs/pii/S1568494625018563 ;
conditional-mutual-information dynamic feature selection,
https://arxiv.org/pdf/2301.00557 .

## Rl_v47.py — stationary return-based feature representation

**Hypothesis.** Most of v18's 98 indicators are **price-LEVEL** quantities (moving
averages, Bollinger bands, price-scaled oscillators). Levels are non-stationary: the
train slice lives at one price regime and the test slice at another, so a critic that
fits train levels (EV 0.99) cannot transfer — a large part of the generalization gap
is **input non-stationarity**, not just capacity. The equity-ML literature is
near-unanimous that models should consume **stationary, scale-free** inputs
(multi-horizon returns, ratios, bounded oscillators), normalized causally. Replace
the level-based block with a compact **return/ratio** representation: multi-horizon
log-returns (1/5/10/21-day), ATR-as-fraction-of-price, distance-from-MA as a *ratio*
(`close/SMA − 1`), plus the already-bounded oscillators (RSI, MFI, Stoch). Single
variable vs v18 = **feature representation** (level → stationary-return), holding the
selector/reward/env fixed.

**Code change (single variable vs v18: `list_of_indicators` replaced by a
stationary set; add a small `add_return_features(df)` helper).**
- `Rl_v47.py`: add `add_return_features(df)` computing causal, trailing columns:
  `LOGRET_1/5/10/21` (`log(close/close.shift(h))`), `ATR_PCT = ATR_14/close`,
  `SMA_RATIO_{20,50} = close/SMA_h − 1`, `MOM_PCT_{10,21}` as returns; keep the
  bounded oscillators already in the list (RSI_14, MFI_14, STOCHk/d). Set
  `list_of_indicators` to exactly this stationary set (~15–20 names).
- All are trailing/causal (`.shift(h)` uses past only). Env/reward/selector/
  hyperparams identical to v18.

**How to run.** `python run_panel.py v47` (whole panel; the readout is whether
stationary inputs shrink the train-EV-vs-test gap).

**Diagnostic / caveat.**
- **Distinct from v26 and v46:** v26/v46 keep the SAME level-based TA (just fewer);
  v47 changes the *kind* of feature (level → return). This is the representation
  lever, orthogonal to count.
- Training EV should fall below 0.95–0.99 (levels no longer memorizable) and val
  curves should decay less after 100k if non-stationarity was the culprit.
- **Causality:** `.shift(h)` and trailing windows only; audit with the causality
  test. No center-aligned smoothing (that was the v6/v7 leak class).
- **The word "normalized" is the trap (advisor):** any z-score/vol-scaling statistic
  applied to these return features must be **fit on the train slice only** and applied
  forward, OR made **trailing/rolling** (a subtler cousin of the bfill bug already
  paid for — fitting on the full series leaks the test distribution backward). Safest
  is to converge the normalization toward v50's causal rolling mechanism so no fitted
  statistic crosses the split boundary. The raw log-returns/ratios themselves are
  already scale-free and can be fed with only v18's existing scaler.
- Degeneracy guard + ≥20-trade gate + v37 selector, as above.

**Sources.** Stationary-feature deep learning for price prediction,
https://arxiv.org/pdf/1810.09965 ; cross-sectional/return-based normalization is the
final step in top equity-ML features, https://arxiv.org/pdf/1910.01491 .

## Rl_v48.py — auxiliary next-return prediction head (self-supervised representation regularizer)

**Hypothesis.** The generalization gap is a **representation** problem: the LSTM
encoder is free to shape its latent space purely to fit training P&L (EV 0.99),
learning idiosyncratic features that don't transfer. Auxiliary-task /
self-predictive-representation work (SPR; "Loss is its own Reward") shows that adding
a **self-supervised prediction loss** that shares the encoder pulls the
representation toward *generic predictive structure*, improving sample efficiency and
out-of-sample generalization at ~zero inference cost — precisely the data-starved,
overfit regime here. Add ONE auxiliary head off the shared LSTM features that
predicts the **next-day log-return**, trained jointly with a small coefficient
`aux_coef` alongside the PPO loss. Single variable vs v18 = **+auxiliary loss**.

**Code change (single variable vs v18: subclass the policy to add an aux head +
loss).**
- `Rl_v48.py`: subclass `RecurrentActorCriticPolicy` (or wrap PPO's `train()`) to add
  a linear `aux_head(features) → r̂_{t+1}` and add `aux_coef * MSE(r̂_{t+1},
  logret_{t+1})` to the total loss. The regression target is the **realized next-day
  log-return**, available in the rollout buffer as `close_{t+1}/close_t` (causal — it
  is the *label* for state `t`, not an input, so no lookahead in the observation).
- `aux_coef = 0.1` (start); everything else — env, reward, features, selector,
  hyperparams — identical to v18.

**How to run.** `python run_panel.py v48` (whole panel; readout is EV-vs-test gap and
val-curve decay).

**Diagnostic / caveat.**
- **Distinct from the rejected L2/weight-regularization (advisor — say it plainly):**
  this is **representation-shaping via an auxiliary task, NOT parameter
  regularization**. The rejected reg shrank weight *norms* (std grew, returns
  regressed); an aux task ADDS supervised information to *shape* the representation —
  a different mechanism, well-supported for exactly this failure mode. Still, watch `clip_fraction`/`std` for the same collapse signature the
  rejected reg showed; if they collapse, `aux_coef` is too high — halve it once, and
  if it still collapses the lever is dead.
- **Implementation caution (flag for run routine):** this is the most invasive draft
  (custom policy subclass in sb3-contrib RecurrentPPO). The target must be read from
  the buffer as the label for the CURRENT step (`r_{t+1}` is realized after acting at
  `t`) and must NEVER enter the observation. Verify shapes on the 20k smoke run
  before a full panel.
- **EV caveat (advisor):** predicting next-day return *is itself* the ceiling problem,
  so the aux target is near-unlearnable — the head may inject mostly noise gradient
  rather than a useful shared representation. Worth **one** run; do NOT over-invest or
  sweep `aux_coef` widely. If the multi-step self-predictive-latent target (SPR-style:
  predict the next *latent state*, not the raw return) is easy to bolt on, it is the
  stronger version and sidesteps the "return is unpredictable" objection.
- Degeneracy guard + ≥20-trade gate + v37 selector.

**Sources.** Data-Efficient RL with Self-Predictive Representations (SPR),
https://arxiv.org/pdf/2007.05929 ; Loss is its own Reward: Self-Supervision for RL,
https://arxiv.org/pdf/1612.07307 .

## Rl_v49.py — momentum behavior-cloning warm-start

**Hypothesis.** Two v18 pathologies share a root cause — a poor initialization.
(a) Degenerate cash-hold checkpoints (HDFCBANK) arise when the random-init policy
never discovers the "be invested" region early. (b) v18 policies "make money but lose
to bull-trending B&H" because they never acquire a trend-following prior. Both are
fixed by **warm-starting** the policy from a simple, causal trend rule via behavior
cloning (BC), then letting PPO fine-tune — the standard hybrid imitation→RL recipe
for sparse/long-horizon control and sample efficiency. Single variable vs v18 =
**policy weights are BC-pretrained** on a trend rule before PPO's 200k steps (PPO
budget, env, reward all unchanged).

**Code change (single variable vs v18: add a BC pretrain stage before `.learn()`).**
- `Rl_v49.py` in `train_ppo_model`, BEFORE `.learn()`: generate expert actions from a
  **causal SMA rule** on the train slice (target exposure = full-in when
  `close > SMA_50` else flat; map to the env's action via the same share logic v18
  uses), roll it through the train env to collect `(obs, expert_action)` pairs, and
  run a few hundred supervised gradient steps minimizing
  `MSE(policy_action(obs), expert_action)` on the actor (BC). Then call `.learn()` as
  in v18.
- The SMA rule is causal (SMA_50 is trailing). Env/reward/features/selector/
  hyperparams identical; only the initial weights differ.

**How to run.** `python run_panel.py v49` (whole panel; target HDFCBANK — the
degenerate-init failure — and bull-window stocks that beat v18's absolute return but
lose to B&H).

**Diagnostic / caveat.**
- Success = fewer degenerate/cash-hold checkpoints AND higher exposure-adjusted alpha
  vs v18, with ≥20 trades. If BC merely reproduces the SMA baseline (which
  `baselines.py` shows PPO already ~ties), the warm-start didn't help PPO escape —
  report as neutral.
- **Keep it a warm-START, not a constraint:** do NOT add a persistent KL-to-prior
  penalty in the first read — a standing KL anchor is functionally the rejected
  "regularization toward a fixed policy" and risks freezing the SMA rule in. BC
  affects only the initial weights; PPO is then free. (A mild, decaying KL anchor is
  a possible v49-followup ONLY if pure warm-start washes out too fast.)
- **Leakage:** the BC target uses trailing SMA only; assert no future bar enters the
  expert action.
- **Priority (advisor, honest):** this is the LOWEST-ranked of the five — it targets
  *optimization / anti-degeneracy*, not the ceiling or the gap, and its SMA prior only
  coin-flips vs PPO in `baselines.py`, so it cannot lift the ceiling above that rule.
  It also brushes the single-variable discipline (BC pretrain is one mechanism; keep
  any KL anchor OUT of the first read as noted). Run it only when the objective is
  explicitly "guarantee an active ≥20-trade policy / kill the HDFCBANK cash-hold,"
  not when the objective is alpha. Deprioritize behind v50/v51/v47.

**Sources.** Hybrid imitation→RL (warm-start then fine-tune),
https://arxiv.org/pdf/2412.07057 ; BC-augmented sample-efficient imitation,
https://arxiv.org/pdf/2001.07798 .

## Rl_v50.py — causal rolling normalization of observations (adaptive, bounded inputs)

**Hypothesis.** v18 fits a **single static** `RobustScaler` on the train slice and
applies it forever. When the test slice drifts to a new regime, those fixed
median/IQR constants are stale, so inputs land off-distribution — a direct
contributor to the train→test gap that is separate from *which* features are used
(v46/v47). The equity-ML fix is **causal rolling normalization**: normalize each
feature by its own *trailing-window* statistics (e.g. rolling z over the past ~252
bars, or trailing percentile rank), so inputs stay bounded and regime-adaptive
across the whole timeline. Single variable vs v18 = **the scaling scheme** (static
train-fit RobustScaler → causal rolling z/rank), features and everything else held
fixed. **Advisor ranks this the #1 gap-closer** (cheapest, safest, hits the likely
root cause, *causal by construction* — a trailing rank/z needs no fitted statistic,
so smallest leakage surface of the five). Prefer the trailing **percentile-rank**
form: outlier-proof and the most regime-robust.

**Code change (single variable vs v18: replace the static scaler in
`prepare_data_for_finrl`).**
- `Rl_v50.py`: in `prepare_data_for_finrl`, replace the RobustScaler transform of the
  indicator/OHLC block with a **causal rolling transform**: for each feature,
  `z_t = (x_t − rollmean_{t-1..t-W}) / rollstd_{t-1..t-W}` with `W=252`, computed on
  the FULL, CONTINUOUS series but using ONLY trailing values (windows shifted by 1 so
  `x_t` is excluded from its own stats). Clip to `[−5, 5]`. The trailing
  **percentile-rank** variant (`x_t`'s rank within its trailing `W`-window, mapped to
  `[−1,1]`) is the preferred, outlier-proof form. No fit/transform split needed — the
  window is self-contained and causal.
- **Do NOT reset the rolling window at the train/val or val/test boundary (advisor).**
  Compute on the continuous series so early val/test rows legitimately pull trailing
  *past* (train) rows into their window; resetting per split starves those rows and
  silently changes behavior. Trailing-rolling is causal by construction — the whole
  advantage is that nothing is "fit on train," so do not reintroduce a global fit.
- Env, reward, features, selector, hyperparams identical to v18.

**How to run.** `python run_panel.py v50` (whole panel; target stocks whose test
window is a different regime from train — ADANIPORTS, TATAMOTORS).

**Diagnostic / caveat.**
- **Distinct from v47:** v47 changes WHICH features (level→return); v50 changes HOW
  the existing features are scaled (static→rolling). Orthogonal; both attack
  non-stationarity from different sides and could later stack.
- **Leakage (critical):** the rolling window MUST be strictly trailing (shift by 1 so
  the current bar is excluded). A centered or inclusive window re-introduces
  lookahead. Audit with `test_indicator_causality.py`-style prefix equality: the
  transformed value at `t` must not change when future rows are appended. The first
  `W` bars have no full window — either warm up (skip) or expanding-window until `W`,
  and trim consistently with v18's non-null trim. (Advisor 2026-09-04 confirmed v50 is
  leak-clean: a trailing `W`=252 percentile-rank is causal per-point, so computing it
  on the unsplit continuous series introduces NO leak — only the first ~252 rows are
  warmup/undefined.)
- **Distinct from VecNormalize (advisor — pre-empt the "dup" objection):** v18's
  `VecNormalize(norm_obs)` keeps a **global running** mean/std over ALL steps seen —
  not windowed, not rank-based, so it is blind to regime shift and to outliers. v50 is
  **rolling + rank** (regime-robust, bounded). They are different mechanisms; keep
  VecNormalize on for a clean single-variable diff, but note the interaction in the
  readout (rolling-normalized inputs are already ~unit-scale, so VecNormalize is
  roughly a no-op on them).
- Degeneracy guard + ≥20-trade gate + v37 selector.

**Sources.** Per-stock trailing z-normalization to handle non-stationarity,
https://arxiv.org/pdf/1810.09965 ; cross-sectional/rolling normalization as standard
practice, https://arxiv.org/pdf/1910.01491 .


---

# Variant v51 — the missing CEILING lever (2026-09-04, auto/research advisor)

## Rl_v51.py — cross-sectional relative-strength features (this stock vs the NIFTY panel)

**Why this is different from the five above.** v46–v50 are *generalization-gap
closers* — they reshape the SAME per-stock indicator set and cannot add alpha it
doesn't contain. v51 is one of the few **ceiling levers**: it feeds the policy
**information it currently cannot see** — where this stock stands *relative to the
other 49*. Cross-sectional (relative-strength) momentum is among the most robust,
widely-replicated equity anomalies, and it is **distinct from everything queued**:
v30/v40 add a single market-regime bit, v44 adds an exogenous market vector, v24/v45
pool the data — but NONE give a single-stock policy its **cross-sectional context**.
The advisor ranked this ABOVE v46/v48 for expected value because it can *lift* the
ceiling, not merely close the gap. It is buildable from data ALREADY in the repo (the
50 per-stock CSVs) — unlike v40/v44 it needs no external index/VIX file.

**Hypothesis.** A stock outperforming its universe (high cross-sectional momentum
rank) tends to keep outperforming over daily-to-monthly horizons; a stock at the
bottom of the cross-section is a different regime than the same stock's *absolute*
indicators reveal. Adding a few **panel-relative** columns lets the policy condition
entries/exits on relative strength, a genuine directional signal (not a risk-off
gate, so it will not manufacture a cash-hold).

**Code change (single variable vs v18: +K cross-sectional feature columns).**
- New precompute step (once, cached): across the full NIFTY50 panel, on each date `t`
  compute, per stock, its **cross-sectional rank ∈ [0,1]** of:
  (i) trailing 21-day return (relative momentum), (ii) trailing 63-day return,
  (iii) distance from its own 200-DMA (`close/SMA200 − 1`), and (iv) 21-day realized
  vol (relative vol rank). Ranks are computed **across the universe on the same date**
  using only that date's trailing values — strictly causal per date.
- In `process_stock`, date-align that stock's four relative-strength columns to its
  frame (present identically in train/val/test) and append their names to
  `list_of_indicators` (observation 101 → 105).
- Env, reward, selector, hyperparams unchanged.

**How to run.** `python run_panel.py v51` (whole panel; relative-strength should help
most on trending leaders/laggards — TATAMOTORS, ADANIENT, RELIANCE).

**Diagnostic / caveat.**
- **Leakage — CONSTITUENT LOOKAHEAD / survivorship (advisor: "the one to nail"):**
  ranking against *today's* NIFTY50 membership leaks future index composition into
  every historical rank — a stock only in the index because it survived to 2026 must
  NOT appear in a 2015 cross-section. The panel MUST be **point-in-time**: on each
  date, rank only the names that (a) were index constituents as of that date and
  (b) have a real (non-ffilled-past-listing) bar that date; drop the rest from that
  date's cross-section. If point-in-time membership is unavailable, restrict to the
  common-listed subset and LABEL the result survivorship-biased — do not present it as
  clean. Log the exact per-date membership used.
- **Leakage — temporal (critical):** each date's rank uses only trailing per-stock
  values (returns via `.shift`, trailing vol, trailing 200-DMA), never the current
  bar's future. Audit with the causality test: a stock's rank column at `t` must be
  unchanged when future rows are appended (each date's cross-section is independent, so
  other stocks' future is excluded by construction — ranks are per-date, trailing-only).
- **Distinct from a cash-hold:** relative strength is directional (which stock to be
  long), not an inaction gate; combined with the ≥20-trade gate + v37 exposure-alpha
  selector, a degenerate cash-hold cannot score. This is the intended anti-artifact
  property that makes it a legitimate ceiling challenger.
- **Stackable:** cross-sectional features are naturally strongest UNDER v24/v45 pooled
  training (one policy sees the whole panel), so a strong single-stock v51 read is the
  gate to a pooled v51 follow-up. Keep the first read single-variable vs v18.

**Sources.** Cross-sectional relative-strength / robust equity anomalies and
cross-sectional standardization, https://arxiv.org/pdf/1910.01491 ; cross-sectional
rank formation for stock prediction, https://arxiv.org/pdf/2606.08930 ;
machine-learning cross-sectional return prediction,
https://link.springer.com/article/10.1007/s00291-022-00693-w .

---

## DESIGN ONLY — v52: meta-labeling act/don't-act filter (López de Prado)

**Idea (advisor runner-up).** Keep v18's policy as the **primary** model deciding
*direction/size*, and train a lightweight **secondary** classifier (meta-label) that
decides *whether to act* on each primary signal — the López de Prado meta-labeling
pattern, which improves precision/F1 and risk-adjusted return by suppressing
low-confidence trades. **DESIGN ONLY / not a clean single-variable fork:** it is a
two-component system (primary policy + secondary filter) and would need its own
train/val protocol for the secondary model, so it violates the single-variable
discipline the project enforces (the v10/v11 two-changes-at-once trap). Hold until at
least one gap-closer (v50) and the ceiling lever (v51) have a trustworthy read under
v37's honest selector; then meta-labeling is the natural way to convert a
higher-precision primary into fewer, better trades. Source: López de Prado, *Advances
in Financial Machine Learning*, Ch. 3 (meta-labeling).

---

# Variants v53–v54 — data-efficiency & multi-timeframe forks (2026-09-04, auto/research)

Two more single-variable forks continuing the features/data-starvation attack. Both must
clear the same pass/fail preconditions as v46–v51 (≥20-trade active-policy gate, v37
exposure-adjusted selector, causality audit for any feature change).

## Rl_v53.py — transfer learning: pooled pretrain → per-stock fine-tune

**Anchor.** Fork of **v18** whose single variable is the policy's INITIALIZATION: instead
of random init, warm-start each per-stock PPO run from a **pooled cross-stock pretrained
checkpoint** (the v24 pooled model), then fine-tune on the target stock's train slice with
the v18 recipe unchanged. Gated: needs a v24 pooled checkpoint to exist first.

**Hypothesis.** v43's framing named the root cause as **data starvation** — one ~1750-bar
train path cannot support a 128-hidden LSTM, so it memorizes (EV 0.99). The direct,
literature-standard fix that does NOT touch capacity or per-stock compute is **transfer
learning**: pretrain a shared policy on the whole panel (~50× data → a representation of
"overarching market signals rather than a single price series"), then **fine-tune per
stock** so the target stock still gets a specialized policy but starts from a
data-rich prior rather than noise. Multi-asset RL work shows a pooled-pretrained policy
transfers to individual assets "with refinement." This keeps v18's single-stock test
protocol (unlike v24/v45, which also *evaluate* pooled) — the ONLY change vs v18 is the
initial weights.

**Code change (single variable vs v18: random init → load pooled-pretrained weights).**
- Prerequisite: a saved v24 pooled model (`models_v24/pooled_ppo.zip` + its VecNormalize).
- `Rl_v53.py` `train_ppo_model`: build the RecurrentPPO model as in v18, then
  `model.set_parameters(pooled_checkpoint)` (matching the shared MlpLstmPolicy arch;
  observation must be the v18 per-stock layout — so the pooled model must have been trained
  on the SAME per-stock observation spec, i.e. the intersection-of-indicators shape). Then
  `.learn(200k)` and the v18 ValidationCallback exactly as before.
- Everything else (env, reward, features, selector, hyperparams, 200k budget) identical to
  v18. Only the starting weights differ.

**How to run.** `python run_panel.py v53` (after a v24 pooled checkpoint exists; the readout
is whether a data-rich prior lowers the train-EV-vs-test gap and lifts exposure-adjusted
alpha vs v18 random-init).

**Diagnostic / caveat.**
- **Distinct from v24/v45:** v24 trains AND evaluates one pooled policy; v45 conditions the
  pooled policy on stock identity; v53 uses the pooled policy ONLY as an initialization for
  a per-stock fine-tune (per-stock eval, per-stock final policy). Different mechanism.
- **Obs-shape gotcha (flag):** the pooled pretrain and the per-stock fine-tune must share
  the observation spec, or `set_parameters` will shape-mismatch. Pretrain v24 on the
  per-stock intersection-of-indicators layout, or add a projection — keep the first read
  simple by matching shapes.
- **Fine-tune LR (keep single-variable):** use v18's `3e-4` for the first read so the only
  variable is initialization. A lower fine-tune LR is a *separate* follow-up, not this fork.
- Should reduce degenerate cash-holds (the prior already "knows how to be invested") — check
  the ≥20-trade gate and the EV-vs-test gap.

**Sources.** Multi-asset RL transfer with refinement (MADDQN pretrain→transfer),
https://arxiv.org/pdf/2505.03949 ; multi-stock shared-policy learns overarching signals,
https://arxiv.org/pdf/2506.04358 .

## Rl_v54.py — multi-timeframe (weekly) context features

**Hypothesis.** v18 feeds only DAILY indicators; the policy must infer longer-horizon trend
from the daily LSTM sequence alone, which the generalization diagnostics suggest it does
poorly. Multi-timeframe feature engineering — appending **higher-timeframe (weekly)**
indicators alongside daily — is a standard, cheap way to surface low-frequency trend/regime
structure the model underweights, and needs no external data (resample the same OHLCV). Add
a small set of **weekly-resampled** columns (e.g. weekly RSI_14, weekly return, weekly
`close/SMA20_weekly − 1`), forward-aligned to daily bars using ONLY completed weeks. Single
variable vs v18 = +K weekly context columns (observation 101 → 101+K).

**Code change (single variable vs v18: +weekly-resampled feature columns).**
- `Rl_v54.py`: add `add_weekly_features(df)` that resamples OHLCV to weekly (`W-FRI`),
  computes a few weekly indicators, and **merges each daily bar with the most recently
  COMPLETED week's** weekly values (shift so the current, still-forming week is excluded —
  a daily bar on Wednesday sees last Friday's completed weekly values, never this week's).
  Append the weekly column names to `list_of_indicators`.
- Env, reward, selector, hyperparams unchanged.

**How to run.** `python run_panel.py v54` (whole panel; weekly trend context should help most
on strongly-trending test windows — TATAMOTORS, RELIANCE, ADANIENT).

**Diagnostic / caveat.**
- **Look-ahead bias is THE trap here (flag — literature-documented):** the well-known
  multi-timeframe bug is aligning a daily bar to the weekly bar that CONTAINS it (which
  isn't complete until week's end). The weekly value for any day must come from the last
  **fully closed** week (`.shift(1)` on the weekly series before the daily merge). Audit
  with `test_indicator_causality.py`: the weekly columns at date `t` must be unchanged when
  future rows are appended.
- **Distinct from v51 (cross-sectional) and v47 (return representation):** v54 adds a
  *higher-timeframe view of the SAME stock*, not a cross-asset rank or a level→return swap.
- Honest caveat: weekly features are a **coarse-graining of existing daily data**, not truly
  exogenous information — so expect a gap-closing/robustness effect, not a ceiling jump.
- Degeneracy guard + ≥20-trade gate + v37 selector.

**Sources.** Multi-timeframe feature engineering (price-level-agnostic),
https://doi.org/10.3390/forecast8030040 ; multi-timeframe interaction learning in DRL
trading (and its look-ahead-bias correction),
https://www.sciencedirect.com/science/article/abs/pii/S0957417422013082 .

---

# Variants v55–v60 — capacity, seasonality, vol-scaled reward & exogenous-vol forks (2026-09-04, auto/research)

Six single-variable forks from the **v18** production champion (v26 stays invalidated).
v55 promotes the ONE reproducible empirical lever (capacity 128→64, positive on BOTH proxy
panels) to a clean production fork; v56/v57 are a GATED diagnostic decomposition of it;
v58/v60 are exogenous-information ceiling levers; v59 is a new (non-DSR) reward. All must
clear the standing preconditions — ≥20-trade active-policy gate + v37 exposure-adjusted
selector; any input/reward change audited by `test_indicator_causality.py`. Two independent
advisor passes (boundary-a pre-write ranking; boundary-b pre-PR) shaped this batch; the
advisor's changes are folded in inline (v58 trimmed, v56/v57 deferred, v60 added).

**Honesty note on the capacity lever (read before v55–v57).** The RL-generalization
literature is *mixed* on "smaller network = better generalization": several works find
larger nets generalize BETTER and name the real culprit **observational overfitting** — the
policy latching onto spurious features in a rich observation — fixed input-side (feature
masking v27, causal rolling-norm v50, feature selection v46, exogenous features) rather than
by raw shrinkage (Song et al., https://arxiv.org/pdf/1912.02975 ). We propose v55 anyway
because on THIS project 128→64 is the only lever empirically positive on both proxy panels,
but we frame it as a *gap-closer*, not a ceiling lift, and pair it with the observational-
overfitting reading (see v56/v57).

**Meta-risk (advisor, above any single variant).** ~15 tweaks × 2 noisy 3-stock panels is a
garden-of-forking-paths engine; `significance.py` already reports 0/49 survive FDR with no
correction for the ~20+ versions tried. The 128→64 "win" could be selection on noise. The
highest-value ACTION is not another variant but hardening the accept gate: a persistent
**trial registry** (every config ever screened, so the Deflated-Sharpe deflation uses the
true trial count) feeding the existing Deflated-Sharpe gate (see the "METHODOLOGY —
Deflated-Sharpe challenger-acceptance gate" note above) on the FULL panel before any lever is
declared real. v55 is the right first spend precisely because it is the cheapest test of
whether a proxy winner survives contact with the production panel.

## Rl_v55.py — capacity reduction (lstm_hidden_size + net_arch 128→64), full features  [DRAFTED, UNRUN]

**Anchor.** Fork of **v18**. Single variable: `policy_kwargs.lstm_hidden_size` 128→64 and
`policy_kwargs.net_arch` [128]→[64]. Everything else byte-identical to v18 — all 106 features
KEPT (the key distinction from the invalidated v26, which cut features).

**Hypothesis.** The generalization diagnostics (critic EV 0.95–0.99 on train, poor test; val
curves peak ~100k then decay) are the signature of too much capacity for ~2500 daily bars.
Halving the LSTM width and the post-LSTM MLP head is the one anti-overfit move positive on
BOTH proxy panels (ITC 128→64 = +12.2pp vs its baseline; TATAMOTORS = +9.0pp), while 128→32
was catastrophic (RELIANCE −237pp) — 64 is the screened sweet spot. This is exactly the
board's NEXT-ACTION #5: "an architectural change that improves generalization WITHOUT
reducing features."

**Code change (single variable vs v18).** `lstm_hidden_size: 128 → 64`; `net_arch: [128] →
[64]`. **Drafted as `Rl_v55.py` (UNRUN):** 2 value edits + a banner vs v18, `ast.parse`
clean; run via `run_panel.py` (no registration needed).

**How to run.** `python run_panel.py v55` (full 10-stock panel; never run frozen files).

**Diagnostic / caveat.**
- Primary read: does train critic EV drop BELOW v18's 0.95–0.99 AND do val curves stop
  decaying after their peak? If EV still pegs at 0.99 the overfit is time-of-episode
  structure, not width (points to v27/v50, not more shrinkage).
- **Distinct from v26** (features untouched) **and from v36** (v36 is a two-variable
  n_steps=256 + lstm=64 STACK anchored to the invalidated v26 — v55 is the clean
  single-variable v18 fork the frontier lacked).
- Must clear the ≥20-trade gate; score with the v37 exposure-adjusted-alpha selector so a
  degenerate cash-hold cannot win. Confidence: HIGHEST of this batch (most-supported lever);
  main risk is it only closes the gap to a still-low ceiling.

**Sources.** PPO Dash (capacity/regularization vs RL generalization),
https://arxiv.org/abs/1907.06704 ; observational overfitting (larger nets can generalize
better; culprit = spurious obs features), https://arxiv.org/pdf/1912.02975 .

## DESIGN ONLY — v56 / v57: capacity-locus decomposition (GATED behind v55 winning the full panel)

**Why gated, not two live proposals (advisor).** 128→64 won as a *joint* change of the LSTM
core and the post-LSTM head. Decomposing it BEFORE v55 confirms on the production panel risks
finding that neither half reproduces (an interaction effect) and burning two proposal slots
on a non-result. So: run v55 first; **only if v55 wins the full panel**, run the matched pair.
- **v56** — `net_arch [128]→[64]` only (LSTM stays 128). Tests whether the readout MLP is the
  overfit locus (if so, the expensive LSTM width can stay).
- **v57** — `lstm_hidden_size 128→64` only (head stays [128]). If halving only the LSTM (which
  ingests the 101-dim observation each step) recovers most of v55's gain, the overfit is
  *observational* → implicates the input-side levers (v27/v50/v46/v58/v60) as the true fix.
- **Read as a set:** compare exposure-adjusted alpha of {v18, v55, v56, v57} on one panel.
  v56≈v55 ⇒ head locus; v57≈v55 ⇒ LSTM/observation locus; v56≈v57≈½v55 ⇒ additive. Each is a
  one-integer change (cheapest possible experiment) but diagnostic, not itself a challenger —
  the production challenger is whichever of v55/v56/v57 maximizes exposure-adjusted alpha at
  ≥20 trades. Sources: same as v55.

## Rl_v58.py — calendar / seasonality context features (exogenous, look-ahead-safe)

**Anchor.** Fork of **v18**. Single variable: +K deterministic calendar columns appended to
the observation. A ceiling lever (adds information the price series does not cleanly encode).

**Hypothesis.** Indian equities show documented calendar seasonality — turn-of-month and
day-of-week effects on NIFTY — that v18's observation cannot see; the LSTM would have to
reconstruct the calendar from bar spacing, which it cannot. Feeding the calendar directly is
cheap and strictly causal (dates are known in advance — zero look-ahead risk). It is a
context signal, not a risk-off gate, so it will not manufacture a cash-hold.

**Code change (single variable vs v18: +calendar columns) — TRIMMED per advisor.**
- `Rl_v58.py`: `add_calendar_features(df)` from `df['datetime']`: (i) `sin`/`cos` of
  day-of-week (2 cols, cyclic), (ii) `turn_of_month` flag (last 1 + first 3 trading days of a
  month = 1), (iii) `days_to_month_end` normalized to [0,1] (coarse monthly-expiry proxy).
  K≈4. Append names to `list_of_indicators`.
- **DROPPED per advisor:** month-of-year one-hots. ~7 train-years ⇒ ~7 samples per monthly
  category — overfit bait, especially while v55 is simultaneously *shrinking* capacity. The
  month effect, if real, must be earned by the higher-sample features above, not memorized
  from 7 examples.
- Env, reward, selector, hyperparams unchanged.

**How to run.** `python run_panel.py v58` (seasonality is stock-agnostic → read the panel
mean, not one stock).

**Diagnostic / caveat.**
- **Causality:** calendar values depend ONLY on the date → trivially pass
  `test_indicator_causality.py` (invariant to appended future rows). Still run the audit.
- Use cyclic sin/cos, NOT raw integer day-of-week — an ordinal wrap injects a false
  discontinuity RobustScaler cannot fix.
- Honest caveat: calendar effects are **weak and partly arbitraged**; expect a modest, broad
  lift at best, likely strongest as a *conditioning* feature that helps other signals. Even
  trimmed it adds ~4 dims (mild tension with the capacity finding). Cheapest true ceiling
  lever (no external data, no cross-panel precompute) — worth one clean read, but ranked
  BELOW v60 (VIX) as an information lever. ≥20-trade gate + v37 selector.

**Sources.** Month-of-the-year effect on NIFTY50 / Bank NIFTY (January anomaly),
https://pmc.ncbi.nlm.nih.gov/articles/PMC8742668/ ; month-of-the-year effect, Indian market,
https://link.springer.com/article/10.1007/s10690-021-09356-2 ; calendar effects &
weak-form efficiency (turn-of-month, day-of-week),
https://ijmec.org.in/index.php/ijmec/article/view/144 .

## Rl_v60.py — India VIX (index implied volatility) as an exogenous observation feature — TOP CEILING LEVER of this batch

**Anchor.** Fork of **v18**. Single variable: append the India VIX level (and its 1-day
change / trailing z-score) to every stock's observation. **Advisor's top missing ceiling
lever** — genuinely exogenous, forward-looking risk information that is NOT derivable from a
single stock's own OHLCV (unlike the price-based regime bits v30/v40/v44).

**Hypothesis.** India VIX is an option-implied, forward-looking estimate of near-term NIFTY
volatility; the literature finds it an unbiased/predominant predictor of future realized
volatility and shows a negative, asymmetric short-term relationship with NIFTY returns (risk
spikes cluster with drawdowns). A per-stock policy that can SEE the market's forward risk
gauge can de-risk into vol spikes and re-engage as vol mean-reverts — information no amount of
capacity tuning on the stock's own bars can manufacture. This raises the ceiling; it is not a
gap-closer.

**Code change (single variable vs v18: +VIX columns). GATED ON DATA.**
- Prerequisite: a daily India VIX series (NSE publishes India VIX since ~2008–09). Add
  `data/INDIAVIX_daily.csv` (`datetime, close`). If unavailable, this fork is BLOCKED — log
  it to `NEEDS_HUMAN.md` (a data-sourcing request) and DO NOT fake it with a stock-derived
  proxy (that would collapse it into v30/v40, no new information).
- `Rl_v60.py`: `add_index_vol_features(df)` left-joins VIX on `datetime` and appends
  (i) VIX level, (ii) 1-day VIX change, (iii) trailing z-score of VIX (causal rolling mean/std,
  window 63). Forward-fill only past gaps (never bfill across the split). Append names to
  `list_of_indicators`. Same value on every stock's frame for a given date.
- Env, reward, selector, hyperparams unchanged.

**How to run.** `python run_panel.py v60` (after `INDIAVIX_daily.csv` exists; whole panel —
VIX is market-wide, read the panel mean).

**Diagnostic / caveat.**
- **Causality (critical):** VIX(t) is the *close* of the index-implied vol on day t — same
  timing as the stock's own close, so aligning VIX(t) to bar t is causal, but the trailing
  z-score MUST use rolling (never centered) stats; `.shift`-audit with
  `test_indicator_causality.py` (VIX columns at t invariant to appended future rows).
- **Date-alignment / holidays:** VIX and the stock share the NSE calendar, but verify no
  extra VIX trading days leak in; inner-join on the stock's dates.
- **Distinct from v30/v40/v44:** those derive a regime bit/vector from PRICE (the index vs its
  200-DMA, etc.) — backward-looking and stock-adjacent. VIX is option-IMPLIED and
  forward-looking: strictly more information. Outranks v58 as an information lever.
- Honest caveat: adds only ~3 dims (mild capacity tension) and its edge is concentrated around
  vol regime changes; on calm test windows expect little. Value is downside protection /
  drawdown reduction as much as return — read max-DD and Sharpe, not just outperformance.
  ≥20-trade gate + v37 selector.

**Sources.** India VIX is an unbiased/predominant predictor of future NIFTY realized
volatility, https://link.springer.com/article/10.1007/s40196-013-0025-4 ; forecasting power of
India VIX, https://www.researchgate.net/publication/305990898_The_Forecasting_Power_of_the_Volatility_Index_Evidence_from_the_Indian_Stock_Market ;
negative-asymmetric VIX–NIFTY return relationship & ML on India VIX,
https://www.mdpi.com/1911-8074/15/12/552 .

## Rl_v59.py — volatility-scaled per-step reward (floored, NOT differential-Sharpe) — LOW PRIORITY

**Anchor.** Fork of **v18**. Single variable: the PRIMARY reward term. v18 uses
`clip(log(eq_t/eq_{t-1}) * 100, -10, 10)` minus the v12 DD penalty. v59 divides the log
return by a **floored trailing realized-vol** estimate before clipping; DD penalty preserved.

**Hypothesis.** A raw per-bar return reward pays the agent the same for a +1% move in a calm
regime and in a turbulent one, so the policy has no incentive to size/time around volatility —
a plausible driver of the whipsaw/over-trading losses (INFY). Volatility scaling (Zhang,
Zohren & Roberts, arXiv:1911.10107) makes the reward risk-adjusted per step (scales rewards up
in low-vol, down in high-vol) and is shown there to let a DRL trader "follow large market
trends without changing positions and scale down through consolidation" — the trend-following
behavior v18 lacks.

**Materially different from the REJECTED DSR (the whole point).** v10's DSR used the
Moody–Saffell recursive differential Sharpe with a `(B − A²)^(3/2)` denominator that detonates
in low-vol windows (VL→85, clip_fraction→1e-4). v59 has NO such term:
`reward = clip( (log(eq_t/eq_{t-1}) / max(σ_t, σ_floor)) * k, -10, 10 )`, where `σ_t` is a
simple trailing stdev of the last N(=20) equity log-returns and `σ_floor` HARD-BOUNDS the
denominator. No ^1.5 power, no recursive B−A² — bounded by construction. This is standard
vol-target scaling, not the differential Sharpe.

**Code change (single variable vs v18: primary reward only).**
- `IntegerTradingEnv`: keep a rolling buffer of the last N equity log-returns; replace
  `primary = clip(logret*100,…)` with
  `primary = clip(logret / max(rolling_std(buf), σ_floor) * k, -10, 10)`. Calibrate `k` so
  mean |primary| ≈ v18's on ONE stock (keep it a *shape* change, not a *scale* change). Reset
  the buffer in `reset()`. v12 DD penalty still subtracted, unchanged.

**How to run.**
`python -c "from Rl_v59 import process_stock, NIFTY50_PATH; import os; process_stock(os.path.join(NIFTY50_PATH,'INFY_daily.csv'))"`
then `python run_panel.py v59`. Priority: INFY (over-trading), TATAMOTORS/RELIANCE (trend).

**Diagnostic / caveat (advisor flags).**
- **Not truly clean single-variable — it STACKS on v18's log-return+DD reward** (re-weights
  the existing primary rather than replacing the whole reward). Treat the `k`-calibration as
  part of the one change, not a second knob.
- **It is a GAP lever, not a ceiling lever** — it re-weights credit assignment, adds no new
  information → bounded upside under this batch's own framing. Hence LOW PRIORITY behind the
  information levers (v60, v58) and the confident gap lever (v55).
- **DSR-failure watch:** monitor `value_loss` / `clip_fraction`; if VL blows up or
  clip_fraction collapses toward 1e-3, `σ_floor` is too small — raise it. `σ_t` MUST be causal
  trailing (never centered).
- Honest flag: reward-shaping has a poor track record here (v10/v11 lost). It earns a slot
  ONLY because the mechanism is provably distinct from DSR and is the literature-standard
  trend-following reward. If it collapses like v10, discard and do NOT retry vol-based rewards.

**Sources.** Zhang, Zohren & Roberts, "Deep Reinforcement Learning for Trading" (volatility
scaling in the reward for trend-following), https://arxiv.org/abs/1911.10107 ;
https://arxiv.org/pdf/1911.10107 .

---

# Variants v61–v65 (2026-09-05) — forks from the v18 champion

Anchored to the **v18 production champion** (not v26, which is an invalidated cash-hold
artifact). Each is ONE variable vs v18. Two independent advisor passes this session
(boundary-a pre-write ranking, boundary-b pre-PR) drove selection: **priority order
v61 > v62 > v63 > v64**, with **v65 a separate measurement-integrity prerequisite** (it
changes the yardstick, not the model). Framing carried over from the v46–v60 batch:
a *gap-closer* narrows the train→test generalization gap (critic EV 0.95–0.99 on train,
poor test) but cannot raise the achievable ceiling; a *ceiling lever* adds genuinely new
information. The board's core problem is BOTH a generalization gap AND a low signal
ceiling, so the batch deliberately mixes one ceiling lever (v61) with three gap-closers
(v62–v64) plus a yardstick fix (v65).

**Two standing pointers from the boundary-b advisor** (fold into next session's run order):
(1) **v65 (walk-forward multi-fold TEST eval) is plausibly the single highest-leverage item
here — above v61.** The project's "0/49 survive FDR / PPO ≈ coin-flip vs SMA" verdicts all rest
on ONE 15% window per stock; the multi-fold alpha *distribution* is what tells you whether ANY
edge exists before more model forks are worth running. (2) For a *per-stock, information-dense*
ceiling lever, the already-designed **v51 (cross-sectional relative-strength RANK of this stock
within the 50-name panel, per date)** is stronger than v61's single slow breadth scalar — v61
is regime-gating, v51 is a dense per-stock signal. They share the same cross-panel precompute
and the same survivorship caveat, so **draft v51 and v61 together**; run v51 as the primary
ceiling lever, v61 as the market-wide complement.

Explicitly **killed this session** (do NOT propose): (1) `VecNormalize(norm_reward=True)` —
v18's reward is already log-scaled and clipped to [−10,10]; a moving-std divisor fights the
fixed v12 DD-penalty scale for ~zero upside. (2) snapshot ensemble via cyclic LR — snapshots
from ONE overfitting run are highly correlated and share the same overfit (and half would be
drawn from the post-100k decay regime), so it is dominated by v22's independent seeds and
v41's SWA. (3) entropy-coefficient decay from step 0 — the val callback already early-stops
the late-training decay this targets, and the literature finds naive decay-from-start can
*underperform* the constant baseline (stabilize-then-decay is what wins). Deprioritized, not
written.

## Rl_v61.py — market-breadth exogenous feature (% of the NIFTY panel above its own 50-DMA) — TOP CEILING LEVER of this batch

**Anchor.** Fork of **v18**. Single variable: append a small market-internal breadth vector
(same value on every stock's frame for a given date) to the observation. The advisor's #1
pick: the only candidate in this batch that adds genuinely NEW information, and it is
buildable entirely from the 50 in-repo CSVs (no external data, no `NEEDS_HUMAN` gate — unlike
v60's India VIX).

**Hypothesis.** *Market breadth* — the fraction of the NIFTY50 universe trading above its own
50-day moving average — is a classic regime signal with documented forward-return content:
broad participation (>~70% above their MA) marks durable uptrends and washouts (<~20%) precede
durable lows, and the informative case is the *divergence* (index up while breadth falls =
narrowing, late-cycle rally). This is information a single stock's own OHLCV cannot contain:
it is a property of the *cross-section*. It is strictly distinct from v30/v40/v44 (which derive
a regime bit/vector from ONE index series vs its DMA — a single time series, not breadth) and
from v51 (this-stock's rank *within* the panel — relative strength, not aggregate
participation). A per-stock policy that can see aggregate participation can lean into
broad-based trends and de-risk into narrowing ones.

**Code change (single variable vs v18: +breadth columns).**
- New precompute helper `compute_market_breadth(nifty50_path)` (run ONCE, cached to
  `data/_market_breadth.csv`): for each `datetime` across all `*_daily.csv`, compute each
  listed stock's own trailing 50-DMA (`close.rolling(50).mean()`, trailing/right-aligned),
  then breadth(t) = mean over stocks-listed-on-t of `1[close_t > DMA50_t]`. Emit (i) breadth
  level ∈ [0,1], (ii) breadth − breadth_{63-day trailing mean} (divergence/momentum), (iii)
  1[breadth > 0.5] regime flag. K≈3.
- In `process_stock`, left-join the cached breadth frame on `datetime` BEFORE the split
  (values are market-wide, identical across stocks); forward-fill past gaps only (never bfill
  across the split). Append the 3 names to `list_of_indicators`.
- Env, reward, selector, hyperparams unchanged.

**How to run.** `python -c "from Rl_v61 import compute_market_breadth, NIFTY50_PATH;
compute_market_breadth(NIFTY50_PATH)"` once, then `python run_panel.py v61` (breadth is
market-wide → read the panel MEAN, not one stock).

**Diagnostic / caveat.**
- **Causality (critical):** each stock's 50-DMA and the 63-day breadth mean MUST be trailing
  (`.rolling`, never centered). breadth(t) uses only closes at/through t. `.shift`-audit with
  `test_indicator_causality.py` — breadth columns at t must be invariant to appended future
  rows. Add the breadth names to `test_indicator_audit.py`'s expected set (they are not on the
  known-leakage list, but the audit uses an explicit version list — v61 must be added there).
- **Survivorship (advisor flag):** compute breadth over only the names actually LISTED on date
  t (non-NaN close), not the fixed final-panel membership — otherwise early dates borrow the
  survival of stocks not yet public. With only the 50 in-repo CSVs, note this is a *proxy* for
  true NIFTY50 breadth (real historical membership churns); acceptable as a market-internal
  signal, but state it in the report.
- **Slow-moving (advisor flag):** breadth is near-constant within a 15% test window, so it
  helps *regime gating* (which trend to trust), not per-bar timing. Expect its value as a
  *conditioning* feature that sharpens other signals, and read max-DD / Sharpe alongside
  outperformance. ≥20-trade gate + v37 exposure-adjusted-alpha selector so a breadth-driven
  cash-hold cannot win.
- Adds only ~3 dims (mild tension with the v55 capacity finding). Outranks v58 (calendar) as
  an information lever; comparable to v60 (VIX) but needs NO external data.

**Sources.** Market breadth (% above MA) as a regime filter / forward-return signal:
https://www.lpl.com/research/blog/market-breadth-and-market-returns.html ;
https://www.schwab.com/learn/story/breadth-check-strength-and-weakness-trend-tracker ;
% of stocks above the 50/200-day MA as breadth regime thresholds,
https://www.thetrading.tools/market-breadth .

## Rl_v62.py — action-repeat / sticky actions (env-side decision-frequency prior)

**Anchor.** Fork of **v18**. Single variable: the env holds each chosen action for `k`
consecutive bars before querying the policy again (decision every `k`-th bar; the intervening
bars re-apply the last action, then settle). Everything else byte-identical to v18.

**Hypothesis.** v18's losses are partly whipsaw/over-trading (INFY: 206 trades; the batch
diagnostics show high-variance churn). A per-bar decision frequency lets the policy react to
one-day noise it cannot distinguish from signal. *Coarsening the decision frequency* is a
structural prior for trend-following: it forces positions to persist, cutting turnover-driven
variance and transaction-cost bleed. This is mechanistically DISTINCT from the reward-side
anti-churn levers already designed — v35 (turnover penalty) and v39 (inaction penalty) *price*
trading in the reward; v62 changes the *environment's* action cadence directly, so the policy
never even chooses on the skipped bars. In the DRL-trading literature PPO specifically is found
to perform BETTER with larger action-repeat values (k≈5–10) than k=1 (A2C prefers small k) —
a rare env-side prior with direct PPO-in-trading support.

**Code change (single variable vs v18: action cadence).**
- `IntegerTradingEnv.step`: add a counter; on bars where `step_count % k != 0`, re-use the
  cached `action_shares` from the last decision bar (subject to the same budget/position
  re-validation in `_process_action`, since cash/holdings changed) instead of the policy's new
  action. Cache the raw decision on `k`-boundary bars. Reward accrues every bar as usual (v12
  log-return − DD, unchanged). Start with **k=3** (small enough to stay well above the
  ≥20-trade gate on a ~370-bar test window).
- Nothing else changes: features, reward, selector, hyperparams, LSTM all v18.

**How to run.** `python -c "from Rl_v62 import process_stock, NIFTY50_PATH; import os;
process_stock(os.path.join(NIFTY50_PATH,'INFY_daily.csv'))"` (INFY = the over-trading case),
then `python run_panel.py v62`.

**Diagnostic / caveat.**
- **Gate interaction (advisor flag — the key risk):** large `k` starves trading and drifts
  toward the degenerate cash-hold the ≥20-trade gate exists to reject. k=3 is chosen to keep
  ≳30 decision bars available; if trade count on any stock falls below 20, that stock's result
  is void — do NOT raise k to chase a smoother curve. If k=3 clears the gate AND lifts
  exposure-adjusted alpha, a k=2/k=5 mini-sweep is the natural follow-up (each still ONE
  variable vs v18).
- **Not a hold-action substitute:** v18 already has a "do nothing" action (action≈0). v62 is
  about *cadence*, not adding a hold — the mechanism is persistence of the last non-trivial
  decision, which is why it attacks whipsaw specifically.
- Read turnover and cost drag explicitly (trades.csv): the win condition is *fewer, better*
  trades, not merely fewer trades. Score with the v37 selector.
- Honest flag: sticky actions have a MIXED record (in ALE they typically *reduce* performance);
  the positive evidence is specifically PPO-in-trading. If k=3 regresses vs v18, discard —
  do not retry larger k (that only deepens the cash-hold risk).

**Sources.** Sticky-actions / action-repeat definition & PPO-prefers-larger-k in trading:
https://arxiv.org/pdf/2004.06627 (An Application of Deep RL to Algorithmic Trading) ;
sticky actions as an env stochasticity/robustness mechanism (ALE), https://arxiv.org/pdf/1812.06110 .

## Rl_v63.py — additive Gaussian input-noise injection during training (data-space regularizer)

**Anchor.** Fork of **v18**. Single variable: during TRAINING only, add small zero-mean
Gaussian noise to the (already VecNormalized) observation before it reaches the policy. Noise
is OFF at validation and test. Everything else byte-identical to v18.

**Hypothesis.** The generalization gap (train critic EV 0.95–0.99, poor test) is the signature
of the policy memorizing the ~1750 training bars. Injecting small input jitter during training
is a data-space regularizer: it smooths the policy/value functions over an ε-ball around each
observed state, which the RL-generalization literature (Selective Noise Injection, IBAC;
Igl et al. NeurIPS 2019) shows improves transfer to held-out states/environments. It is
materially DIFFERENT from the two rejected/adjacent levers: (1) rejected weight/L2/reward
*regularization* penalizes parameters or reward — a parameter-space penalty; v63 perturbs the
*inputs* — a data-space augmentation with no penalty term. (2) v27 (feature-masking) *zeroes
whole features* (dropout-style); v63 *jitters ALL features by a small amount* (additive), a
distinct corruption model that preserves each feature's information while blurring its exact
value.

**Code change (single variable vs v18: train-time obs noise).**
- A thin `VecEnvWrapper` (or observation hook) placed OUTSIDE `VecNormalize` in
  `train_ppo_model` only: `obs_noisy = obs + N(0, σ²)`, applied on the *normalized* obs so a
  single global σ is scale-consistent across the 106 heterogeneous features (the advisor's
  calibration point: perturb POST-VecNorm, not on raw indicator scales). σ small — start
  **σ=0.1** (≈10% of a unit-variance normalized feature). The val env (ValidationCallback) and
  the test env get NO wrapper → deterministic eval, unchanged.
- Reward, features, selector, hyperparams, LSTM all v18.
- **DRAFTED as `Rl_v63.py` (UNRUN):** a `TrainObsNoiseWrapper(VecEnvWrapper)` placed OUTSIDE
  `VecNormalize`, wrapping ONLY the train env passed to `RecurrentPPO`; the callback still
  receives the plain `VecNormalize` for stat sync, and the returned/saved env is noise-free.
  `ast.parse` clean, 63 ins/3 del vs v18. Run via `run_panel.py v63` (no registration needed).
  A run-routine must first smoke-test that noise is train-only (val/test obs identical to v18).

**How to run.** `python run_panel.py v63` (full panel; the effect is a broad regularizer, read
the panel mean and the train-EV diagnostic).

**Diagnostic / caveat.**
- **Primary read:** does train critic EV drop below v18's 0.95–0.99 *and* does the val curve's
  post-100k decay flatten? If EV still pegs at 0.99, σ is too small (or the overfit is
  time-of-episode structure, not per-state memorization → points to v28/v43, not more noise).
- **Eval must stay clean:** if noise leaks into val/test the metric is corrupted and
  degenerate-selection risk rises — assert the wrapper is train-only in a one-line smoke check.
- **Advisor's expectation-management:** with 106 mostly-weak indicators, jitter may simply
  drown the little signal present → modest upside; low cost, run it, don't over-hope. If it
  helps, it STACKS cleanly under v55 (capacity) and the feature levers.
- σ is part of the ONE change (a σ=0.05/0.1/0.2 sweep is the follow-up, each still one variable
  vs v18). Do NOT also add a noise *schedule* — that would be a second knob.

**Sources.** Igl et al., "Generalization in RL with Selective Noise Injection and Information
Bottleneck," NeurIPS 2019, https://arxiv.org/html/1910.12911 ;
https://papers.nips.cc/paper/9546-generalization-in-reinforcement-learning-with-selective-noise-injection-and-information-bottleneck.pdf ;
data augmentation for RL generalization (RAD/DrAC family),
https://proceedings.neurips.cc/paper/2021/file/2b38c2df6a49b97f706ec9148ce48d86-Paper.pdf .

## Rl_v64.py — explicit short-lag return frame-stack (append last k daily log-returns to the observation)

**Anchor.** Fork of **v18**. Single variable: append the last `k` daily close-to-close
log-returns as explicit observation columns. Everything else byte-identical to v18.

**Hypothesis.** v18 asks the LSTM to reconstruct recent momentum from a stream of levels and
indicators. Making the last few returns *explicit* offloads that reconstruction from the
recurrent memory onto the input, a representation change that in practice stabilizes learning
and often helps even when the information is nominally derivable. It is DISTINCT from v54
(weekly-resampled multi-timeframe context — a coarser horizon) and from v47 (which *replaces*
the whole feature set with stationary returns); v64 *adds* a tiny stationary short-lag block on
top of v18's existing 106 features, changing only the representation of recent momentum.

**Code change (single variable vs v18: +k lag-return columns).**
- `add_lag_return_features(df, k=5)`: `logret = log(close).diff()`, then columns
  `logret_lag_1 … logret_lag_k` via `logret.shift(1..k)` (all strictly past bars — lag_1 is
  yesterday's return, known at today's decision). Append names to `list_of_indicators`. K=5.
- Leading NaNs handled by v18's existing trim-to-first-all-non-null + ffill/0 path (no new NaN
  logic). Env, reward, selector, hyperparams unchanged.

**How to run.** `python run_panel.py v64` (full panel).

**Diagnostic / caveat.**
- **Causality:** every column is a `.shift(≥1)` of a past return → trivially causal; still run
  `test_indicator_causality.py`, and add v64 to `test_indicator_audit.py`'s explicit version
  list (lag-returns are not leakage names, but the audit is version-gated).
- **It IS a gap-closer (advisor):** the LSTM already ingests the ordered sequence, so explicit
  lagged returns are mostly redundant re-encoding — a feature-convenience, no NEW information.
  The value is representational (offloading the LSTM), so expect a small effect. Cheapest of the
  four to implement; fine to include, ranked below v61–v63.
- Adds k=5 dims (mild capacity tension); if it helps, it composes with v55.
- k is part of the one change (k∈{3,5,10} is the follow-up sweep). Do not also change scaling.

**Sources.** Frame-stacking / explicit recent-observation history as a standard RL input prior:
https://arxiv.org/pdf/1812.06110 ; stationary return features for financial RL,
https://arxiv.org/abs/1911.10107 .

## METHODOLOGY (not a model variant) — v65: walk-forward multi-fold TEST evaluation (fix the yardstick)

**Anchor / status.** NOT a fork of v18's model — a change to how EVERY variant is scored. The
advisor flagged this as arguably the highest-leverage item in the batch, because it fixes the
measurement that all of v19–v64 inherit. Companion script, not an `Rl_vNN.py`. Distinct from
v29/v38 (which add multi-window *validation/checkpoint-selection*) and v37 (exposure-adjusted
*selector*): v65 changes the final *test* evaluation into multiple folds.

**Problem it fixes.** The entire champion ranking (v18 mean −63.2pp, 1/10 beats B&H) rests on
ONE 15% chronological test slice per stock. A single window is a single draw: "beats B&H" on
that slice can be the luck of one regime rather than skill, and every fork is judged against
the same possibly-atypical yardstick. No amount of model tuning fixes a noisy ruler.

**Change (one methodological variable: single-fold → walk-forward multi-fold test).**
- New `walkforward_eval.py`: instead of one 70/15/15 split, sweep the test window forward in
  `F` expanding/rolling folds (e.g. train-on-past / validate / test-next-slice, advance,
  repeat), reusing v18's existing `train_ppo_model` / `test_ppo_model` / v37 selector unchanged
  per fold. Report per-stock the DISTRIBUTION of exposure-adjusted alpha across folds (mean,
  std, % of folds beating B&H, and a Deflated-Sharpe-style adjustment for the fold count), not
  a single number.
- Purely additive: does not touch any `Rl_vNN.py`; a variant is "better" only if it wins on the
  fold *distribution*, which is far harder to fake than one window.

**How to run.** `python walkforward_eval.py v18` to establish the multi-fold champion baseline,
then `python walkforward_eval.py v61` (etc.) and compare distributions.

**Diagnostic / caveat.**
- **Cost:** F folds ≈ F× the training compute per stock. Start with F=3 on a 3-stock panel
  (RELIANCE/ITC/HDFCBANK, the recalibrated proxy panel) before the full 10 × F.
- **Causality across folds (advisor — specify the embargo SIZE):** each fold's
  scalers/VecNormalize/feature computation must be fit on that fold's train prefix ONLY, AND the
  embargo gap between a fold's train and test must be **≥ the longest indicator lookback**
  (v18's 50-DMA-and-longer windows; a breadth/regime feature can be longer) **PLUS the LSTM
  burn-in** — otherwise test-side features computed adjacent to train leak trailing-window
  information across the boundary. Also **recompute per-fold-train**, not once on the full
  series: `hmax`/median-close, the first-all-non-null trim row, and every rolling feature. A
  gap sized only to "a few bars" is the trap.
- **Interpretation:** if v18's single-window "1/10 beats B&H" collapses to "beats B&H in a small,
  inconsistent fraction of folds," that RE-FRAMES the whole project (the one-window wins were
  partly luck) and should be logged to the FRONTIER as a measurement correction — higher
  leverage than any single fork, because it tells the run routines which apparent wins are real.

**Sources.** Combinatorial purged cross-validation & the multiple-testing/overfit problem in
backtests — López de Prado, "Advances in Financial Machine Learning" (CPCV, Deflated Sharpe);
Deflated Sharpe Ratio, https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551 ;
walk-forward / purged CV for financial time series,
https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3257420 .

## Rl_v66.py — DESIGN-ONLY / LOW PRIORITY — train-fit PCA compression of the observation

**Anchor.** Fork of **v18**. Single variable: replace the 106-indicator observation block with
its top-`m` train-fit principal components (prices/cash/shares untouched). DESIGN-ONLY and
LOW PRIORITY — written for completeness with an honest negative prior, not a recommended run.

**Hypothesis.** Observational-overfitting theory (Song et al., 2019) says a chunk of RL
overfit is the agent latching onto *spurious, redundant* observation features. v18's 106
pandas-ta indicators are heavily collinear (many are transforms of the same price/vol series).
PCA fit on the TRAIN split only, projecting val/test through the same components, removes the
linear redundancy and shrinks the input to `m`≈15–20 uncorrelated axes — a principled
de-correlation, DISTINCT from v26 (an arbitrary hand-cut to 22 names — an invalidated
artifact), from v46 (supervised MI *selection* of raw names — keeps original axes), and from
v50 (rank-normalization — same dimensionality). It is a pure gap-closer (a linear reparam of
existing info — no new information, so it cannot raise the ceiling).

**Code change (single variable vs v18: obs = train-fit PCA scores).**
- In `process_stock`, after the train/val/test split and RobustScaler, fit
  `sklearn.decomposition.PCA(n_components=m)` on `train_df`'s indicator columns ONLY, then
  `transform` all three splits; replace the indicator block with the `m` component columns.
  `list_of_indicators` becomes `["PC1"…"PCm"]`. Everything downstream (env, reward, selector,
  hyperparams) unchanged.

**How to run.** `python run_panel.py v66` (only if a slot is free after v61–v65).

**Diagnostic / caveat (HONEST — this is why it is low priority).**
- **Poor financial-DNN track record:** the literature repeatedly finds PCA/CART preprocessing
  does NOT significantly help — and sometimes *degrades* — deep models on market data, because
  variance-ranked components discard low-variance-but-predictive signal (information loss). Do
  NOT run this before the higher-value levers; if run and it loses, do not retry other `m`.
- **Leakage:** PCA MUST be fit on train ONLY and applied to val/test via the frozen components
  (same discipline as the RobustScaler). A union-fit PCA leaks the test distribution.
- **Scope (advisor):** compress ONLY the indicator block. Cash, position, and price state must
  pass through verbatim — the agent needs them exactly, and folding them into principal
  components scrambles the account state the env logic and reward depend on.
- **`m` is part of the one change** (an `m`∈{10,20,30} sweep is the follow-up, each one
  variable vs v18). ≥20-trade gate + v37 selector still apply.

**Sources.** Song et al., "Observational Overfitting in Reinforcement Learning" (spurious obs
features drive overfit), https://arxiv.org/pdf/1912.02975 ; PCA can *degrade* deep stock-prediction
models via information loss, https://arxiv.org/pdf/2003.01859 .

## Rl_v67.py — LOW PRIORITY / UNCERTAINTY PROBE — test-time stochastic action dispersion

**Anchor.** Fork of **v18**. Touches only `test_ppo_model`; training byte-identical to v18.
**Reframed after advisor review (do NOT ship as a performance lever):** for v18's diagonal-
Gaussian policy head, the deterministic action *is* the distribution mean, and the mean of `R`
stochastic samples is just an unbiased *noisy* estimate of that same mean — so averaging
samples and mapping once ≈ the deterministic action plus sampling noise, i.e. a near **no-op**
(strictly weaker than deterministic). Averaging the raw actions cannot capture any
action→env nonlinearity, because the env map is applied once, after the average. Its honest
use is therefore as an **uncertainty / variance PROBE**, not a return improver.

**Hypothesis (as a diagnostic, not a lever).** The per-step *dispersion* of the R sampled
actions is a cheap read on where the trained policy is uncertain. High dispersion clustered
around the whipsaw/over-trading episodes (INFY) would localize WHERE the policy is guessing —
useful to target the real levers (v55 capacity, v63 noise, v50 rank-norm) rather than to lift
returns directly. Distinct from v22 (train-time *seed* ensemble = R independent trainings) and
v41 (SWA = weight averaging); those combine *different* models, this only re-samples ONE head.

**Code change (single variable vs v18: test read-out only).**
- `test_ppo_model`: per step, draw `R` samples via `predict(deterministic=False)` threading the
  SAME `lstm_states`/`episode_starts`, average the `R` continuous actions, and pass the mean to
  the env. Thread the LSTM state from ONE canonical rollout (e.g. the deterministic pass) to
  keep the recurrent state well-defined; the averaging affects only the action applied. R=15.
- Nothing in training, features, reward, or selection changes.

**How to run.** `python run_panel.py v67` (compare test curves vs v18 head-to-head; the ONLY
difference is the test read-out).

**Diagnostic / caveat.**
- **No-op risk is the headline (advisor):** because avg-of-samples ≈ the deterministic mean,
  the test P&L should be within noise of v18. If it differs *materially*, suspect a bug (state
  mismatch, unseeded sampling), not a real edge. Do NOT report a P&L delta here as a win.
- **State/action mismatch (second-order):** threading the LSTM state from the deterministic
  pass while applying an *averaged stochastic* action is a mild inconsistency — acceptable
  only because avg≈deterministic; if ever reframed as a lever this must be fixed.
- **Read the DISPERSION, not the return:** log per-step std of the R samples; that is the
  intended output. Seed the sampling for reproducibility.
- Ranked LOWEST of the batch — a diagnostic, not a challenger; does not go through the
  ≥20-trade / v37-selector acceptance path.

**Sources.** "Average-then-act" ensemble read-out is more stable than per-head greedy, and
ensembles give ~1/K action-estimate variance reduction: Averaged-DQN (variance reduction by
averaging), https://arxiv.org/pdf/1611.01929 ; ensemble RL for variance reduction / robustness,
https://arxiv.org/pdf/2001.05209 .

---

# Batch v68–v72 — activation/Lipschitz regularization + stationary inputs (advisor-gated, 2026-09-06)

Single-variable forks of the current champion **v18** (v26/feature-reduction and the 22-indicator
proxy are still INVALIDATED cash-hold artifacts per FRONTIER — do NOT anchor to them). This batch
was ranked by an independent opus advisor at session start. It is deliberately built on the ONE
piece of real empirical signal the run/tinker screens have produced: **symmetric capacity
reduction (lstm_hidden+net_arch 128→64) was the only single-variable change that beat baseline**
(+9 to +12pp, still under gate). The advisor's framing: the diagnostics pin the **critic** as the
overfitter (EV 0.95–0.99 on train, poor test; val decays past 100k), so attack effective capacity
and input covariate-shift *directly* on the regularization axis — where v55–v57 only moved the
*width* axis and did so symmetrically across both heads.

Advisor priority: **v68 (LayerNorm) ≈ v69 (critic-only capacity) > v70 (frac-diff, highest
ceiling) > v71 (spectral norm) > v72 (CVaR, HOLD).** Two ideas were considered and **rejected**
this session (see the "Considered and rejected" note at the end of this batch) so no future
session re-drafts them: actor/recurrent LSTM dropout (PPO-unsafe) and potential-based reward
shaping (policy-invariant ⇒ inert, or misspecified ⇒ a v19 duplicate).

---

## Rl_v68.py — LayerNorm in the actor-critic network (activation normalization)  [QUEUE, top-tier]

**Anchor.** Fork of **v18**. Single variable: insert LayerNorm into the policy/value network
(the post-LSTM MLP extractor and the LSTM *output*). Everything else — features, reward, selector,
hyperparameters, LSTM size — byte-identical to v18.

**Hypothesis.** The measured symptom is a memorizing critic (train EV pegged 0.95–0.99, val curve
peaks ~100k then decays). LayerNorm is the single most robustly-supported intervention in the
recent plasticity-loss / RL-generalization literature for exactly this signature: it keeps
activation scales bounded as the on-policy data distribution drifts, prevents the effective
learning-rate blow-up and dormant-neuron accumulation that accompany critic overfit, and does so
**without shrinking weight magnitudes** — so it is mechanistically *distinct from the rejected
L2/weight regularization* (which biases parameters toward zero and collapsed clip_fraction in
v10/v11). It sits on this project's one real empirical signal (capacity reduction helped) but on
the regularization axis instead of the width axis, and it is distinct from VecNormalize (which
normalizes the *observation input*, not internal *activations* — nothing in v19–v67 touches
activation normalization).

**Honest prior (do not over-hope).** The literature is explicit that LayerNorm reliably fixes
*training-time* plasticity but is **inconsistent on generalization on its own** — the clean wins
come when it is combined with a regenerative/shrink-perturb regularizer (Lyle et al. 2024). So the
realistic expected outcome is "critic EV finally drops below 0.99 and val stops decaying," which
is a *necessary* precondition for the later levers even if test P&L does not jump on this change
alone. That diagnostic movement is itself the deliverable.

**Code change (single variable vs v18: activation normalization).**
- Subclass `MlpLstmPolicy` (sb3-contrib `RecurrentActorCriticPolicy`) and inject `nn.LayerNorm`
  into the MLP extractor and after the LSTM output projection, then pass the subclass as the
  policy to `RecurrentPPO` in `train_ppo_model` (~Rl_v18.py:785). `policy_kwargs` unchanged
  otherwise (lstm_hidden_size=128, net_arch=[128], Tanh).
- **Feasibility (advisor):** LayerNorm on the MLP extractor and on the LSTM *output* is a small
  custom-policy edit. LayerNorm *inside the LSTM recurrence* would need a custom LSTM cell (SB3
  uses `nn.LSTM`) — do NOT do that; the cheap extractor+output version captures most of the
  benefit and keeps this a true single variable. Reward/features/selector all v18.

**How to run.** `python run_panel.py v68` (full panel; read the train-EV and val-curve
diagnostics first, P&L second).

**Diagnostic / caveat.**
- **Primary read:** does train critic EV drop below v18's 0.95–0.99 *and* does the post-100k val
  decay flatten? That is the intended effect; a P&L lift is a bonus, not the acceptance test.
- **Guardrail:** watch `clip_fraction` and policy `std`. LayerNorm should NOT collapse clip_frac
  (that was the L2/DSR failure); if it does, the insertion point is wrong (e.g. normalizing the
  action pre-logits) — move it off the action head.
- **Acceptance:** a genuine active policy (≥20 trades/stock) scored by the v37 exposure-adjusted
  selector, beating v18. INFY / HDFCBANK (the clearest overfit casualties) are priority reads.

**Sources.** Lyle et al., "Normalization and effective learning rates in RL," NeurIPS 2024,
https://proceedings.neurips.cc/paper_files/paper/2024/file/c04d37be05ba74419d2d5705972a9d64-Paper-Conference.pdf ;
Juliani & Ash, "A Study of Plasticity Loss in On-Policy Deep RL" (PPO), NeurIPS 2024,
https://proceedings.neurips.cc/paper_files/paper/2024/file/ce7984e36d58659211a8dc7d5457cd6f-Paper-Conference.pdf ;
"Plasticity Loss in Deep RL: A Survey," https://arxiv.org/html/2411.04832v3 .

---

## Rl_v69.py — asymmetric critic-only capacity (shrink the value head only)  [QUEUE, top-tier — strongest new lever]

**Anchor.** Fork of **v18**. Single variable: give the **value (critic) head less capacity than
the policy (actor) head** via SB3's dict `net_arch`, leaving the actor untouched. Everything else
byte-identical to v18.

**Hypothesis.** This is the most literal possible response to the project's own diagnostic. The
critic is the overfitter (EV 0.95–0.99 while the actor's test behavior is poor), yet every
capacity lever tried so far (v55/v56/v57) shrinks the actor **and** critic *symmetrically*.
Shrinking only the value head reduces the critic's ability to memorize per-episode training
returns — which is what EV→0.99 measures — while preserving the actor's expressiveness to still
represent a good trading policy. It is distinct from v55–v57 (symmetric shrink) and from v68
(normalization, not width). The advisor ranked this at parity with v68 as the cheapest high-value
experiment on the board (a one-line `net_arch` change).

**Code change (single variable vs v18: asymmetric head width).**
- `Rl_v18.py:777` `net_arch: [128]` → `net_arch: {"pi": [128], "vf": [64]}` (SB3 dict form;
  actor width unchanged at 128, critic MLP head halved to 64). `lstm_hidden_size` stays 128 for
  both (do not also change the LSTM — that would be a second variable, and v57 already probes the
  LSTM locus).
- **Optional PPO-safe stack (a *second*, separately-run one-variable fork, not combined here):**
  dropout on the **value net only**. This is the salvageable, PPO-safe core of the rejected
  actor/recurrent-dropout idea — the PPO importance ratio and entropy depend solely on the actor,
  so value-net dropout cannot corrupt them, and it directly regularizes the overfitting critic.
  Keep it as its own run (v69-b) so the width change and the dropout change stay isolated.

**How to run.** `python run_panel.py v69` (full panel).

**Diagnostic / caveat.**
- **Primary read:** does critic EV fall below 0.99 **without** the actor degrading (trade count
  stays ≥20/stock, actions stay varied)? If the actor collapses to cash, the critic starvation
  went too far — try `"vf":[96]` before `[64]`.
- **Acceptance:** genuine active policy beating v18 under the v37 selector.
- Keep to ONE change: width OR value-dropout, not both in the same run.

**Sources.** Value-function overfit as the RL generalization bottleneck & spectral/normalization
control of the critic: Bjorck et al., "Towards Deeper Deep RL with Spectral Normalization,"
NeurIPS 2021, https://arxiv.org/abs/2106.01151 ; SB3 `net_arch` dict form (per-head width),
https://stable-baselines3.readthedocs.io/en/master/guide/custom_policy.html ;
"Normalization and effective learning rates in RL," NeurIPS 2024 (critic-side effect),
https://proceedings.neurips.cc/paper_files/paper/2024/file/c04d37be05ba74419d2d5705972a9d64-Paper-Conference.pdf .

---

## Rl_v70.py — fractional differentiation of the price channel (stationary, memory-preserving)  [QUEUE — highest ceiling]

**Anchor.** Fork of **v18**. Single variable: replace/augment the raw price channel with its
**fractionally-differentiated** transform — a real differencing order `d*∈(0,1)` (not d=0 raw
price, not d=1 returns) that renders the series stationary while retaining maximum long memory.
Applied ONLY to the price/close channel (optionally volume); the ~98 oscillator indicators are
untouched. Reward, selector, hyperparameters all v18.

**Hypothesis.** This attacks the *cause* the other levers only treat downstream. The train window
is a specific price/vol regime (the 2020–21 bull) and RobustScaler is fit on train, so raw-price
and price-level features on the later test slice extrapolate *outside the fitted range* — a
textbook covariate-shift generator, and a direct route for the critic to key on a price level it
never sees again. Integer differencing to returns (v47's d=1) removes the non-stationarity but
also destroys the memory/level information; fractional differencing (López de Prado, AFML ch. 5)
finds the minimum `d*` that passes an ADF stationarity test while keeping the series highly
correlated with the original — stationary-but-memory-preserving inputs shrink the shift *at the
source*. Distinct from v47 (returns = d=1, memory destroyed) and v50 (rolling-norm rescales but
keeps the level's non-stationary structure). The advisor rated it the most on-target lever of the
batch for a *generalization* gap specifically, at the cost of a slightly larger (pipeline) edit.

**Code change (single variable vs v18: frac-diff the price channel).**
- Add a causal fixed-width fractional-differencing helper (FFD: fixed backward window of binomial
  weights `w_k = -w_{k-1}(d-k+1)/k`, truncated when `|w_k|<τ`) and produce a `close_ffd` column
  (and optionally `volume_ffd`), appended to `list_of_indicators` (~Rl_v18.py:88). FFD is causal
  by construction (only past bars enter each value).
- **Fix `d*` on the TRAIN slice only** — binary-search the smallest `d` whose `close_ffd` passes
  ADF on the train prefix, then apply that fixed `d*` to val and test (choosing `d` on the full
  series is a leak). Keep the price channel; the FFD column is an *added* stationary view.
- Because this touches `list_of_indicators`, the `.py` draft MUST add `"Rl_v70"` to the explicit
  version list in `test_indicator_audit.py` (~line 48) AND pass `test_indicator_causality.py`
  (FFD is causal, so the train-prefix value must equal the full-series value — this is the exact
  invariant that test checks). Do NOT introduce any known-leakage name.

**How to run.** `python run_panel.py v70` (full panel; then `python test_indicator_causality.py`
with `CAUSALITY_SYMBOL=RELIANCE` to confirm the FFD column is causal).

**Diagnostic / caveat.**
- **Primary read (same as v26/v55):** does train EV finally drop below 0.99 and do val curves
  stop decaying past 100k? A frac-diff price view should reduce test-slice extrapolation.
- **Leakage guard is mandatory:** d* chosen on train only; causality test must pass. If it fails,
  the FFD window is peeking (bug in the weight truncation or a centered window) — fix before any
  panel read.
- **Keep it single-variable:** frac-diff the price channel only, not all 98 indicators (most are
  already oscillator-stationary; broadcasting muddies the experiment). `d*` and `τ` are part of
  the ONE change; a `d` sweep is the follow-up, each still one variable vs v18.

**Sources.** López de Prado, *Advances in Financial Machine Learning*, ch. 5 "Fractionally
Differentiated Features," https://www.oreilly.com/library/view/advances-in-financial/9781119482086/c05.xhtml ;
"Fractional differentiation and its use in machine learning," Springer,
https://link.springer.com/article/10.1007/s12572-021-00299-5 ;
Hudson & Thames implementation notes, https://hudsonthames.org/fractional-differentiation/ .

---

## Rl_v71.py — spectral normalization of the policy/value MLP (Lipschitz control)  [QUEUE — below v68/v69]

**Anchor.** Fork of **v18**. Single variable: wrap the linear layers of the actor-critic MLP with
`torch.nn.utils.spectral_norm` (bound each layer's largest singular value), leaving width, LSTM,
reward, features, and selector at v18.

**Hypothesis.** Spectral normalization constrains the network's **Lipschitz constant** — its
sensitivity to input perturbations — which is precisely the quantity that blows up under the
train→test covariate shift this project has. Mechanistically it is distinct from both v68
(LayerNorm rescales *activations*) and the rejected L2 (shrinks *weight magnitude*): it bounds the
*gain* of each layer without forcing weights toward zero. In value-based RL, constraining the
Lipschitz constant of the critic recovers much of the benefit of heavier machinery (Gogianu et
al. 2021 lift C51 to Rainbow-level with a single spectrally-normalized layer) and stabilizes
larger nets (Bjorck et al. 2021); the 2024 continual-learning work shows spectral *regularization*
reduces hyperparameter sensitivity and prevents gradient/parameter explosion — the same
overfit-critic axis as v68/v69.

**Code change (single variable vs v18: spectral norm on MLP linears).**
- In the custom policy, apply `spectral_norm` to the `nn.Linear` layers of the MLP extractor
  (and, as the primary target, the **value** head). Do NOT apply it to the LSTM (custom cell
  needed) or to the action mean/log-std head (can distort the policy distribution). One power
  iteration per forward (SB3/PyTorch default) — negligible cost.
- Everything else v18.

**How to run.** `python run_panel.py v71` (full panel).

**Diagnostic / caveat.**
- **Honest risk (advisor):** it is regularization-family, so it carries nonzero risk of the
  v10/v11 `clip_fraction`-collapse signature. Same guardrail: watch clip_fraction and std; if
  they collapse, restrict spectral_norm to the value head only.
- **Primary read:** critic EV below 0.99 and flatter val decay, with a genuine active policy.
- **Ordering:** run AFTER v68/v69 confirm the normalization/Lipschitz axis is the right one; if
  LayerNorm already fixes the EV/val diagnostic, spectral norm is a redundant second option, not a
  stack (running both at once is two variables).

**Sources.** Gogianu et al., "Spectral Normalisation for Deep RL: an Optimisation Perspective,"
ICML 2021, https://proceedings.mlr.press/v139/gogianu21a/gogianu21a.pdf ;
Bjorck et al., "Towards Deeper Deep RL with Spectral Normalization," NeurIPS 2021,
https://arxiv.org/abs/2106.01151 ;
"Learning Continually by Spectral Regularization," ICLR 2025,
https://arxiv.org/pdf/2406.06811 .

---

## Rl_v72.py — DESIGN ONLY / HOLD — CVaR (expected-shortfall) downside reward penalty

**Anchor.** Fork of **v18**. Single variable: replace v12/v18's fixed-threshold drawdown penalty
term with a **CVaR (expected shortfall)** penalty — the mean of the worst-`k`% per-step returns
over a rolling window — leaving the primary log-return reward, features, selector, and
hyperparameters unchanged.

**Hypothesis.** CVaR is a smarter member of the drawdown-penalty family than the fixed
`λ·max(0, dd − 0.10)` term (Rl_v18.py:525): it penalizes the *tail* of the realized return
distribution rather than a hand-picked 10% peak-to-trough threshold, so it adapts to each stock's
volatility. Crucially it is **NOT the rejected Differential Sharpe Ratio**: CVaR = mean of the
worst-k% of a rolling return window — no ratio and no `(B − A²)^{3/2}` denominator, so the DSR
detonation mode (VL→85, clip_frac→1e-4) is structurally absent.

**Why DESIGN ONLY / HOLD (advisor).** Be skeptical that this helps the *generalization* problem.
The project's disease is failure-to-generalize and losing to trend, not excessive downside
appetite. CVaR is a reward-*shape* change: at best it improves risk-adjusted *test* metrics
(Sharpe, maxDD); it does not explain or fix the val decay after 100k. It also lands squarely in
the v10/v11 trap zone — co-varying reward shape with the val-selection interaction. **Do not run
it until a reward-side lever is demonstrably the bottleneck**, and if run, run it only AFTER
v68–v71 so reward shape is not confounded with the normalization/capacity levers that the
diagnostics actually point to.

**Code change (single variable vs v18: penalty term only).**
- Track a rolling deque of the last `N` per-step portfolio log-returns in the env; compute
  `cvar = mean(sorted(returns)[:ceil(kN)])` (the worst `k`%, e.g. k=0.10, N=20); set
  `reward = primary − λ · max(0, −cvar)` in place of the DD-penalty line (Rl_v18.py:525–527).
  `λ`, `k`, `N` are the ONE change's constants.

**Diagnostic to look for.** If ever run: does test Sharpe/maxDD improve *without* the val-return
selector degenerating to cash-holds (the ≥20-trade gate must still pass)? Read train EV to
confirm it is unchanged (this lever should not touch the generalization gap; if EV moves, the
penalty is dominating the primary reward — λ too high).

**Sources.** Risk-sensitive RL with CVaR (no exploding denominator), "Robust Risk-Sensitive RL
with CVaR," https://arxiv.org/pdf/2405.01718 ; "Risk-Sensitive Reward-Free RL with CVaR," ICML
2024, https://proceedings.mlr.press/v235/ni24c.html .

---

## Considered and REJECTED this session (2026-09-06) — do NOT re-draft without a materially different mechanism

- **Actor / recurrent (variational) LSTM dropout.** Genuinely distinct from v27 (input masking)
  and v63 (input noise) — Gal-Ghahramani dropout regularizes the recurrent hidden dynamics, not
  the inputs — and distinct from the rejected L2 (multiplicative noise / implicit sub-network
  ensemble, not weight shrinkage). **But it is PPO-unsafe in the policy net:** dropout makes the
  acting distribution differ from the distribution re-evaluated in the loss, corrupting the PPO
  importance ratio and the entropy term, and reproduces the same `clip_fraction`/`std` pathology
  v10/v11 already showed. The ONE salvageable, PPO-safe piece — dropout on the **value net only**
  (the ratio never sees the critic) — is captured as the optional v69-b stack, not here.
- **Potential-based reward shaping (Ng 1999) toward trend-holding.** Disqualified on theory:
  `F = γΦ(s') − Φ(s)` is *provably policy-invariant*, so it cannot change the learned policy at
  the optimum — it only alters the optimization path, i.e. reaches the same overfit faster, which
  is neutral-to-harmful given the disease is overfitting-at-convergence gated by val early-stop.
  The only way it "helps" is by misspecifying the potential (non-zero terminal potential / not a
  true difference form), at which point it is no longer policy-invariant and is simply
  **v19 (B&H-relative reward) in disguise**. Either inert or a duplicate — dropped.
