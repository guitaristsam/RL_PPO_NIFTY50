# HANDOFF — auto-run-B

Last updated: 2026-09-05T23:20:00Z

## Status: IN PROGRESS — v23 panel running (task b7n3rnsrt)

**Current task:** v23 full panel (warmup=150k, eval_freq=25k) — 0/10 complete as of 23:15 UTC

## EXPLOSIVE FINDING THIS SESSION (2026-09-05)

The "v18 baseline" used for all prior comparisons was pre-vecnorm-fix for 9/10 stocks.

**Correct v18 baseline: -72.74pp** (not -38.78pp).
**ITC +40pp does NOT reproduce** with current code (fresh run: -65.99pp).
**ADANIENT: +4pp (not +67pp)** — still beats B&H, barely.

**v19/v20/v21 were NOT losses vs correct baseline:**
- v19: -72.38pp (+0.36pp vs v18 clean)
- v20: -71.58pp (+1.16pp vs v18 clean)
- v21: -73.16pp (-0.42pp vs v18 clean)
All within ±1.2pp of correct v18 — indistinguishable.

## Tonight's Work (Session 2026-09-05)

### Completed
- [x] v20 READOUT written (results_v20/READOUT.md)
- [x] v18 clean 10-stock panel run (results_v18/) — confirmed baseline correction
- [x] NEEDS_HUMAN.md written with v18 baseline issue + v27 proposal
- [x] PR #3 updated with correct framing
- [x] Advisor (Opus) consulted — recommends v27 "start fully invested" > turnover penalty

### In Progress
- [ ] v23 panel (task b7n3rnsrt, started ~23:15 UTC) — expected ~23:15 + 150 min = ~01:45 UTC

## v18 Clean Results (for READOUT reference)

| Stock | Outperf | Sharpe | Trades | B&H Return |
|-------|---------|--------|--------|-----------|
| RELIANCE | -76.93pp | -0.102 | 139 | +68.70% |
| INFY | -39.50pp | -0.598 | 59 | +22.50% |
| TATAMOTORS | -257.93pp | -0.559 | **5 DEGEN** | +250.97% |
| ITC | -65.99pp | 0.534 | 129 | +105.88% |
| ADANIENT | +4.12pp | -0.180 | 53 | -21.61% |
| HDFCBANK | -15.91pp | 0.300 | 46 | +30.62% |
| TCS | -5.35pp | -0.010 | 64 | +4.96% |
| SBIN | -44.39pp | 0.452 | 98 | +88.72% |
| AXISBANK | -24.74pp | 0.587 | 69 | +51.62% |
| HINDALCO | -200.74pp | -0.292 | 181 | +178.12% |
| **Mean** | **-72.74pp** | +0.013 | 84.3 | +98.04% |

## v23 Completion Steps (CRITICAL for next session)

When task b7n3rnsrt completes:
1. Collect results: `for stock in RELIANCE INFY TATAMOTORS ITC ADANIENT HDFCBANK TCS SBIN AXISBANK HINDALCO; do report="results_v23/${stock}/${stock}_report.txt"; if [ -f "$report" ]; then outperf=$(grep -i "outperform" "$report" | head -1); trades=$(grep -i "total trades" "$report" | head -1); echo "$stock: $outperf | $trades"; fi; done`
2. Key diagnostic: TATAMOTORS trades count. If >20, the warmup fix worked.
3. Compare mean vs v18 clean (-72.74pp). If >0pp better with active policies, note improvement. If >5pp better with TATAMOTORS fixed, consider declaring cautious progress.
4. Write results_v23/READOUT.md
5. Commit and push all results
6. Update PR #3 with v23 results
7. Delete lease: `rm autoresearch/.lease-run-b && git add -A && git commit && git push`

## Setup Commands for Fresh Session

```bash
pip install stable-baselines3 sb3-contrib finrl gymnasium scikit-learn matplotlib tensorboard tqdm rich -q

WHL="https://files.pythonhosted.org/packages/00/c8/4ed6c9bc469bc937e0e437da78a437e320a9a001984a556463b8a00f5910/pandas_ta-0.4.67b0-py3-none-any.whl"
curl -sL "$WHL" -o /tmp/pandas_ta.whl
pip install /tmp/pandas_ta.whl --ignore-requires-python -q

python - << 'PATCH'
path = '/usr/local/lib/python3.11/dist-packages/pandas_ta/overlap/hma.py'
with open(path) as f: c = f.read()
old = '    hma.name = f"HMA{"" if mamode == "wma" else mamode[0]}_{length}"'
new = '    _mm = "" if mamode == "wma" else mamode[0]\n    hma.name = f"HMA{_mm}_{length}"'
if old in c:
    with open(path,'w') as f: f.write(c.replace(old,new))
    print('patched')
else: print('ok')
PATCH

python - << 'PATCH'
path = '/usr/local/lib/python3.11/dist-packages/finrl/__init__.py'
with open(path, 'w') as f:
    f.write("from __future__ import annotations\ntry:\n    from finrl.test import test\nexcept Exception:\n    pass\n")
print('finrl patched')
PATCH
```

## Immediate Next Step
Wait for task b7n3rnsrt notification (v23 panel complete) then write READOUT.

## Key Insights for Next Session
- Correct v18 baseline = -72.74pp
- All v19-v21 experiments are null results (±1pp of baseline)
- TATAMOTORS degeneracy is the biggest single issue (-258pp, only 5 trades)
- v27 "start fully invested" is the advisor's top recommendation (attacks beta gap)
- Use median outperformance in addition to mean for future comparisons
- FRONTIER.md needs correcting (auto-tinker's job but should be flagged)

## Advisor Recommendations (Opus, 2026-09-05)
1. v27 = v18 + initial position fully invested (not turnover penalty)
2. Add log(PPO_final/BH_final) ratio to summarize_results.py, report median
3. If v23 also flat → stop varying rewards, feature set is the constraint
