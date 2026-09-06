# HANDOFF — auto-research (private to this routine)

_Last session: 2026-09-06 (UTC). Fresh cold-resume every fire — read this FIRST._

## State at end of 2026-09-06 session

- **Champion for building = v18** (unchanged on the board). v26 + the 22-indicator proxy are STILL
  the INVALIDATED cash-hold artifacts — do NOT anchor to them. Hard rule stands: a challenger
  counts only if it beats v18 with GENUINE ACTIVE policies (≥20 trades/stock), scored by the v37
  exposure-adjusted-alpha selector.
- **No champion movement on the board this cycle.** FRONTIER CHAMPION rows still v18. The tinker
  proxy (recalibrated to RELIANCE/ITC/HDFCBANK, baseline -9.194pp @seed42, gate 25.69pp under the
  new METRIC2_clip50) is a noisy directional screen; every hyperparam tweak (ITC-2..21) DISCARDED.
  The **one real empirical signal**: symmetric capacity reduction (lstm+net 128→64) was the ONLY
  change to beat baseline (ITC-7 +12.2pp, proxy-exp3 +9.0pp) — still under gate but consistent
  across two independent screens. This anchored tonight's batch.
- Next session: re-check FRONTIER first; if a run validated any challenger (v19/v22/v24/v37/v55/
  v68/v69), DEEPEN the winner instead of adding cold v18 forks.

## What I shipped this session (on auto/research; commits after 30df650)

variants.md now runs through **v72**. New batch v68–v72, all single-variable vs **v18**, ranked by
an independent opus advisor (boundary-a). Theme: attack the diagnosed overfitting-critic
(EV 0.95–0.99, val decay past 100k) on the regularization / input-covariate-shift axes — where
v55–v57 only moved the *width* axis, symmetrically across both heads.

- **v68** LayerNorm in actor-critic net (activation normalization). QUEUE top-tier. Advisor #1 —
  most robustly-supported anti-critic-overfit lever in the plasticity literature; distinct from
  VecNormalize (input) and from rejected L2 (weight shrinkage). HONEST caveat: LayerNorm fixes
  TRAIN plasticity but is INCONSISTENT on generalization alone — the deliverable is the EV/val
  diagnostic movement. Cheap version = extractor + LSTM output only (NOT inside recurrence).
- **v69** asymmetric critic-only capacity: net_arch [128]→{"pi":[128],"vf":[64]}. QUEUE top-tier,
  advisor's STRONGEST NEW lever — most literal response to "the critic memorizes". Distinct from
  v55–57 (symmetric). Optional PPO-safe stack v69-b = value-net-only dropout (the salvageable core
  of the rejected actor-dropout idea; critic is invisible to the PPO ratio). **DRAFTED as
  Rl_v69.py — UNRUN, ast-clean, 15 ins/1 del vs v18** (only the net_arch line + comments;
  `python run_panel.py v69` works via importlib; no list_of_indicators change → no audit edit).
- **v70** fractional differentiation of the PRICE channel (López de Prado FFD). QUEUE, advisor's
  HIGHEST CEILING — fixes covariate shift at the source (RobustScaler fit on train → price levels
  extrapolate on test). Distinct from v47 (returns=d1) and v50 (rolling-norm). GOTCHAS: apply to
  close (+opt volume) ONLY not the 98 indicators; fix d* by ADF on TRAIN slice only (leak else);
  FFD is causal → whoever DRAFTS the .py MUST add "Rl_v70" to test_indicator_audit.py list AND
  pass test_indicator_causality.py.
- **v71** spectral normalization of the policy/value MLP (Lipschitz control). QUEUE, below v68/69.
  = my own spectral idea + advisor New #2. Distinct from LayerNorm (activations) & L2 (magnitude).
  Run AFTER v68/69 confirm the normalization axis; guardrail = clip_fraction/std collapse risk.
- **v72** CVaR/expected-shortfall reward penalty. DESIGN-ONLY / HOLD. Distinct from rejected DSR
  (no exploding denominator) & fixed DD. Advisor skeptical: reward-shape ≠ the generalization
  disease; run only if a reward lever becomes the bottleneck, and only AFTER v68–71.

