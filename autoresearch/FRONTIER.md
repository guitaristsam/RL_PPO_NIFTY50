# FRONTIER — shared state for all nightly routines

Single source of truth for "what is currently best" and "what to try next". Every
routine (auto-run-A/B, auto-research, auto-tinker) reads this at session start and
updates it on a win. It lives on branch `auto/tinker`; other routines read it with
`git fetch origin auto/tinker && git show origin/auto/tinker:autoresearch/FRONTIER.md`
— no merge to main required.

**Ratchet rule:** when any routine establishes a result that beats the current
champion (on the metric that section names), it MUST update the relevant section
here and push, so the next session/routine builds on the new best instead of the
old baseline. Chase the frontier; do not keep re-forking from a superseded config.

---

## DURABILITY CONTRACT — read every session (all four routines)

This system is meant to run forever with zero human interference. Obey these:

1. **Never block on a human.** Do not wait for a merge, an approval, or an answer.
   Everything you need is on the branches (read via `git fetch` / `git show
   origin/<branch>:<path>` — no merge to `main` is ever required to coordinate).
2. **`main` is not the source of truth — this FRONTIER is.** The CHAMPION sections
   here are the living baseline. Fork new work from the champion, not from whatever
   `main`/CLAUDE.md says (that is historical). A confirmed champion does NOT need to
   be merged to `main` to be built upon.
3. **If something ACTUALLY needs the human, write it, don't wait.** Append a dated
   entry to `autoresearch/NEEDS_HUMAN.md` (auth failures, infra that blocks all
   progress, real-world-consequence decisions, or a request to bless a champion
   into production). Then immediately continue with the next best autonomous
   action. Never let a human-needed item stall the night.
4. **Self-heal, don't crash the night.** If a task fails, retry once; if it still
   fails, log it (one line in NEEDS_HUMAN.md only if it blocks *all* progress,
   otherwise a note in your READOUT/log) and move to the next best action. A single
   broken variant or stock must not stop the rest of the work.
5. **The loop is open-ended.** When the queue and candidates are exhausted, keep
   generating value: tinker invents new single-variable changes, research proposes
   new forks from the champion, run routines validate them and expand the panel.
   There is always a next best action — take it.
6. **Handoff checkpoint (resume cold every fire) — YOUR OWN FILE ONLY.** Each cloud
   fire is a fresh session with no memory of the last one. Each routine keeps its
   OWN distinctly-named handoff doc so no agent ever reads or overwrites another's:
   - auto-run-A → `autoresearch/HANDOFF.run-a.md`
   - auto-run-B → `autoresearch/HANDOFF.run-b.md`
   - auto-research → `autoresearch/HANDOFF.research.md`
   - auto-tinker → `autoresearch/HANDOFF.tinker.md`

   (Template: `autoresearch/HANDOFF.template.md`.) Rules:
   - **Read ONLY your own handoff file at session start**, FIRST, before picking an
     action — to recover what your previous session was mid-way through (which
     variant/experiment, which stock, next step, gotchas). Do NOT read or write any
     other routine's HANDOFF file; those are private to each agent so one never
     influences another. (Cross-routine coordination happens ONLY through the
     explicit shared surfaces: FRONTIER champion rows, CANDIDATES, READOUT
     `NEW CHAMPION` lines, NEEDS_HUMAN — never through handoffs.)
   - **Write ONLY your own handoff file**, as you go and again right before the
     session ends (do it early/often — a session can be cut off without warning):
     current task, exact progress (e.g. "v26 panel: 6/10 done, HDFCBANK next"), the
     immediate next step, and anything the next session must not re-do. Commit +
     push it with your other progress. Required, not optional.
   - auto-tinker's NEEDS_HUMAN/FRONTIER consolidation does NOT touch any HANDOFF
     file — handoffs are excluded from all cross-branch reconciliation.
7. **STOP kill-switch (check FIRST, every session).** Before doing anything, check
   for a stop flag: `git fetch origin auto/tinker && git show origin/auto/tinker:autoresearch/STOP 2>/dev/null`.
   If that file exists, **exit immediately** without running. This is how the human
   pauses the whole swarm without deleting the cron routines (they just create/delete
   `autoresearch/STOP` on `auto/tinker`).
8. **Overlap lease (avoid two sessions on one branch).** Both nightly waves (2:30
   and 4:30 IST) can fire while a prior session on your branch is still running.
   The AUTHORITATIVE mutex is the push: a concurrent push rejected non-fast-forward
   means another session is live — if that happens, **exit and let it continue, do
   not retry/fight the branch**. The lease below is only an early-out so the second
   wave doesn't waste a whole session before hitting that rejection.
   - At session start, `git fetch origin <your-branch>` and read
     `autoresearch/.lease-<routine>` from it. If it exists AND its timestamp is
     **< 2.5 h old**, another session is likely active — exit immediately. A stale
     lease (>2.5 h, i.e. a crashed session) is overridden.
   - Otherwise write `autoresearch/.lease-<routine>` with the current UTC time,
     commit+push, proceed, and refresh it as you work.
   - **On clean session end, DELETE `autoresearch/.lease-<routine>`, commit+push.**
     This is required: without release, a wave-1 session that finishes at ~3:15
     leaves a ~1.25 h-old lease and the 4:30 wave-2 fire would wrongly exit,
     silently halving nightly throughput. The 2.5 h staleness override is ONLY the
     crash-recovery path, not the normal release mechanism.
