# autoresearch experiment log

Newest first. One row per experiment. `mean_val_outperf_pp` is the objective
(higher is better); `test` is report-only. Keep a change only if val beats the
current best by ≥ +3.0 pp (noise gate). See `program.md`.

| # | date (UTC) | change (one variable) | mean_val_outperf_pp | test | kept? | commit |
|---|---|---|---|---|---|---|
| 0 | — | baseline (v18 indicators + hyperparams, BUDGET=60k, panel=RELIANCE/TATAMOTORS/HDFCBANK) | _run to establish_ | _—_ | baseline | — |

> The baseline row's metric is established by the first `python train.py` run with
> the file unmodified. Every later experiment is judged against the best value
> above it.
