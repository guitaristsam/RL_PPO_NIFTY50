# NEEDS_HUMAN — the only file the human must ever check

This is the system's outbox to Sam. The nightly routines run fully autonomously
and never block waiting on a human. If (and only if) something *genuinely* needs
human action — one they cannot do for themselves — a routine appends a dated entry
here and then keeps working on the next best autonomous action.

**If this file has no open entries, there is nothing for you to do.** The swarm is
self-sustaining: it forks from the current champion in FRONTIER.md, screens new
ideas, validates winners, and ratchets — indefinitely.

What counts as ACTUALLY needing a human (append here): a credential/auth failure
the agent can't fix, a repeated infra error blocking all progress, a decision with
real external consequences (e.g. spending money, deleting data), or an explicit
request to bless a confirmed champion into production `main`/CLAUDE.md. What does
NOT belong here: normal experiment losses, a variant underperforming, routine
progress updates — those go in log.md / READOUTs.

Format: `- [YYYY-MM-DD] [routine] <what is needed> — <why> — <what the swarm did instead>`

---

## Open

_none — nothing needed from you._

## Resolved

_(move entries here once addressed)_
