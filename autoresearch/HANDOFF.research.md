# HANDOFF — auto-research (private to this routine)

_Last session: 2026-09-06 (UTC), SECOND fire of the day. Fresh cold-resume every fire — read this FIRST._

## State at end of 2026-09-06 (2nd) session

- **Champion for building = v18** (unchanged on the board). v26 + the 22-indicator proxy are STILL
  the INVALIDATED cash-hold artifacts — do NOT anchor to them. Hard rule stands: a challenger
  counts only if it beats v18 with GENUINE ACTIVE policies (≥20 trades/stock), scored by the v37
  exposure-adjusted-alpha selector.
- **No champion movement on the board this cycle.** FRONTIER CHAMPION rows still v18. The tinker
  proxy (RELIANCE/ITC/HDFCBANK, baseline -9.194pp @seed42, gate 25.69pp under METRIC2_clip50) is a
  noisy directional screen; every hyperparam tweak (ITC-2..21) DISCARDED.
  The **one real empirical signal**: symmetric capacity reduction (lstm+net 128→64) was the ONLY
  change to beat baseline (ITC-7 +12.2pp, proxy-exp3 +9.0pp) — still under gate but consistent
  across two independent screens. **This session's advisor argued this is a MEASUREMENT-POWER
  problem, not an idea problem** → see v78 methodology (5-seed comparison to PROMOTE v55).
- Next session: re-check FRONTIER first; if a run validated any challenger (v19/v22/v24/v37/v55/
  v68/v69/v74/v75/v77), DEEPEN the winner instead of adding cold v18 forks.

## What I shipped this session (on auto/research; commits after the v73 batch)

variants.md now runs through **v78**. New batch v74–v78, all single-variable vs **v18**, ranked by
an independent opus advisor (boundary-a). Theme this session: the **OPTIMIZATION-TRAJECTORY** axis
(LR schedule, adaptive-KL trust region) + the advisor's #1 missing lever (**episode-windowing =
data diversity**) + a **measurement-power** methodology to rescue the existing v55 signal. Prior
batches covered regularization/features/selection; the trajectory + data-sampling axes were open.

Advisor ranking of the optimization batch: **v75 (target_kl) > v74 (LR decay) > (decoupled critic
LR — NOT proposed, judged a likely waste: overlaps the completed vf_coef sweep & the v10/v11
"critic-EV non-binding" result).** The advisor's headline was v77 (episode windowing) as the
highest-value missing lever, and v78 (5-seed protocol) as the cheapest path to advance the frontier.

- **v74** COSINE learning-rate decay 3e-4→0 (was constant). **DRAFTED Rl_v74.py — UNRUN, AST-clean.**
  Optimization-trajectory axis; no prior experiment touched the LR *shape* (only constants 1e-3/1e-4,
  rejected). HONEST scoping (advisor): best-val restore already deploys the ~100k checkpoint, so v74
  can't win by "avoiding late decay" — only by a BETTER PEAK. Hence cosine not linear (holds LR high
  through the peak region; linear is ~1.5e-4 there ≈ the rejected constant). Ranked cheap side-run,
  NOT the headline. `python run_panel.py v74` works via importlib. No list_of_indicators change.
- **v75** PPO target_kl=0.02 adaptive epoch-loop early-stop (was None). **DRAFTED Rl_v75.py — UNRUN,
  AST-clean.** Advisor's #1 optimization-side lever to run FIRST. Distinct from rejected fixed
  clip_range (per-sample ratio) — this bounds the AGGREGATE KL per update. TWO caveats baked in:
  (1) with n_epochs=5 it may rarely bind → partial no-op; follow-up 0.01/0.015. (2) if it slows
  learning the val peak can shift PAST the 200k eval grid → read val@200k, extend budget only as a
  SEPARATE (second-variable) confirmation. `python run_panel.py v75` works. No audit edit.
- **v76** ~~decouple/unshare actor-critic MLP~~ **VOIDED by the pre-PR advisor.** Premise FALSE at
  the SB3 pin: SB3 1.8.0 REMOVED shared MLP layers, so v18's `net_arch=[128]` ALREADY builds
  separate policy/value nets (== dict(pi=[128],vf=[128])). v76 is a genuine no-op; the real value-head
  knob is v69's asymmetric shrink. Recorded as VOID in variants.md. **Lesson: any "unshare the
  actor/critic MLP" idea is dead at SB3 ≥ 1.8.0 — only per-head width/depth is a live net_arch lever.**
- **v77** random-start fixed-length (L=252) episode windows within the single-stock TRAIN split.
  **DESIGN, HIGH PRIORITY — advisor's #1 missing lever.** Attacks the overfit ROOT (one path
  traversed ~114×) not the downstream optimizer. Distinct from v43 (synthetic stitch) and v24/v45
  (cross-stock). Env-side only (reset picks random start + episode-length cap in step). LEFT
  DESIGN-ONLY because it touches reset()/terminal — the exact surface of every "bug already paid
  for" — and needs a V24_LOG_RESETS-style env smoke test I can't run here. Precise code + gotchas in
  variants.md. Whoever drafts: keep L≥252 (DD-penalty horizon), verify ≥20 trades, dedicated RNG.
