# NEEDS_HUMAN — items requiring human attention

Entries appended by nightly routines. Human should review, act, and mark resolved.
auto-tinker consolidates this file across branches.

---

## [OPEN] 2026-09-05 — v18 Baseline Integrity Issue (run-b) — HIGH SEVERITY

**The ITC +40pp "PPO beats B&H" achievement does NOT reproduce with current code.**

All experiment comparisons (v19/v20/v21) were against pre-vecnorm-fix data for 9/10 stocks.
The correct v18 mean outperformance is **-72.74pp** (not -38.78pp). See `results_v18/READOUT.md`
on auto/run-b for full details.

**Corrected comparison:**
- v19/v20/v21 all fall within ±1.2pp of v18 clean → none were genuine losses
- ADANIENT is the only genuine B&H-beater (+4.12pp, B&H period was -21%)
- TATAMOTORS degenerate (5 trades) and HINDALCO dominate the mean due to 150-250% B&H returns

**Action needed:**
1. Update CLAUDE.md: correct v18 baseline from -38.78pp → -72.74pp, correct "2 stocks beat B&H" → "1 stock (ADANIENT, +4pp)"
2. Update FRONTIER.md: v18 champion entry correct mean outperf
3. Review whether the project should still claim "second PPO-beats-B&H stock (ADANIENT +66.8pp, Sharpe 0.64)" — the fresh run shows +4.12pp, not +66.8pp

---

## [OPEN] 2026-09-05 — Metric Problem: Mean Outperf is Noisy (run-b, Opus advisor)

**Use log terminal-equity ratio and median, not mean pp-outperformance.**

Arithmetic mean pp-outperformance is incomparable across stocks with different compounding.
TATAMOTORS -257.93pp and HINDALCO -200.74pp dominate the mean; on log ratio they are
less extreme. Advisor recommends:
- Add `log(PPO_final / BH_final)` to `summarize_results.py`
- Report median outperformance alongside mean

**Action needed:** Update `summarize_results.py` to add log-ratio column.

---

## [OPEN] 2026-09-05 — Next Experiment Design: v27 "Start Fully Invested" (Opus advisor)

**Proposed v27:** Modify `IntegerTradingEnv` so the initial state is fully invested
(buy max shares at t=0) instead of holding cash. Single-variable change from v18.

**Rationale:** The policy is chronically under-exposed (near-zero beta). On bull markets,
"do nothing" in cash scores -258pp (TATAMOTORS). If "do nothing" instead means hold shares
(= B&H), the degenerate policy scores 0pp and the policy must earn deviations from B&H.
This attacks the root cause (beta gap) without changing reward or architecture.

**Implementation:**
```python
# In IntegerTradingEnv.reset():
# After super().reset(), buy max shares with available cash:
initial_price = self.data.close.values[0]
initial_shares = int(self.initial_amount // initial_price)
initial_cost = initial_shares * initial_price * (1 + self.buy_cost_pct)
if initial_cost <= self.state[0]:
    self.state[1 + self.stock_dim] = initial_shares
    self.state[0] -= initial_cost
```

**Action needed:** Implement Rl_v27.py as single-variable fork of v18 + this change.
Validate on proxy panel (auto-tinker) then full panel (auto-run).

---

## [OPEN] 2026-09-06 — Cost Drag Confirmed as Root Cause (run-b, Opus advisor)

**Transaction costs are 15.2% of initial capital on average across the 10-stock panel.**

Per-stock breakdown from `results_v18/*/trades.csv`:
| Stock | Trades | Cost/Initial |
|-------|--------|-------------|
| ITC | 129 | 31.4% |
| RELIANCE | 139 | 27.5% |
| SBIN | 98 | 20.3% |
| HINDALCO | 181 | 16.1% |
| AXISBANK | 69 | 14.1% |
| TCS | 64 | 13.3% |
| HDFCBANK | 46 | 10.9% |
| INFY | 59 | 9.3% |
| ADANIENT | 53 | 7.9% |
| TATAMOTORS | 5 | 1.0% |
| **Mean** | **84** | **15.2%** |

Win rates are 56-87% per stock but returns are near-zero. Costs alone explain ITC's
entire −66pp gap. The advisor (Opus, 2026-09-06) assessment: **cost drag is the binding constraint,
not reward shaping or overfit.**

**Corrected v27 recommendation (SUPERSEDES "start fully invested"):**
Advisor says start-fully-invested only sets t=0; the policy sells down by day 3 — it
attacks the symptom, not the cause. Real fix:

**v27 = action deadband + minimum hold:**
- `|action_shares| < 0.1*hmax → 0` (no trade if tiny)  
- minimum-hold: skip trade if position changed < 3 bars ago
- This directly cuts turnover by 50-70%, saving ~8-10pp of cost drag

**v28 = turnover penalty in reward:** `reward -= λ * cost_t / eq_t`

**Action needed:**
1. Implement `Rl_v27.py` with action deadband + minimum-hold (single-variable from v18)
2. Validate proxy panel (auto-tinker) then full panel (auto-run)
3. Update `NEEDS_HUMAN.md [OPEN] 2026-09-05 v27` as superseded

---

## [SUPERSEDED — 2026-09-06] 2026-09-05 — Next Experiment Design: v27 "Start Fully Invested"

**Superseded by action deadband recommendation above.** "Start fully invested" was
advisor's first proposal but is now assessed as attacking t=0 only (policy sells down
by day 3). Action deadband directly attacks the 15pp ongoing cost drag.

---

## [RESOLVED — informational] 2026-09-05 — v27 Turnover Penalty (SUPERSEDED)

Original proposal: `reward -= λ * (traded_value / equity)`. Superseded by advisor
recommendation to instead fix the starting-position problem. Turnover penalty reduces
trading further, pushing toward cash (wrong direction for beta gap problem).

**2026-09-06 UPDATE:** New advisor says turnover penalty in reward IS worth trying
as v28 (after v27 action deadband). Reward penalty changes the objective; deadband
changes the action space. Both are worth trying, deadband first.
