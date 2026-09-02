# HANDOFF — auto-tinker session state

**Session start:** 2026-09-02T21:11:18Z (session 3)

## Current task

Continuing hyperparameter experiments from the 22-indicator champion (exp1: -7.855pp).
Gate = 60.4pp (calibrated 2026-09-01). Gate target to beat: -7.855 + 60.4 = +52.5pp.
Gate analysis: physically unreachable on this panel — TATAMOTORS bear val inflates noise.
Key insight: gate unreachable, but logging for directional insights. Advisor recommends panel recalibration.

## Advisor guidance (session 3 start, 2026-09-02)

Independent Opus advisor recommended:
1. Skip n_lstm_layers=2 and vf_coef=1.0 (contraindicated — add capacity to already-overfitting model)
2. n_epochs 5→3 (exp18) — best of planned 4
3. n_steps=256 + gamma=0.95 combination run (exploratory, same "shorter horizon" hypothesis)
4. Panel recalibration: 5 stocks or clip per-stock at ±100pp to reduce σ and make gate reachable
5. batch_size 128 (weaker prior)

## Progress

- [x] Calibration seed 42/43/44 — DONE. Gate = 60.4pp.
- [x] exp1: 106→22 indicators — KEPT (-7.855pp, +67.7pp vs baseline), commit 9c74acb
- [x] exp2: n_epochs 5→10 — DISCARD (-82.766pp)
- [x] exp3: lstm 128→64 — DISCARD (+1.169pp, under gate)
- [x] exp4: ent_coef 0.01→0.05 — DISCARD (-4.778pp, under gate)
- [x] exp5: n_steps 512→256 — DISCARD (+9.512pp, under gate; best secondary result)
- [x] exp6: lr 3e-4→1e-3 — DISCARD (-96.906pp)
- [x] exp7: gae_lambda 0.95→0.80 — DISCARD (-101.674pp)
- [x] exp8: 22→6 indicators — DISCARD (-47.033pp; test near-zero +0.406pp notable)
- [x] exp9: clip_range 0.2→0.1 — DISCARD (-89.735pp)
- [x] exp10: lr 3e-4→1e-4 — DISCARD (-110.912pp)
- [x] exp11: n_steps 512→1024 — DISCARD (-75.125pp; test +26.439pp, all 3 beat B&H notable)
- [x] exp12: 11-indicator trend set — DISCARD (-86.689pp)
- [x] exp13: BUDGET 60k→80k — DISCARD (-8.686pp, ≈ same as champion)
- [x] exp14: gamma 0.99→0.95 — DISCARD (+5.560pp, +13.4pp over champion, under gate)
- [ ] exp15: n_lstm_layers 1→2 — RUNNING (session 3; advisor says contraindicated but logging result)
- [ ] exp16: n_epochs 5→3 (renamed from exp18; advisor top pick)
- [ ] exp17: n_steps=256 + gamma=0.95 (combination, exploratory)
- [ ] exp18: batch_size 64→128 (weaker prior)
- [ ] exp19: Panel recalibration — swap STOCKS, recalibrate gate

## Current train.py state

- STOCKS = ["RELIANCE", "TATAMOTORS", "HDFCBANK"]
- BUDGET_TIMESTEPS = 60000
- SEED = 42
- INDICATORS: 22-indicator v26 curated set (champion config)
- n_lstm_layers = 2 (exp15 change — will revert to 1 after run)

## Uncommitted changes

- autoresearch/train.py — n_lstm_layers=2 (exp15)
- autoresearch/HANDOFF.tinker.md — this file

## Next step

1. Wait for exp15 completion notification
2. Log exp15 result in log.md, revert n_lstm_layers to 1
3. Apply exp16 (n_epochs 5→3), run
4. Apply exp17 combination (n_steps=256 + gamma=0.95), run
5. exp18 batch_size 128
6. Consider panel recalibration (swap STOCKS for ITC/RELIANCE/HDFCBANK, recalibrate gate at 3 seeds)

## Gotchas

- pandas_ta hma.py patched for Python 3.11 (line 69) — patch already applied this session. Fresh containers need re-patch.
- .ta_cache/ is populated (RELIANCE, TATAMOTORS, HDFCBANK) — runs are fast (~8-12 min per experiment).
- Gate (60.4pp) calibrated for 3-stock panel at 60k budget. If STOCKS or BUDGET_TIMESTEPS changes, must recalibrate.
- 80k budget confirmed ≈ same as 60k on val (exp13); no benefit to increasing budget.
- TATAMOTORS seed=42 degenerate cash-hold (B&H=-55.75% in val period, policy likely holds cash for +177pp).
  This inflates baseline and makes gate physically unreachable.
- Advisor says: ignore test column (too noisy), focus on val directional insights.

## Summary table (directional hits so far, all under gate)

| exp | change | val pp | vs champion | direction |
|---|---|---|---|---|
| 14 | gamma 0.95 | +5.56 | +13.4pp | ↑ (shorter horizon) |
| 5 | n_steps 256 | +9.51 | +17.4pp | ↑ (more frequent updates) |
| 4 | ent_coef 0.05 | -4.78 | +3.1pp | ↑ (more exploration) |
| 3 | lstm 64 | +1.17 | +9.0pp | ↑ (less capacity) |
