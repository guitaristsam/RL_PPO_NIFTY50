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