**KILLED this session (do NOT re-draft — recorded in variants.md "Considered and REJECTED"):**
- actor / recurrent (variational) LSTM dropout — PPO-UNSAFE: dropout in the policy net makes the
  acting dist differ from the loss-evaluated dist, corrupts the importance ratio/entropy →
  v10/v11 clip_frac/std pathology. Only value-net dropout is safe (→ folded into v69-b).
- potential-based reward shaping (Ng 1999) — policy-invariant ⇒ inert (same overfit, faster), or
  misspecified ⇒ v19 (B&H-relative) in disguise.

## Immediate next steps for the NEXT research session

1. Read FRONTIER first. If a run validated any challenger, DEEPEN it (don't add cold v18 forks).
2. Highest-value UNWRITTEN .py drafts still pending (priority order):
   - **Rl_v68.py** (LayerNorm) — needs a custom MlpLstmPolicy subclass (extractor + LSTM output
     LayerNorm). Advisor top-tier. Higher code risk than v69 (custom policy), can't torch-smoke here.
   - **Rl_v70.py** (frac-diff) — needs causal FFD helper + d*-on-train + audit/causality wiring.
   - **Rl_v51.py** (cross-sectional relative-strength) and **Rl_v61.py** (market breadth) — both
     still UNWRITTEN, both need the one-time cross-panel per-date rank precompute from the 50 CSVs;
     draft them together. Still the #1 "features > selection" ceiling levers per earlier sessions.
   - **Rl_v47.py** (stationary return features) — contained.
3. If run-routines report a challenger stuck below the ≥20-trade gate, the anti-degeneracy levers
   (v39 inaction penalty, v62 cadence, v49 BC warm-start, v69-b value-dropout) rise in priority.
4. The signal ceiling is still THE problem. Keep pushing run-routines toward the CEILING levers
   (v24/v45 pooled, v51 cross-sectional, v61 breadth, v60 VIX, v70 frac-diff) over more
   reward/hyperparam forks. Regularization levers (v68/69/71) are necessary-but-maybe-not-sufficient.

## Do NOT re-propose (rejected list — CLAUDE.md + prior + this session)
DSR reward, weight/L2/reward regularization, deepening-only DD, 1M timesteps, min-val-trades=5,
n_epochs 5→3, norm_reward=True, snapshot-cyclic-LR ensemble, entropy-decay-from-0, actor/recurrent
dropout (PPO-unsafe), potential-based reward shaping (inert/v19-dup). v19 (B&H-relative) is UNRUN
not rejected. v49 BC must stay warm-START only (persistent KL anchor = the rejected reg).

## Gotchas
- v18 anchors (verified 2026-09-06): reward/DD penalty Rl_v18.py:511-527 (primary clip :517;
  dd_penalty :525; reward :527); PPO_PARAMS :756-780 (policy_kwargs :772-779, net_arch :777,
  model ctor :785); list_of_indicators :88; feature/tech-indicator wiring in prepare_data_for_finrl
  :286-375 (tech_indicators derived :318). IntegerTradingEnv step ~:490-533.
- run_panel.py does importlib.import_module(f"Rl_{ver}") → `python run_panel.py v69` just works.
- test_indicator_audit.py uses an EXPLICIT version list (v8-v24,v26). v68/v69/v71/v72 do NOT change
  list_of_indicators (no audit edit). v70 DOES add a feature name → whoever DRAFTS v70.py MUST add
  "Rl_v70" to that list AND pass test_indicator_causality.py, and introduce no known-leakage name.
- v68/v71 need a custom MlpLstmPolicy subclass (sb3-contrib RecurrentActorCriticPolicy). Could NOT
  be torch/sb3-smoke-tested here (no torch/sb3 in this env). Rl_v69.py ast-parses; a run-routine
  must confirm SB3 accepts the dict net_arch and that clip_fraction/std don't collapse.
- Never edit frozen files (v6-v26 baselines; v27-v67 drafts effectively frozen). Only ADD new vNN.

## PR
- PR #4 (open, draft) → main. Update its body to cover v37–v72 (was v37–v67) each session.
