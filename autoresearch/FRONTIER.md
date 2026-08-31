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
| **v18 (baseline)** | −63.2pp | 1/10 | current champion; see CLAUDE.md v18 panel table |

> Update when a run routine's readout shows a variant with a better mean outperf
> (and ideally more beats-B&H) than the row above. Move the winner to the top and
> note the date + results dir.

## CHAMPION — fast proxy (autoresearch screen)

Best `mean_val_outperf_pp` on the 3-stock proxy panel. Set by auto-tinker; this is
the leaderboard head from `log.md`, surfaced here for the other routines.

| config | mean_val_outperf_pp | test | source commit |
|---|---|---|---|
| v18 defaults | _first run establishes_ | _—_ | — |

---

## NEXT ACTIONS — ranked (highest expected value first)

Any routine may add/reorder. Pick the top item you are equipped to run. When you
finish one, strike it through and record the outcome (win → update a CHAMPION
section; loss → note it so nobody retries it).

1. (run) Validate the next unrun queued variant on the full panel: v26, v22, v20,
   v21, v23 — but if a proxy CANDIDATE outranks these, validate that first.
2. (tinker) Screen single-variable anti-overfit changes on the proxy; promote any
   that clear the +3pp margin AND hold on the test column to CANDIDATES.md.
3. (research) Explain why the current proxy/panel champion works; propose the next
   single-variable fork *from the champion config*, not from v18, once the champion
   is no longer v18.

## CANDIDATES pending full-panel validation

Proxy winners from auto-tinker awaiting confirmation. Run routines: validate the
top candidate before the fixed queue. (auto-tinker appends here via CANDIDATES.md;
this list mirrors the highest-priority ones.)

_none yet_