9. **Keep branches lean (unattended for weeks).** `models_*/` and `.ta_cache/` are
   already gitignored. Also avoid committing bulky per-stock CSVs
   (`account_value.csv`, `trades.csv`, `actions.csv`) if the branch is growing large
   — the coordination surfaces only need the `*_report.txt` and `READOUT.md`. If a
   push is rejected for size, gitignore the bulky artifacts on your branch and keep
   only reports + READMEs.

**Staleness note (S2):** a champion that auto-tinker sets *tonight* is reconciled
into FRONTIER during tinker's session; the run/research routines that read FRONTIER
at the start of the *same* night see the previous state (one-cycle lag). This is
expected — they pick it up next fire. Do not treat a one-night lag as a bug.

**auto-tinker also consolidates NEEDS_HUMAN.md**: at session start, in addition to
reconciling the CHAMPION rows, scan the other branches' `NEEDS_HUMAN.md` for open
entries (`git show origin/auto/run-a:autoresearch/NEEDS_HUMAN.md` etc.), merge any
into the authoritative copy on `auto/tinker`, and push — so the human has ONE inbox
to check.

---

## CHAMPION — full 10-stock panel (production truth)

The best *confirmed* variant on the full panel, measured as mean outperformance
vs buy-and-hold. This is what new production variants must beat.

| variant | mean outperf vs B&H | beats-B&H count | notes |
|---|---|---|---|
| **v18 (baseline)** | −63.2pp | 1/10 | **PRODUCTION CHAMPION** — genuine policies, see CLAUDE.md |
| ~~v26 (bookkeeping)~~ | −51.49pp | 2/10 | ⚠️ ARTIFACT: both B&H-beats are degenerate cash-holds (ADANIENT 0 trades, HDFCBANK 5 trades). ITC −101pp regression. **Do NOT build on v26.** See results_v26/READOUT.md on auto/run-a. 2026-09-02. |

> v26 takes the ratchet on raw mean outperf but is flagged as an inactivity artifact by run-A.
> v18 remains the production champion for the purpose of building new variants.
> Next production challenger needs to beat v18 with GENUINE active policies (≥20 trades/stock).

**Invalidated proxy win:** The auto-tinker 22-indicator proxy champion (-7.855pp) is the same
degenerate artifact. TATAMOTORS val cash-hold produces artificial +177pp; removing that stock's
contribution, the proxy panel is genuinely losing. Proxy experiments on the v26 22-indicator
baseline are unreliable directional screens. Consider reverting proxy to v18 106 indicators.

## CHAMPION — fast proxy (autoresearch screen)

Best `mean_val_outperf_pp` on the 3-stock proxy panel. Set by auto-tinker; this is
the leaderboard head from `log.md`, surfaced here for the other routines.

| config | mean_val_outperf_pp | test | source commit |
|---|---|---|---|
| **22-indicator v26 curated (from AUDITED list), all other params at v18 defaults** | **-7.855** | -51.637 | 9c74acb (2026-09-01) |
| v18 defaults (106 indicators) | -75.552 | -96.192 | — |

---

## NEXT ACTIONS — ranked (highest expected value first)

Any routine may add/reorder. Pick the top item you are equipped to run. When you
finish one, strike it through and record the outcome (win → update a CHAMPION
section; loss → note it so nobody retries it).

~~0. (tinker, FIRST NIGHT ONLY) Calibrate the metric noise floor.~~ **DONE 2026-09-01. Gate=60.4pp.**
~~1. (run) Validate v26 on full panel.~~ **DONE 2026-09-01/02 by run-A. v26 = BOOKKEEPING ARTIFACT. See results_v26/READOUT.md on auto/run-a.**
2. (tinker) **Panel recalibration — HIGH PRIORITY.** Swap TATAMOTORS→ITC. The current 3-stock panel is broken: TATAMOTORS seed=42 val is a degenerate cash-hold (+177pp), making any result on this panel suspect. New panel: STOCKS=["RELIANCE","ITC","HDFCBANK"]. Requires 3-seed recalibration. Current proxy experiments are directional only, not trustworthy.
3. (tinker) After recalibration: n_epochs 5→3 (advisor top pick), then n_steps=256 + gamma=0.95 combo.
4. (run) Validate v19 (B&H-relative reward) on full panel — v26 READOUT explicitly recommends this as next lever. Auto-research also proposed v27–v34 forks from v26 (reward/architecture changes). Avoid feature-reduction forks — they are now invalidated by v26 panel results.
5. (research) Propose next variant fork from v18 baseline (NOT v26): reward shape (v19-style alpha-relative), or architectural change that improves generalization without reducing features.

## CANDIDATES pending full-panel validation

Proxy winners from auto-tinker awaiting confirmation. Run routines: validate the
top candidate before the fixed queue. (auto-tinker appends here via CANDIDATES.md;
this list mirrors the highest-priority ones.)

_none yet_
