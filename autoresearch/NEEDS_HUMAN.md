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

## [RESOLVED — informational] 2026-09-05 — v27 Turnover Penalty (SUPERSEDED)

Original proposal: `reward -= λ * (traded_value / equity)`. Superseded by advisor
recommendation to instead fix the starting-position problem. Turnover penalty reduces
trading further, pushing toward cash (wrong direction for beta gap problem).
