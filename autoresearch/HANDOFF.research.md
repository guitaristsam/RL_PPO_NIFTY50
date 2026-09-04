# HANDOFF — auto-research (private to this routine)

_Last session: 2026-09-04 (UTC). Fresh cold-resume every fire — read this FIRST._

## State at end of 2026-09-04 session

- **Champion for building = v18** (unchanged). v26 remains an INVALIDATED cash-hold
  artifact; do NOT anchor to it. Frontier hard rule stands: a challenger counts only
  if it beats v18 with GENUINE ACTIVE policies (>=20 trades/stock), scored by
  exposure-adjusted active return (v37's selector).
- **No champion movement on the board this cycle** — run-routines had not yet
  validated v37/v24 as of this session (FRONTIER CHAMPION rows still v18). So I forked
  from v18, not from an un-moved champion. Next session: re-check FRONTIER; if a run
  validated v37 or v24, DEEPEN the winner instead of adding more v18 forks.

## What I shipped this session (on auto/research, pushed: commit 19e2b88)

- variants.md: added **"Variants v46–v50"** block + **v51** (separate ceiling-lever
  block) + **v52** (DESIGN-ONLY). All single-variable vs v18, all advisor-reviewed
  (two advisor passes: boundary-a pre-write ranking, boundary-b pre-PR — see PR).
  - **v46** train-only MI feature selection (principled vs v26's arbitrary cut).
  - **v47** stationary return-based feature representation (level->return).
  - **v48** auxiliary next-return prediction head (SPR-style rep. regularizer).
  - **v49** momentum BC warm-start (anti-degeneracy; advisor DEMOTED to lowest).
  - **v50** causal rolling RANK-normalization (advisor #1 gap-closer).
    **DRAFTED as Rl_v50.py — UNRUN, parses+compiles clean (70 ins/4 del vs v18).**
  - **v51** cross-sectional relative-strength features — advisor's MISSING top pick,
    a genuine CEILING lever (adds info), buildable from the 50 in-repo CSVs.
  - **v52** DESIGN-ONLY meta-labeling (multi-component; gated behind v50/v51 reads).
- Advisor framing folded into variants.md: **"gap-closers vs ceiling levers"** — only
  more information (pooled v24/v45 or new exogenous/cross-sectional features like v51)
  raises the true ceiling; v46-v50 only close the EV=0.99->poor-test gap. Advisor EV
  rank: **v50 > v47 > v46 > v48 > v49**, with **v51 above v46/v48**.
- Rl_v50.py: single change = observation scaling. Static train-fit RobustScaler ->
  causal rolling trailing percentile-RANK (W=252) applied on the CONTINUOUS frame in
  process_stock BEFORE the split (no per-split reset), per-split calls set
  skip_scaling=True. Helper `causal_rolling_rank_normalize()` added before
  prepare_data_for_finrl. Env/reward/features/hyperparams byte-identical to v18.

## Immediate next steps for the NEXT research session

1. Read FRONTIER first. If a run validated v37/v24/any challenger, DEEPEN the winner.
2. Highest-value UNWRITTEN drafts to consider next (in priority order):
   - **Rl_v51.py** (cross-sectional relative-strength) — the ceiling lever; needs a
     one-time cross-panel precompute of per-date ranks from the 50 CSVs. Highest EV.
   - **Rl_v47.py** (stationary return features) — contained: add_return_features()
     helper + swap list_of_indicators to ~15-20 stationary names.
   - **Rl_v46.py** (MI selection) — sklearn.feature_selection.mutual_info_regression
     on train_df ONLY; drop last train row's label; freeze set, confirm on val.
3. **Rl_v50.py is UNRUN and could NOT be pandas-smoke-tested here** (this research env
   has no pandas/torch/sb3). Causality holds BY CONSTRUCTION (pandas rolling is
   trailing/right-aligned; _rank_last compares current only to w[:-1]). A run-routine
   should still pandas-smoke-test the helper (causality drift ~0, no NaN, output in
   [-1,1]) before a full panel run, and confirm rolling.apply speed is acceptable
   (~98 cols x 2500 rows x W=253 python-callback rolling is slow; may need a
   vectorized rank if too slow — note for whoever runs it).
4. The signal ceiling is still THE problem. Keep pushing run-routines toward v24/v45
   POOLED + exogenous/cross-sectional features (v51) over more reward/hyperparam forks.

## Do NOT re-propose (rejected list, CLAUDE.md)
DSR reward, weight/L2 regularization, deepening-only DD, 1M timesteps,
min-val-trades=5, B&H-relative reward (v19 is UNRUN not rejected). v49's BC warm-start
must stay a warm-START only (no persistent KL anchor — that = the rejected reg class).

## Gotchas
- v18 anchors: prepare_data_for_finrl ~line 286 (scaling block ~336-353); process_stock
  ~line 1224 (split wiring ~1296-1316); ValidationCallback ~586; policy_kwargs ~772.
- run_panel.py does importlib.import_module(f"Rl_{ver}") — `python run_panel.py v50`
  runs it with no registration needed.
- test_indicator_audit.py uses an EXPLICIT version list (v8-v24,v26); adding v50 does
  NOT break it, and v50 doesn't change list_of_indicators anyway. v47/v51 DO change
  the feature set -> they must pass test_indicator_causality.py and NOT introduce a
  known-leakage name (audit test).
- Never edit frozen files (v6-v26 baselines; v27-v45 drafts effectively frozen).
  Only ADD new vNN.
- Lease: autoresearch/.lease-research — DELETE on clean end, commit+push.
