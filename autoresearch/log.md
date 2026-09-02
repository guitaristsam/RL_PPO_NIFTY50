# autoresearch experiment log

Newest first. One row per experiment. `mean_val_outperf_pp` is the objective
(higher is better); `test` is report-only. Keep a change only if val beats the
current best by ≥ +**60.4 pp** (calibrated gate). See `program.md`.

## Noise gate recalibration (2026-09-02) — RELIANCE/ITC/HDFCBANK panel

TATAMOTORS panel invalidated (degenerate cash-hold artifact). Switching to ITC panel.
Calibration still in progress (seeds 43/44 running):

| seed | RELIANCE+ITC sum | HDFCBANK val | mean_val_outperf_pp |
|---|---|---|---|
| 42 | +5.67pp (RELIANCE+ITC together) | -33.25pp | **-9.194** |
| 43 | TBD | TBD | TBD |
| 44 | TBD | TBD | TBD |

New gate = max(3.0pp, 2 × stdev of seeds 42/43/44) — TBD when all seeds complete.

---

## Noise gate calibration (2026-09-01)

Baseline (v18 defaults, BUDGET=60k, panel=RELIANCE/TATAMOTORS/HDFCBANK) at three seeds:

| seed | RELIANCE val | TATAMOTORS val | HDFCBANK val | mean_val_outperf_pp |
|---|---|---|---|---|
| 42 | -250.23pp | +177.13pp | -153.55pp | **-75.552** |
| 43 | -249.18pp | -13.26pp | -139.97pp | -134.135 |
| 44 | -244.26pp | -10.74pp | -96.85pp | -117.284 |

- stdev([-75.55, -134.14, -117.28]) = 30.2pp
- **Gate = max(3.0pp, 2 × 30.2pp) = 60.4pp**
- Baseline (SEED=42) = **-75.552pp** → must beat **-15.2pp** to keep

Note: TATAMOTORS seed=42 has +177pp val due to B&H=-55.75% (bear market in val period);
likely a degenerate cash-hold. Seeds 43/44 show TATAMOTORS around -10 to -13pp — more realistic.
This inflates seed-42 baseline, making the gate harder to clear on the mean.

**Gate analysis:** After exp1 set a new best of -7.855pp, the remaining gate target is +52.5pp.
Analysis shows this is physically unreachable with "real" learned policies on this panel at seed=42:
TATAMOTORS max ~+15pp (can't hold all cash, B&H=-55.75%), RELIANCE max ~+10pp, HDFCBANK max ~+10pp →
achievable mean ≈ +11.7pp, far below +52.5pp threshold. The gate correctly captures that the proxy
screen is noisy — future sessions should consider recalibrating with a different panel or more seeds.

## Critical finding (2026-09-02): v26 proxy win was a degenerate artifact

auto/run-a completed v26 full 10-stock panel (2026-09-02). Mean outperf -51.49pp vs v18 -63.2pp.
Both B&H-beating stocks are degenerate cash-holds (ADANIENT 0 trades, HDFCBANK 5 trades).
ITC: +40pp (v18) → -61pp (v26), TATAMOTORS: -24pp (v18) → -149pp (v26). **v26 is NOT a win.**
The proxy champion (exp1: 22 indicators) is the same TATAMOTORS degenerate artifact.
TATAMOTORS seed=42 proxy val +177pp = holding cash while B&H loses -55.75%.
Implication: all 15 proxy experiments are unreliable — the proxy panel must be recalibrated.
Next session should swap TATAMOTORS→ITC and recalibrate gate (RELIANCE/ITC/HDFCBANK).

| # | date (UTC) | change (one variable) | mean_val_outperf_pp | test | kept? | commit |
|---|---|---|---|---|---|---|
| 15 | 2026-09-02 | n_lstm_layers 1→2 (deeper LSTM, more temporal capacity) | -59.684 | -11.684 | DISCARD (−51.8pp vs champion; advisor confirmed contraindicated — adds overfit capacity) | — |
| 14 | 2026-09-02 | gamma 0.99→0.95 (shorter time horizon, less discounting) | +5.560 | -69.932 | DISCARD (+13.4pp over champion, under gate; HDFCBANK +0.58pp — near-zero) | — |
| 13 | 2026-09-02 | BUDGET_TIMESTEPS 60k→80k (more training budget, recalibration attempt) | -8.686 | -39.935 | DISCARD (-0.8pp vs champion; 80k≈60k, gate unchanged) | — |
| 12 | 2026-09-02 | INDICATORS: trend-focused 11-set (MACD full + ADX/DMP/DMN + RSI/MOM + ATR/LOGRET) | -86.689 | -90.372 | DISCARD | — |
| 11 | 2026-09-02 | n_steps 512→1024 (longer rollouts, more LSTM context per update) | -75.125 | +26.439 | DISCARD (note: test all 3 beat B&H) | — |
| 10 | 2026-09-02 | learning_rate 3e-4→1e-4 (slower, more stable convergence) | -110.912 | -37.481 | DISCARD | — |
| 9 | 2026-09-02 | clip_range 0.2→0.1 (tighter trust region) | -89.735 | -77.055 | DISCARD | — |
| 8 | 2026-09-02 | INDICATORS: 22→6 (RSI, MACD, ATR, LOGRET, MFI, ADX only) | -47.033 | **+0.406** | DISCARD (note: test near-perfect +0.4pp, all stocks ≈B&H) | — |
| 7 | 2026-09-02 | gae_lambda 0.95→0.80 (shorter credit horizon) | -101.674 | -58.779 | DISCARD | — |
| 6 | 2026-09-01 | learning_rate 3e-4→1e-3 (faster convergence) | -96.906 | -18.717 | DISCARD | — |
| 5 | 2026-09-01 | n_steps 512→256 (more frequent policy updates) | +9.512 | -36.435 | DISCARD (best result after exp1: +17.4pp, HDFCBANK improved to +0.58pp) | — |
| 4 | 2026-09-01 | ent_coef 0.01→0.05 (more exploration entropy) | -4.778 | -68.350 | DISCARD (+3.1pp over best, under gate) | — |
| 3 | 2026-09-01 | lstm_hidden_size/net_arch 128→64 (smaller model, less capacity to overfit) | +1.169 | -64.978 | DISCARD (+9.0pp over best, RELIANCE +11pp, HDFCBANK +2pp, under gate) | — |
| 2 | 2026-09-01 | n_epochs 5→10 (more gradient steps per rollout) | -82.766 | -94.441 | DISCARD (-74.9pp regression from current best) | — |
| 1 | 2026-09-01 | INDICATORS: 106→22 (v26 curated set: 7 trend, 7 momentum, 4 volatility, 3 volume, 1 return) | **-7.855** | -51.637 | **KEPT** (+67.7pp vs full baseline; seed=43 conf +49.3pp, not in CANDIDATES) | 9c74acb |
| 0 | 2026-09-01 | baseline (v18 defaults, BUDGET=60k, 3-stock panel, SEED=42) | -75.552 | -96.192 | baseline | — |

