# autoresearch experiment log

Newest first. One row per experiment. `mean_val_outperf_pp` is the objective
(higher is better); `test` is report-only.

## ACTIVE GATE (2026-09-05): METRIC2_clip50 — 25.69pp

**New metric:** METRIC2_clip50 clips each stock's outperf to ±50pp before averaging.
This compresses heavy-tail basin-flip variance (RELIANCE -244pp at seed=43 → -50pp clip).
Both METRIC (unclipped) and METRIC2 are printed each run. **Decision uses METRIC2.**

| seed | RELIANCE | ITC | HDFCBANK | METRIC2 (clipped) | METRIC (unclipped) |
|---|---|---|---|---|---|
| 42 | +0.98pp | +4.69pp | -33.25pp | **-9.194** | -9.194 |
| 43 | -243.74pp → clip -50pp | -2.12pp | -41.69pp | **-31.269** | -95.850 |
| 44 | -172.43pp → clip -50pp | +5.17pp | -86.19pp | **-31.609** | -84.483 |

- stdev(METRIC2) = 12.84pp → **Gate = max(3.0, 2×12.84) = 25.69pp**
- METRIC2 baseline (seed=42) = **-9.194pp** → must beat **+16.49pp** to keep
- METRIC gate = 94.19pp (same as before — unclipped metric is still impossible to gate on)

**Reachability check:** with HDFCBANK clipped at -33.25pp (best observed), RELIANCE and ITC
must average +49.5pp each for the 3-stock mean to reach +16.49pp. Production shows ITC can reach
+40pp and RELIANCE ~+68pp outperf (v9), so this gate is genuinely reachable with a good policy.

Prior gate was 94.2pp (METRIC, ITC panel, 2026-09-02). Prior was 60.4pp (TATAMOTORS panel, invalidated). See `program.md`.

## Noise gate recalibration (2026-09-02) — RELIANCE/ITC/HDFCBANK panel

TATAMOTORS panel invalidated (degenerate cash-hold artifact). Switching to ITC panel.
Calibration still in progress (seeds 43/44 running):

| seed | RELIANCE+ITC sum | HDFCBANK val | mean_val_outperf_pp |
|---|---|---|---|
| 42 | +5.67pp (RELIANCE+ITC together) | -33.25pp | **-9.194** |
| 43 | -245.86pp (RELIANCE+ITC together) | -41.69pp | **-95.850** |
| 44 | -245.87pp (RELIANCE+ITC together) | -86.19pp | **-84.483** |

- stdev([-9.194, -95.850, -84.483]) = 47.1pp
- **Gate = max(3.0pp, 2 × 47.1pp) = 94.2pp**
- Baseline (SEED=42) = **-9.194pp** → must beat **+85.0pp** to keep

**Gate analysis:** The ITC panel gate (94.2pp) is also unreachable. HDFCBANK val ≈ −33 to −86pp across seeds; RELIANCE and ITC are highly variable. Seed-to-seed range of 86pp (seed 42: −9.2pp vs seed 43: −95.9pp) reflects that 60k steps is not enough for stable training. The ITC panel baseline at seed=42 (−9.194pp) is much healthier than the TATAMOTORS panel (−75.552pp), confirming TATAMOTORS was degenerate. All experiments should compare to the seed=42 baseline (−9.194pp) for directional signal.

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
ITC panel recalibration complete (2026-09-02). Gate = 94.2pp, baseline (seed=42) = -9.194pp.

## ITC panel experiments — METRIC2_clip50 (gate=25.69pp, baseline=-9.194pp, target=+16.49pp)

All experiments use SEED=42 unless noted. METRIC2 (clipped) is the keep/discard criterion; METRIC (unclipped) is listed for reference.

**NOTE on ITC-1 through ITC-15 (pre-2026-09-05):** these rows pre-date METRIC2. The column labeled "METRIC2" shows the unclipped METRIC value; "METRIC" shows the test outperformance. Reinterpret accordingly.

### 2026-09-05 (METRIC2_clip50 era, gate=25.69pp, target=+16.49pp)

| # | date (UTC) | change (one variable) | METRIC2 | METRIC | test | kept? | commit |
|---|---|---|---|---|---|---|---|
| *(experiments starting from ITC-16)* | | | | | | | |

### 2026-09-04 and earlier (METRIC/unclipped era, gate=94.2pp — all discard)

| # | date (UTC) | change (one variable) | METRIC (unclipped) | test | kept? |
|---|---|---|---|---|---|
| ITC-15 | 2026-09-04 | max_grad_norm 0.5→1.0 | -54.384 | -27.562 | DISCARD |
| ITC-14 | 2026-09-04 | max_grad_norm 0.5→0.3 | -22.191 | -17.329 | DISCARD |
| ITC-13 | 2026-09-04 | enable_critic_lstm=False | -83.468 | -21.176 | DISCARD (critic LSTM essential) |
| ITC-12 | 2026-09-04 | BUDGET 60k→40k | -13.021 | -7.103 | DISCARD |
| ITC-11 | 2026-09-04 | clip_range 0.2→0.15 | -98.357 | -18.851 | DISCARD |
| ITC-10 | 2026-09-04 | clip_range 0.2→0.3 | -59.819 | -35.010 | DISCARD |
| ITC-9 | 2026-09-04 | vf_coef 0.5→1.0 | -98.194 | -31.949 | DISCARD |
| ITC-8 | 2026-09-04 | lstm 128→32 | -76.037 | -28.030 | DISCARD |
| ITC-7 | 2026-09-04 | lstm/net_arch 128→64 | **+2.960** | -19.042 | DISCARD (best; +12.2pp vs baseline) |
| ITC-6 | 2026-09-04 | gamma 0.99→0.95 | -4.201 | -30.686 | DISCARD (+4.99pp) |
| ITC-5 | 2026-09-04 | ent_coef 0.01→0.05 | -7.047 | -17.852 | DISCARD (+2.1pp) |
| ITC-4 | 2026-09-04 | batch_size 64→128 | -106.505 | -37.548 | DISCARD |
| ITC-3 | 2026-09-04 | n_steps 512→256 | -21.208 | -21.641 | DISCARD |
| ITC-2 | 2026-09-02 | n_epochs 5→3 | -108.092 | -30.826 | DISCARD |
| ITC-1 | 2026-09-02 | baseline (SEED=42, 22 indicators, v18 hyperparams) | **-9.194** | -5.730 | **BASELINE** |

## TATAMOTORS panel experiments (RELIANCE/TATAMOTORS/HDFCBANK, gate=60.4pp, baseline=-7.855pp — INVALIDATED)

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

