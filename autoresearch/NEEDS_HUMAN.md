# NEEDS_HUMAN — items requiring human attention

Entries appended by nightly routines. Human should review, act, and mark resolved.
auto-tinker consolidates this file across branches.

---

## [OPEN] 2026-09-05 — v18 Baseline Integrity Issue (run-b)

**Severity: HIGH — retroactively invalidates all experiment rejections**

**Finding:** The `results/` directory (used as the v18 baseline) appears to contain
pre-vecnorm-fix data for 9/10 stocks. The vecnorm fix (`91e620d`, 2026-06-11) reportedly
only re-ran RELIANCE. All experiments (v19/v20/v21) were compared against this biased baseline.

**Evidence from clean v18 re-run (results_v18/, 2026-09-05):**

| Stock | Old baseline (results/) | Fresh v18 (results_v18/) | Change |
|-------|------------------------|--------------------------|--------|
| RELIANCE | -41.47pp | -76.93pp | **-35pp worse** |
| INFY | -61.90pp | -39.50pp | +22pp better |
| ITC | **+40.10pp (B&H win!)** | **-65.99pp** | **-106pp — NOT a B&H win** |
| ADANIENT | +66.83pp | +4.12pp | -63pp (still beats B&H weakly) |

**ITC's +40.10pp result — the primary "PPO beats B&H" achievement cited in CLAUDE.md —
does NOT reproduce with current post-fix code.**

**Action needed:**
1. Confirm whether the 10-stock results in `results/` are pre-fix (check git blame on those files vs commit 91e620d).
2. Once v18 clean panel completes (results_v18/ on auto/run-b), verify the correct baseline.
3. Update CLAUDE.md and FRONTIER.md to reflect correct baseline numbers.
4. Re-evaluate the project's progress claim (currently "2 stocks beat B&H" — may be 1 or 0 with correct code).

**Status:** v18 clean panel running (auto/run-b, 2026-09-05). Will post complete results when done.

---

## [OPEN] 2026-09-05 — v27 Design Proposal (run-b, via Opus advisor)

**Severity: LOW — enhancement opportunity**

**Proposal:** v27 = v18 + turnover penalty in the reward function.

**Evidence from advisor analysis:**
- Mean cost drag across 10 stocks: ~20.1% of log-equity (~4.5%/yr on average)
- INFY: 43.8% cost drag, SBIN: 32.3% cost drag
- Gross-of-cost, 5/10 stocks would beat B&H (vs 2/10 net)
- Transaction costs account for ~26pp of the 38.8pp mean underperformance gap

**Proposed implementation:**
```python
# In IntegerTradingEnv.step() after computing primary reward:
traded_value = abs(action_shares) * price
reward -= lambda_tc * (traded_value / self.asset_memory[-1])
# Suggested lambda_tc: 0.1 to 1.0 (tune via proxy panel)
```

**Single-variable from v18**: only the reward calculation changes.
**Expected effect**: fewer trades, lower cost drag, possibly 5+/10 stocks beating B&H gross.

**Action needed:** Have auto-tinker prototype this on proxy panel, or implement Rl_v27.py.
