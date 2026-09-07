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

### [OPEN] 2026-09-05 — v18 Baseline Integrity Issue (run-b) — HIGH SEVERITY

**The ITC +40pp "PPO beats B&H" achievement does NOT reproduce with current code.**

All experiment comparisons (v19/v20/v21) were against pre-vecnorm-fix data for 9/10 stocks.
The correct v18 mean outperformance is **-72.74pp** (not -38.78pp, not -63.2pp).
See `results_v18/READOUT.md` on auto/run-b for full stock-level details.

**Corrected stock results:**
| Stock | Outperf | Trades | B&H |
|-------|---------|--------|-----|
| RELIANCE | -76.93pp | 139 | +68.70% |
| INFY | -39.50pp | 59 | +22.50% |
| TATAMOTORS | -257.93pp | 5 (DEGEN) | +250.97% |
| ITC | -65.99pp | 129 | +105.88% |
| ADANIENT | +4.12pp | 53 | -21.61% |
| HDFCBANK | -15.91pp | 46 | +30.62% |
| TCS | -5.35pp | 64 | +4.96% |
| SBIN | -44.39pp | 98 | +88.72% |
| AXISBANK | -24.74pp | 69 | +51.62% |
| HINDALCO | -200.74pp | 181 | +178.12% |
| **Mean** | **-72.74pp** | 84.3 | +98.04% |

**Corrected comparison:**
- v19/v20/v21 all fall within ±1.2pp of v18 clean → none were genuine losses
- ADANIENT is the only genuine B&H-beater (+4.12pp, B&H period was -21%)

**Action needed from human:**
1. Update CLAUDE.md: correct v18 baseline from -63.2pp → -72.74pp
2. Update CLAUDE.md: correct "2nd PPO-beats-B&H stock (ADANIENT +66.8pp)" → "+4.12pp"
3. Decide whether to revise the project README/narrative given that ITC +40pp doesn't reproduce
Source: auto-run-B (2026-09-05)

---

### [OPEN] 2026-09-05 — Metric Noise: Recommend log-ratio + median in summarize_results.py (run-b, Opus advisor)

**Arithmetic mean pp-outperformance is incomparable across stocks with different compounding.**
TATAMOTORS -257.93pp and HINDALCO -200.74pp dominate the mean. Advisor recommends:
- Add `log(PPO_final / BH_final)` column to `summarize_results.py`
- Report median outperformance alongside mean

This is a low-priority code change (no experiment impact), but improves interpretability.
**Action needed:** Update `summarize_results.py` to add log-ratio and median columns.
Source: auto-run-B (2026-09-05)

---

### [OPEN] 2026-09-05 — v27 "Start Fully Invested" proposal (run-b, Opus advisor)

**Proposed v27:** Modify `IntegerTradingEnv` so the initial state is fully invested
(buy max shares at t=0) instead of holding cash. Single-variable change from v18.

**Rationale:** The policy is chronically under-exposed (near-zero beta). On bull markets,
"do nothing" in cash scores -258pp (TATAMOTORS). If "do nothing" means hold shares (= B&H),
the degenerate policy scores 0pp and the policy must earn deviations from B&H.
This attacks the root cause (beta gap) without changing reward or architecture.

**Implementation (in IntegerTradingEnv.reset()):**
```python
initial_price = self.data.close.values[0]
initial_shares = int(self.initial_amount // initial_price)
initial_cost = initial_shares * initial_price * (1 + self.buy_cost_pct)
if initial_cost <= self.state[0]:
    self.state[1 + self.stock_dim] = initial_shares
    self.state[0] -= initial_cost
```

Source: auto-run-B (2026-09-05). Opus advisor endorsed over turnover penalty (v27-turnover superseded).

---

## Resolved

_(move entries here once addressed)_

### [RESOLVED — auto-tinker 2026-09-06] FRONTIER v18 baseline correction

FRONTIER.md now corrected to -72.74pp (was -63.2pp), 1/10 beats B&H (ADANIENT only).
Source: auto-run-A/B (2026-09-04 to 2026-09-05). Handled autonomously.
