# HANDOFF — auto-research (private to this routine)

_Last session: 2026-09-03 (UTC). Fresh cold-resume every fire — read this FIRST._

## State at end of 2026-09-03 session

- **RE-ANCHORED to v18.** The FRONTIER now records that **v26 (feature reduction)
  is a DEGENERATE CASH-HOLD ARTIFACT**, not a win (both its B&H-beats were 0/5-trade
  cash-holds; ITC regressed +40pp→−61pp). The auto-tinker proxy champion is the same
  TATAMOTORS cash-hold artifact. **v18 is the restored production champion for
  building.** My PREVIOUS session's v27–v34 forks were anchored to the now-invalidated
  v26 — do NOT build further on them; anchor to v18.
- **Frontier hard requirement:** the next challenger must beat v18 with GENUINE
  ACTIVE policies (≥20 trades/stock). A bear-window cash-hold does not count.
- **Two advisor passes this session** established the key reframe:
  - **Blocker ranking: features > selection > reward.** significance.py (0/49 FDR)
    and baselines.py (PPO ≈ coin-flip vs SMA) say the SIGNAL is the ceiling. The only
    two levers that raise it: **v24 pooled cross-stock training** (~50× data, fixes
    EV=0.99 memorization) and **exogenous regime/cross-asset features** (v40/v44).
  - The selector fix is a **measurement-integrity PRECONDITION**, not an alpha source.
  - **Critical:** naive alpha/IR-over-B&H STILL rewards a bear-window cash-hold (high
    IR: positive low-vol active return vs a falling benchmark). The correct score is
    **exposure-adjusted active return** `active_t = pv_ret_t − exposure_t·bh_ret_t`
    (exposure-matched Jensen's alpha) — a cash-hold has exposure≈0 → score≈0.

## What I shipped this session (on auto/research, pushed)

- variants.md: added **"Variants v37–v44"** — 7 v18-anchored single-variable proposals
  + advisor blocker-ranking + a Deflated-Sharpe methodology note. Sources cited (URLs).
  - **v37** (HIGHEST / prerequisite): exposure-adjusted-alpha val selector + dual
    activity gate. **DRAFTED as Rl_v37.py (UNRUN, parses clean).**
  - v38 multi-window CPCV-style robust selector (mean−std over K purged sub-windows).
  - v39 inaction/missed-opportunity reward penalty (deprioritized vs selector).
  - v40 market-regime feature (index vs 200-DMA); v44 richer exogenous vector (DESIGN).
  - v41 SWA over top-K checkpoints (action-ensemble fallback).
  - v43 stationary block-bootstrap path augmentation (attacks data starvation).
  - v42 DESIGN-ONLY stack (alpha × multi-window), gated behind v37+v38 confirmation.
  - Methodology: Deflated-Sharpe challenger-acceptance gate (extend significance.py).
- Rl_v37.py: UNRUN draft. ONLY change vs v18 = ValidationCallback score (lines
  ~604–711) + restore print + callback construction min_val_trades=20. Env/reward/
  features/hyperparams identical. Verified `ast.parse` OK; no frozen file touched.
- PR #4 (draft, auto/research→main) title+body updated to the v18 re-anchoring.

## Immediate next steps for the NEXT research session

1. Read FRONTIER first. If a run-routine validated v37 or v24, read its READOUT and
   DEEPEN the winner. If v37 works, the next fork is **v42** (alpha × multi-window)
   or layering a feature lever (v40) UNDER the fixed selector.
2. Highest-value unwritten drafts to consider: **v40** (needs an index CSV or an
   equal-weight proxy built from the 50 stock closes — check data/ for an index
   file first) and **v43** (block-bootstrap — a `make_block_bootstrap_train` helper).
3. The signal ceiling is the real problem. Push run-routines toward **v24 pooled**
   + **exogenous features** over any more reward/hyperparameter forks.
4. Do NOT re-propose the rejected list (DSR, weight-reg, deepening-DD, 1M steps,
   min-val-trades=5, B&H-relative v19). v19/v22/v24 are UNRUN not rejected.

## Gotchas

- Champion config for building = **v18** (NOT v26). v18 env/reward at Rl_v18.py
  lines ~404–530; ValidationCallback ~586–711; restore ~819–841; callback
  construction ~794–804.
- v18 env is single-stock (stock_dim=1): `state[0]`=cash, `state[1]`=price,
  `state[1+sd]`=shares. v37's exposure snapshot relies on this.
- run_panel.py does `importlib.import_module(f"Rl_{ver}")` — `python run_panel.py v37`
  runs with no registration.
- Never edit frozen files (v6–v26 baselines, and now v27–v36 drafts are effectively
  frozen too — they're on the branch). Only ADD new vNN.
- Lease: autoresearch/.lease-research — DELETE on clean end, commit+push.
