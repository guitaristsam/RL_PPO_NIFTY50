# autoresearch/ — autonomous experiment loop

An overnight agent that tinkers with the PPO trading policy on its own: change one
thing, train a fast proxy, keep it only if a single metric improves, repeat.

Adapted from **[karpathy/autoresearch](https://github.com/karpathy/autoresearch)**
(MIT). We use the *pattern*, not the code — karpathy's `train.py` is a nanochat
GPT that needs an NVIDIA H100 and has nothing to do with trading. What carries
over is the harness philosophy:

| karpathy/autoresearch | this adaptation |
|---|---|
| agent edits one `train.py` (a GPT) | agent edits one `train.py` (a PPO trading experiment) |
| fixed 5-min wall-clock budget | fixed **timestep** budget (deterministic across cloud CPUs) |
| metric `val_bpb` (lower better) | metric `mean_val_outperf_pp` vs buy-and-hold (higher better) |
| `program.md` is the agent brief | same |
| keep/discard by metric, git = log | same, plus a `log.md` leaderboard |

## Files

- `train.py` — the only file the agent edits. Self-contained fast experiment that
  reuses the leak-audited plumbing from the frozen `Rl_v18.py` baseline (indicator
  computation, NaN handling, RobustScaler, integer trading env, buy-and-hold) so
  results stay comparable to production. Editable knobs are fenced in an
  `AGENT-EDITABLE BLOCK`.
- `program.md` — the agent's standing instructions and hard rules. Read this first.
- `log.md` — experiment leaderboard (newest first). One row per experiment.
- `CANDIDATES.md` — proxy winners flagged for full 10-stock panel validation by
  the nightly `run_panel.py` routines.
- `.ta_cache/` — cached pandas-ta output per stock (gitignored; the slow step).

## Run one experiment manually

```bash
cd autoresearch
python train.py
# ... trains a 3-stock panel at reduced budget, prints:
# METRIC mean_val_outperf_pp=<x> mean_test_outperf_pp=<y>
```

First run per stock computes ~300 indicators and caches them to `.ta_cache/`;
later runs load the cache.

## What the metric is (and is not)

`mean_val_outperf_pp` is the mean, over a 3-stock panel (RELIANCE, TATAMOTORS,
HDFCBANK), of `PPO validation return − buy-and-hold validation return`. It is a
**cheap directional screen**, deliberately cheaper than production: reduced
timesteps, 3 stocks not 10, and it scores the *final* checkpoint whereas
production early-stops on the best validation checkpoint. So a proxy win is a
**candidate**, never a verdict — it must be re-run on the full panel before any
claim. `mean_test_outperf_pp` is printed alongside as a REPORT-ONLY overfit check;
never optimize against it.
