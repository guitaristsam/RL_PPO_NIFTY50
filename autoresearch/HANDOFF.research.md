# HANDOFF — auto-research (private to this routine)

_Last session: 2026-09-05 (UTC). Fresh cold-resume every fire — read this FIRST._

## State at end of 2026-09-05 session

- **Champion for building = v18** (unchanged on the board). v26 is still the INVALIDATED
  cash-hold artifact — do NOT anchor to it. Hard rule stands: a challenger counts only if it
  beats v18 with GENUINE ACTIVE policies (≥20 trades/stock), scored by exposure-adjusted
  active return (v37's selector).
- **No champion movement on the board this cycle.** FRONTIER CHAMPION rows still v18; the fast
  proxy champion (22-ind, -7.855pp) remains flagged as a degenerate TATAMOTORS artifact and the
  proxy panel was recalibrated to RELIANCE/ITC/HDFCBANK (baseline -9.194pp @seed42, gate 94.2pp)
  — unreachable, i.e. the proxy is a noisy directional screen only. So I forked from v18 again.
  Next session: re-check FRONTIER first; if a run validated any challenger (v19/v22/v24/v37/v55),
  DEEPEN the winner instead of adding more cold v18 forks.

## What I shipped this session (on auto/research; commits 1d39a1a, 5b41057)

variants.md now runs through **v67**. Added two batches, both single-variable vs v18, both
advisor-gated (boundary-a pre-write ranking; boundary-b pre-PR):

- **v61** market-breadth exogenous feature (% of the 50-CSV panel above own 50-DMA). **CEILING
  lever, advisor TOP PICK** — new information, buildable from in-repo CSVs, NO external-data gate
  (unlike v60 VIX). Distinct from v30/v40 (single index) and v51 (this-stock rank). Watch:
  survivorship (rank only names listed on date t), slow-moving (regime-gating not per-bar timing).
- **v62** action-repeat / sticky actions (env-side, hold action k=3 bars). Anti-overtrading GC,
  distinct from reward-side v35/v39. KEY RISK: large k → cash-hold, fails ≥20-trade gate; keep k small.
- **v63** additive Gaussian input-noise, TRAIN-ONLY (SNI/IBAC data-space regularizer). GC.
  Distinct from rejected weight/L2 reg (param-space) and v27 masking (zeroes features).
  **DRAFTED as Rl_v63.py — UNRUN, ast-clean, 63 ins/3 del vs v18** (TrainObsNoiseWrapper outside
  VecNormalize, train env only; callback+returned env stay plain).
- **v64** explicit short-lag return frame-stack (last k=5 daily logrets). GC (barely CL), cheap.
- **v65** walk-forward multi-fold TEST evaluation (METHODOLOGY, not a model variant). Advisor's
  "missing high-value" item: the whole champion ranking rests on ONE 15% test slice/stock; a
  multi-fold test fixes the yardstick everything is judged by. Companion `walkforward_eval.py`.
- **v66** train-fit PCA obs compression. DESIGN-ONLY, LOW PRIORITY — honest negative prior
  (PCA often degrades financial DNNs via info loss). Distinct from v26 (hand-cut) / v46 (MI).
- **v67** test-time stochastic action averaging (R=15 samples, average-then-act). Inference-side
  variance lever, no retraining; distinct from v22 (seeds) / v41 (SWA). Modest honest upside.

**Advisor priority order: v61 > v62 > v63 > v64, with v65 a separate measurement prerequisite.**
**KILLED this session (do NOT propose):** VecNormalize norm_reward=True (fights fixed DD scale,
reward already clipped); snapshot ensemble via cyclic LR (correlated snapshots from one overfit
run, dominated by v22/v41); entropy-coef decay-from-0 (val callback already early-stops it, and
naive decay can underperform baseline). Deprioritized, not written.

## Immediate next steps for the NEXT research session

1. Read FRONTIER first. If a run validated any challenger, DEEPEN it (don't add cold v18 forks).
2. Highest-value UNWRITTEN drafts still pending (priority order):
   - **Rl_v51.py** (cross-sectional relative-strength) — still the #1 drafting task per the
     features>selection framing; needs a one-time cross-panel per-date rank precompute from the
     50 CSVs. v61 (market breadth) shares that precompute machinery — draft them together.
   - **Rl_v61.py** (market breadth) — the ceiling lever I proposed; drafting it needs the same
     cross-panel precompute + a causal 50-DMA/breadth helper. HIGH value.
   - **Rl_v62.py** (action-repeat) — localized env change (cache action, counter in step()).
   - **Rl_v47.py** (stationary return features) — contained.
3. If run-routines report a challenger stuck below the ≥20-trade gate, the anti-degeneracy
   levers (v39 inaction penalty, v62 cadence, v49 BC warm-start) become higher priority.
4. The signal ceiling is still THE problem. Keep pushing run-routines toward the CEILING levers
   (v24/v45 pooled, v51 cross-sectional, v61 breadth, v60 VIX) over more reward/hyperparam forks.

## Do NOT re-propose (rejected list, CLAUDE.md + this session)
DSR reward, weight/L2/reward regularization, deepening-only DD, 1M timesteps, min-val-trades=5,
B&H-relative reward (v19 is UNRUN not rejected), norm_reward=True, snapshot-cyclic-LR ensemble,
entropy-decay-from-0. v49 BC must stay warm-START only (no persistent KL anchor = the rejected reg).

## Gotchas
- v18 anchors (verified 2026-09-05): IntegerTradingEnv step/_process_action ~432-509;
  train_ppo_model ~714 (VecNormalize block ~733-739, model ctor ~785, PPO_PARAMS ~756-780);
  process_stock ~1224 (split wiring ~1305-1316); ValidationCallback ~586.
- run_panel.py does importlib.import_module(f"Rl_{ver}") → `python run_panel.py v63` just works.
- test_indicator_audit.py uses an EXPLICIT version list (v8-v24,v26). v63 does NOT change
  list_of_indicators (no audit change). BUT v61/v64 DO add feature names → whoever DRAFTS them as
  .py must add that version to the audit's list AND pass test_indicator_causality.py, and must not
  introduce a known-leakage name.
- Rl_v63.py is UNRUN and could NOT be torch/sb3-smoke-tested here (no torch/sb3 in this env). It
  ast-parses. The one real risk is the VecEnvWrapper↔VecNormalize discovery in RecurrentPPO —
  a run-routine should confirm SB3 still finds the inner VecNormalize (unwrap_vec_normalize) and
  that val/test obs are byte-identical to v18 (noise train-only) before a full panel.
- Never edit frozen files (v6-v26 baselines; v27-v60 drafts effectively frozen). Only ADD new vNN.

## PR
- PR #4 (open, draft) → main. Body updated 2026-09-05 to cover v37-v67 (was v37-v54).
