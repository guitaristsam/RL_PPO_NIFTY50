# HANDOFF — auto-research (private to this routine)

_Last session: 2026-09-07 (UTC). Fresh cold-resume every fire — read this FIRST, then FRONTIER._

## State at end of 2026-09-07 session

- **Champion for building = v18** (board unchanged). v26 + the 22-indicator proxy are STILL the
  INVALIDATED cash-hold artifacts — do NOT anchor to them. A challenger counts only if it beats
  v18 with GENUINE ACTIVE policies (≥20 trades/stock).
- **No champion movement on the board this cycle** (design-only routine; I don't run models).
- **THIS SESSION'S ADVISOR VERDICT (opus, session-start) — the key steer, internalize it:**
  proximate cause = overfit via excess EFFECTIVE CAPACITY (why the proxy screen rewards
  capacity-64 / gamma↓ / LR-decay — all ONE shrink mechanism); **ROOT cause = SIGNAL CEILING.**
  Shrink levers only reclaim variance around a ~near-zero-mean edge; best proxy signal ≈ +12pp vs
  a +25.69pp gate NOTHING cleared, and dumb SMA/momentum already match PPO ⇒ the gap is
  INFORMATION, not tuning. **Only new EXOGENOUS features can lift the ceiling.** A 99th transform
  of the same OHLCV series has ~zero marginal EV.
- **Advisor's meta-headline: EXECUTION > more design.** The highest-EV moves are ALREADY WRITTEN &
  UNRUN — push run-routines to execute **v51** (cross-sectional rank), **v60** (India VIX), **v61**
  (breadth), **v19** (B&H-relative reward) BEFORE any new fork. My new v81/v82 are the NEXT
  exogenous levers once those are consumed, not ahead of them.
- **Anti-stack rule (hard):** v80 gamma-0.97 + v55 capacity-64 + v31 LR-decay are ONE mechanism —
  never combine (over-shrinks to the cash-only degenerate = the v10/v11 combine-and-lose trap).

## What I shipped this session (on auto/research)

variants.md now runs through **v85**. Two batches, all single-variable vs **v18**:

- **v80** gamma 0.99→0.97 (discount-as-regularizer; Amit ICML2020 / Jiang AAMAS2015). **DRAFTED
  Rl_v80.py — UNRUN, AST-clean** (copy of v18, only the 3 gamma sites changed: PPO_PARAMS + BOTH
  VecNormalize wrappers; verified by diff). `python run_panel.py v80` works. HIGH-confidence /
  LOW-ceiling — bank it, do NOT stack. Empirically the #2 proxy signal; theory-grounded.
- **v81** market/idiosyncratic RETURN DECOMPOSITION (+2 cols: `MKT_LOGRET_1`, `EXCESS_LOGRET_1`;
  equal-weight panel mean from the 50 CSVs, no external file). **DESIGN — advisor's #1 EV lever.**
  Distinct from v30(bit)/v40(slow 200-DMA trend-state, data-BLOCKED)/v51(rank): it's the
  contemporaneous return split into systematic+idiosyncratic. Needs audit/causality wiring +
  fixed-constituent leakage discipline (like v51). NOT drafted (touches the pipeline + tests).
- **v82** sector-peer relative return (+1 col `SECTOR_EXCESS_LOGRET_1`; needs a hardcoded
  SYMBOL→sector map). **DESIGN — advisor's explicit "missing add,"** the orthogonal 3rd factor.
  Gated behind v81.
- **v83** nearness-to-52wk-high (+1 col `NEAR_52W_HIGH` = close/trailing-252-max; George&Hwang
  2004). **DESIGN — endogenous, honest caveats:** marginal info over 98 TA indicators uncertain;
  attacks the SAME failure mode (a) as UNRUN v19 → run v19 FIRST, draft v83 only if v19 doesn't fix it.
- **v84** cross-sectional return DISPERSION (2nd-moment market regime, +1 broadcast col; Gorman-
  Sapra-Weigand 2010). **DESIGN — LOW priority**, gated behind v81 (coarse single scalar).
- **v85** Probabilistic-Sharpe-Ratio checkpoint selector (reuses significance.py's PSR; corrects
  selection-bias/non-normality that v18-return & v20-Sharpe don't). **DESIGN — cheap insurance,**
  selection axis (advisor: filter not ceiling-mover). Distinct from v20/v37/v73.

## KILLED this session (do NOT re-draft)
- **Time-since-entry / holding-period STATE feature** — LSTM hidden state already encodes it;
  carries no info about whether holding is correct → pure overfit surface. Attack failure mode (b)
  from reward side (v35/v39) instead.
- Stacking the shrink levers (v80/v55/v31). More optimizer/trust-region micro-tweaks (mined out;
  target_kl already contradicted by the proxy, n_epochs/n_steps/batch_size/clip_range all lost).

## Immediate next steps for the NEXT research session
1. Read FRONTIER first. If a run validated ANY challenger (v19/v51/v60/v61/v37/v55/v81…), DEEPEN
   the winner — do NOT add cold v18 forks.
2. If no movement: the ceiling is STILL the problem. Keep pushing run-routines toward EXECUTION of
   the exogenous backlog (v51/v60/v61/v19), then v81 (the drafted-design headliner). Consider
   drafting Rl_v81.py (the .py) since it's the #1 EV lever — but it needs the cross-panel precompute
   + audit/causality wiring + a leakage-safe fixed-constituent build (can't torch/sb3-smoke here).
3. Genuinely-unwritten high-value .py drafts still pending: Rl_v81 (market decomposition — TOP),
   Rl_v77 (episode windowing — needs env reset smoke test), Rl_v68 (LayerNorm), Rl_v70 (frac-diff).

## Do NOT re-propose (rejected — CLAUDE.md + prior + this session)
DSR reward, weight/L2/reward regularization, deepening-only DD, 1M timesteps, min-val-trades=5,
n_epochs 5→3, norm_reward=True, actor/recurrent dropout (PPO-unsafe), potential-based reward
shaping (inert/v19-dup), CONSTANT lr 1e-3/1e-4, decoupled/lower critic LR, unshare-actor/critic-MLP
(no-op at SB3≥1.8.0), naive RAD obs-cutout (PPO-unsafe), holding-period state feature (this
session), stacking shrink levers, more optimizer micro-tweaks. v19/v51/v60/v61 are UNRUN not rejected.
NOTE: gamma *schedule/level* (v80) and LR *schedule* (v31/v74) are NOT the rejected constant-LR
tweaks — different mechanism; keep distinct.

## Gotchas
- v18 anchors (verified 2026-09-07): gamma sites Rl_v18.py:670 (val VecNormalize), :738 (train
  VecNormalize), :761 (PPO_PARAMS) — all THREE are the same discount, move together. PPO_PARAMS
  :756-780; policy_kwargs net_arch :777; model ctor :785. list_of_indicators :88.
- run_panel.py does importlib.import_module(f"Rl_{ver}") → `python run_panel.py v80` just works.
- test_indicator_audit.py uses an EXPLICIT version list; v80 changes NO indicators (no audit edit).
  v81/v82/v83/v84 ADD feature columns → each needs audit + causality wiring (custom names pass the
  static known-leakage check trivially; the causality prefix-equality test is the real guard).
- Never edit frozen files (v6–v26 baselines; v27–v79 drafts effectively frozen). Only ADD new vNN.

## PR
- PR #4 (open, draft) → main. Update its body to cover v37–v85 (was v37–v78) each session.
