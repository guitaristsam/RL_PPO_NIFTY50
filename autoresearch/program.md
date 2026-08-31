# program.md — autoresearch operating instructions

You are an autonomous research agent. Your job: improve the PPO trading policy by
editing **one file**, `autoresearch/train.py`, running it, and keeping changes
that improve a single metric. This file (`program.md`) is your standing brief —
re-read it at the start of every session. The pattern is adapted from
[karpathy/autoresearch](https://github.com/karpathy/autoresearch).

## The loop

1. Read `train.py` and the top of `log.md` (the leaderboard — current best metric
   and what produced it). Read `CLAUDE.md` at the repo root once for project
   context and the list of already-tried-and-rejected ideas.
2. Form ONE hypothesis. Change exactly **one variable** in the AGENT-EDITABLE
   block of `train.py` (or, for reward/architecture ideas, one localized change).
   Single-variable discipline is mandatory — see CLAUDE.md "Process notes". Two
   simultaneous changes that offset each other is the classic failure here.
3. Run it: `python train.py`. It trains on a 3-stock panel and prints a final
   line: `METRIC mean_val_outperf_pp=<x> mean_test_outperf_pp=<y>`.
4. Decide keep or discard:
   - **Keep** only if `mean_val_outperf_pp` beats the current leaderboard best by
     a **margin of at least +3.0 pp** (noise gate — a smaller gain is likely
     seed/slice noise, not signal). On keep: `git add -A && git commit` with the
     metric in the message, and prepend a row to `log.md`.
   - **Discard** otherwise: `git checkout -- autoresearch/train.py` to revert, and
     still append a one-line row to `log.md` (negative results are data — they
     stop you and others re-trying the same thing).
5. Repeat until the session ends. Each experiment is one commit, so `git log` is
   the full experiment history.

## Hard rules (do not violate)

- **Never edit `Rl_v18.py` or any frozen file** (`Rl_v6..v24`, `v26`, the helper
  scripts). Only `train.py`, `log.md`, and new files under `autoresearch/`.
- **Indicators: remove or reorder only, never add.** Every name in the audited
  `INDICATORS` list has passed `test_indicator_causality.py`. Adding an unaudited
  name can leak future information and silently inflate the metric — the most
  dangerous failure mode, because it looks like a huge win. If you change
  `INDICATORS`, run `python test_indicator_causality.py` from the repo root as a
  gate before trusting the result; if it fails, revert immediately.
- **Never select on the test number.** `mean_test_outperf_pp` is REPORT-ONLY. Use
  it only as a red flag: if val improves a lot but test does not (or moves the
  other way), the change is overfitting the proxy — discard it and note why.
- **Keep the metric line intact.** Do not remove or rename the `METRIC ...` print;
  the harness and your keep/discard decision depend on parsing it.

## What this metric is and is NOT

The proxy trains at a reduced budget on a 3-stock panel and evaluates the
*final* checkpoint. Production (`run_panel.py`) trains 200k steps on 10 stocks and
early-stops on the best validation checkpoint. So this is a **cheap directional
screen, not a verdict.** A proxy win is a *candidate*, not a confirmed
improvement. When a change clears the margin gate AND holds up on the test column:
append it to `autoresearch/CANDIDATES.md` (create if absent) with the metric and
the one-line change description. The nightly panel-run routines read that file and
validate top candidates on the full 10-stock panel. Do not claim a variant
"works" from the proxy alone.

## Ideas worth trying (not exhaustive — invent your own)

The documented pathology is a train/test generalization gap: critic explained
variance pegs at 0.95-0.99 while test underperforms; val curves peak ~100k then
decay. Levers that attack that, and are single-variable here:
- Prune `INDICATORS` (fewer features = less to overfit; this is v26's thesis).
- Raise `ent_coef` (more exploration / less premature policy collapse).
- Shrink the policy (`lstm_hidden_size`, `net_arch`) — smaller model, less overfit.
- Lower `BUDGET_TIMESTEPS` (earlier stop) or study the metric vs budget curve.
- `n_steps` / `batch_size` / `n_epochs` (gradient noise scale).

Already tried and REJECTED in this project (do NOT re-propose without a
materially different mechanism — see CLAUDE.md): DSR reward, added regularization,
deepening-only drawdown penalty, 1M timesteps, min-val-trades filter, B&H-relative
reward.

## Frontier (chase the current best, don't re-fork from a stale baseline)

`autoresearch/FRONTIER.md` is the shared board all four nightly routines read.
- At **session start**, read it. Your baseline is the current proxy CHAMPION, not
  necessarily v18 — if a previous session's kept change is the head of `log.md`,
  `train.py` already reflects it; keep building single-variable changes *from that*.
- When you set a new proxy best, update the "CHAMPION — fast proxy" row in
  FRONTIER.md and push, so the run/research routines know what leads.
- When you flag a CANDIDATES.md winner, also add it to FRONTIER.md's
  "CANDIDATES pending" list so a run routine validates it before its fixed queue.
- **You are the sole writer of FRONTIER.md** (avoids multi-routine conflicts). At
  session start, reconcile the full-panel CHAMPION section: `git fetch --all`, scan
  the other routines' latest readouts for a new champion —
  `git show origin/auto/run-a:results_*/READOUT.md` and same for `origin/auto/run-b`
  (look for a "NEW CHAMPION" line naming a variant that beats the current panel
  row) — and if one beats the current champion, update the CHAMPION panel row and
  push. This is how a win discovered by a run routine propagates to everyone.

## Advisor (session boundaries only)

The local `advisor` tool is not available in this environment. Per the global
fallback, spawn an **independent Opus sub-agent as advisor** using the `Task` tool
— but only at two points, NOT per experiment (per-experiment calls are wasteful
and the metric is the real arbiter):
- **Session start**, before choosing which class of change to explore tonight:
  forward your plan and the current leaderboard, ask for the highest-value
  direction and traps to avoid.
- **Before opening/updating the PR**, to sanity-check that the committed winners
  are real (margin cleared, test column consistent, no leakage) and not artifacts.

## Session bookkeeping

- Work only on branch `auto/tinker`. Push after every few experiments so progress
  survives a session cut-off (state lives in git, not the session).
- `.ta_cache/` and `models/` are gitignored — do not commit them.
- Do not stop early; keep generating and screening distinct ideas until the
  environment ends the session. When you have committed winners, open or update a
  PR to `main` titled `auto-tinker: proxy experiment results` summarizing the
  leaderboard movement and any CANDIDATES.md additions.