- **v78** METHODOLOGY (not a model): k-seed ensemble-MEAN (k=5) as the COMPARISON unit (distinct
  from v22 which ensembles at inference). Rationale: v55's +9–12pp is stuck UNDER the gate = seed
  noise, not absence. First application = re-screen v55 as 5-seed mean vs 5-seed v18 → cheapest path
  to PROMOTE a real signal. Reuses v22's seed_offset plumbing + significance.py. For run routines.

**KILLED / not-proposed this session (do NOT re-draft):**
- Decoupled / lower CRITIC learning rate — advisor judged likely waste: it targets critic EV, which
  v10/v11 already showed is NON-binding, and it overlaps the completed vf_coef sweep. Only revisit
  with independent evidence the critic baseline actively poisons advantages (e.g. val improves when
  the critic is frozen).

## Immediate next steps for the NEXT research session

1. Read FRONTIER first. If a run validated any challenger, DEEPEN it (don't add cold v18 forks).
2. **If a run routine has bandwidth, push v78 (5-seed re-screen of v55) as the top action** — it can
   move the frontier with an idea already in hand, unlike any new fork.
3. Highest-value UNWRITTEN .py drafts still pending (priority order):
   - **Rl_v77.py** (episode windowing) — advisor's #1 lever; needs the env-reset smoke test. Draft it
     in a session/routine that can run torch/sb3 + the reset logging.
   - **Rl_v68.py** (LayerNorm) — custom MlpLstmPolicy subclass. Higher code risk; can't torch-smoke here.
   - **Rl_v70.py** (frac-diff) — causal FFD helper + d*-on-train + audit/causality wiring.
   - **Rl_v51.py** (cross-sectional relative-strength) & **Rl_v61.py** (market breadth) — cross-panel
     per-date rank precompute from the 50 CSVs; draft together. #1 "features > selection" ceiling levers.
   - **Rl_v47.py** (stationary return features) — contained.
4. If run-routines report a challenger stuck below the ≥20-trade gate, anti-degeneracy levers
   (v39 inaction penalty, v62 cadence, v49 BC warm-start, v69-b value-dropout) rise in priority.
5. The signal ceiling is still THE problem. Keep pushing run-routines toward CEILING levers
   (v24/v45 pooled, v51 cross-sectional, v61 breadth, v60 VIX, v70 frac-diff, **v77 windowing**) over
   more reward/hyperparam forks. Regularization/trajectory levers (v68/69/71/74/75) are
   necessary-but-maybe-not-sufficient.

## Do NOT re-propose (rejected list — CLAUDE.md + prior + this session)
DSR reward, weight/L2/reward regularization, deepening-only DD, 1M timesteps, min-val-trades=5,
n_epochs 5→3, norm_reward=True, snapshot-cyclic-LR ensemble, entropy-decay-from-0, actor/recurrent
dropout (PPO-unsafe), potential-based reward shaping (inert/v19-dup), CONSTANT lr 1e-3/1e-4,
decoupled/lower critic LR (vf_coef-overlap + critic-EV non-binding), unshare-actor/critic-MLP
(no-op at SB3≥1.8.0, was v76). v19 (B&H-relative) is UNRUN
not rejected. v49 BC must stay warm-START only (persistent KL anchor = the rejected reg). NOTE:
LR *schedule* (v74) and target_kl (v75) are NOT the rejected constant-LR/clip tweaks — different
mechanisms; keep them distinct in future rejected-list reasoning.

## Gotchas
- v18 anchors (verified 2026-09-06): reward/DD penalty Rl_v18.py:511-527 (primary clip :517;
  dd_penalty :525; reward :527); PPO_PARAMS :756-780 (policy_kwargs :772-779, net_arch :777,
  model ctor :785); list_of_indicators :88; IntegerTradingEnv reset :424, step :470-533.
- v74 uses a local `import math` inside train_ppo_model for the cosine closure (minimal diff).
- run_panel.py does importlib.import_module(f"Rl_{ver}") → `python run_panel.py v74`/`v75` just work.
- test_indicator_audit.py uses an EXPLICIT version list. v74/v75/v76 do NOT change list_of_indicators
  (no audit edit). v77 also doesn't (env-only). v70 DOES add a feature → audit+causality wiring needed.
- v68/v71/v76-if-drafted need a custom MlpLstmPolicy subclass or dict net_arch; could NOT be
  torch/sb3-smoke-tested here (no torch/sb3 in this env). v74/v75 are pure-kwarg → lower risk but a
  run-routine must still confirm SB3 accepts the schedule callable / target_kl and that
  clip_fraction/std don't collapse.
- Never edit frozen files (v6-v26 baselines; v27-v73 drafts effectively frozen). Only ADD new vNN.

## PR
- PR #4 (open, draft) → main. Update its body to cover v37–v78 (was v37–v73) each session.
