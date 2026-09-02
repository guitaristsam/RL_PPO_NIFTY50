# HANDOFF — auto-research (private to this routine)

_Last session: 2026-09-02 (UTC). Fresh cold-resume every fire — read this FIRST._

## State at end of 2026-09-02 session
- CHAMPION is **v26 = 22 curated indicators** (fast-proxy screen, -7.9pp), NOT v18.
  All my new proposals are forked FROM v26, not v18. Do the same next time — read
  the FRONTIER champion rows before proposing anything.
- Frontier direction is clear: **less capacity generalizes better** (v26 feature
  cut +67.7pp; n_steps↓, gamma↓, lstm↓, ent_coef↑ all positive under-gate).
- Key insight I acted on: the 3-stock/60k val oracle is **misaligned, not just
  noisy** (6-indicators → perfect test/-47 val; n_steps=1024 → +26 test/-75 val).
  So fixing the val SELECTOR (v29/v33) is higher-leverage than any regularizer.

## What I shipped this session (on auto/research, pushed)
- variants.md: added section "Variants v27–v34" — 8 single-variable forks from
  v26, ranked v29>v33>v28>v34>v27>v31>v30>v32, + observational-overfitting
  explanation for why 22>106 (FRONTIER next-action #3), with citations.
- Rl_v31.py (UNRUN draft): v26 + linear LR decay. Compiles, 22 indicators intact.
- Rl_v34.py (UNRUN draft): v26 + gSDE (use_sde=True). Compiles. CAVEAT flagged:
  verify sb3-contrib RecurrentPPO accepts use_sde before trusting.
- PR to main #4 opened (DRAFT) and updated: https://github.com/guitaristsam/RL_PPO_NIFTY50/pull/4
- SECOND batch added: v35 (turnover penalty, targets INFY over-trading) + v36
  (DESIGN-ONLY stack of n_steps=256+lstm=64, gated behind full-panel single-var
  confirmation — answers FRONTIER next-action #2). variants.md now covers v27-v36.
- Subscribed to PR #4 activity. Two advisor passes done; all pre-PR fixes applied.

## Immediate next steps for the NEXT research session
1. If champion moved again (read FRONTIER), re-anchor. If any of v27–v34 was run
   by a run-routine, read its READOUT and DEEPEN the winner (next fork from IT).
2. Highest-value unwritten drafts: v29 (multi-subwindow val — MOST invasive, needs
   ValidationCallback rewrite) and v28 (random episode-start — needs env.reset
   edit). Consider drafting these as UNRUN files next.
3. Do NOT re-propose the rejected list (DSR, weight-reg, deepening-DD, 1M steps,
   min-val-trades). v19 (B&H-relative) and v22 (ensemble) are UNRUN not rejected —
   flag to run before inventing more forks; re-baseline both onto v26.

## Gotchas
- Champion config = v26 = v18 defaults + 22-indicator list ONLY. PPO kwargs at
  lines ~760-784 in Rl_v26.py. Indicator list at lines ~94-115.
- run_panel.py does importlib.import_module(f"Rl_{ver}") — a new Rl_vNN.py is
  runnable as `python run_panel.py vNN` with no registration.
- Never edit frozen files (v6-v26 baselines). Only add new vNN.
- Lease: autoresearch/.lease-research — DELETE on clean end, commit+push.
