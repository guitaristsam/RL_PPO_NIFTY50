# HANDOFF — auto-tinker session state

**Session start:** 2026-09-01T19:41:10Z (session 1) / continued 2026-09-02 (session 2)

## Current task

Continuing hyperparameter experiments from the 22-indicator champion (exp1: -7.855pp).
Gate = 60.4pp (calibrated 2026-09-01). Gate target to beat: -7.855 + 60.4 = +52.5pp.
Gate analysis: physically unreachable on this panel — TATAMOTORS bear val inflates noise.
Keep experimenting for secondary insights; log all results.

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
- [ ] exp15: n_lstm_layers 1→2 (deeper LSTM)
- [ ] exp16: vf_coef 0.5→1.0 (higher critic weight)
- [ ] exp17: batch_size 64→128 (larger minibatches)
- [ ] exp18: max_grad_norm 0.5→1.0 (looser gradient clipping)

## Current train.py state

- STOCKS = ["RELIANCE", "TATAMOTORS", "HDFCBANK"]
- BUDGET_TIMESTEPS = 60000 (reverted from 80k)
- SEED = 42
- INDICATORS: 22-indicator v26 curated set (champion config)
- gamma = 0.99 (champion config; exp14 reverted)

## Uncommitted changes

- autoresearch/log.md — exp14 result added
- autoresearch/HANDOFF.tinker.md — exp14 marked done

## Next step

1. Run exp15: n_lstm_layers=2 (deeper LSTM, more temporal capacity)
2. Run exp16: vf_coef=1.0 (higher critic weight)
3. Run exp17: batch_size=128 (larger minibatches)
4. Run exp18: n_epochs=3 (fewer gradient steps per rollout; may reduce overfit)
5. Consider recalibrating panel (swap TATAMOTORS for ITC or different stock)
6. Commit+push each experiment

## Gotchas

- pandas_ta hma.py was patched on the host for Python 3.11 f-string compat; this patch is not committed (library file, not repo file). If a fresh container restarts, the patch must be re-applied: change line 69 of `/usr/local/lib/python3.11/dist-packages/pandas_ta/overlap/hma.py` from a nested f-string to use an intermediate variable `_hma_suffix`.
- .ta_cache/ is populated — recomputing from scratch would be slow. It's gitignored.
- All deps installed: finrl, pandas-ta (ignore-requires-python), alpaca-trade-api, exchange-calendars, stockstats, wrds, yfinance, matplotlib, scikit-learn.
- The gate (60.4pp) is calibrated for the 3-stock panel at 60k budget. If STOCKS or BUDGET_TIMESTEPS changes, the gate must be recalibrated.
- 80k budget confirmed ≈ same as 60k on val (exp13); no benefit to increasing budget.
