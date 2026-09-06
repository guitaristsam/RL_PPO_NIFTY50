# HANDOFF — auto-tinker session state

**Session start:** 2026-09-06T21:09:55Z (current session)

## Current task

Running METRIC2_clip50 proxy experiments on ITC panel (RELIANCE/ITC/HDFCBANK).
Gate = 25.69pp. Baseline = -9.194pp. Target to beat = +16.49pp.

No experiment has cleared the gate yet. Best result: ITC-32 (ReLU activation) at +5.684pp (+14.878pp vs baseline).

## Key findings this session

- **ReLU activation (ITC-32):** METRIC2=+5.684pp — NEW BEST. +14.878pp vs baseline. Under gate.
- **gamma=0.97 (ITC-29):** METRIC2=+3.395pp — second best. +12.59pp vs baseline. Sweet spot at 0.97.
- **gamma sweet spot:** 0.97 > 0.95 > 0.99 > 0.96 > 0.98. Non-monotonic; 0.97 is clearly best.
- **normalize_advantage=False (ITC-28):** -36.612pp — destabilizes training significantly.
- **v27 env (start fully invested, ITC-26):** -26.071pp — DD penalty fires immediately, policy sells.
- **DD_LAMBDA=0 (ITC-27):** -15.968pp — pure log-return prefers cash for volatile stocks.
- **LR decay (ITC-23):** -4.907pp — still a directional hit (+4.3pp vs baseline).

## Progress (all experiments ITC-panel, seed=42, BUDGET=60k)

- [x] ITC-22: target_kl=0.02 → -16.778pp DISCARD
- [x] ITC-23: LR linear decay → -4.907pp DISCARD (+4.3pp, directional HIT)
- [x] ITC-24: gamma=0.95 re-run → -4.201pp DISCARD (+4.99pp, directional HIT)
- [x] ITC-25: n_steps=1024 → -33.681pp DISCARD
- [x] ITC-26: USE_FULLY_INVESTED_START=True → -26.071pp DISCARD
- [x] ITC-27: DD_LAMBDA=0 → -15.968pp DISCARD
- [x] ITC-28: normalize_advantage=False → -36.612pp DISCARD
- [x] ITC-29: gamma=0.97 → +3.395pp DISCARD (NEW BEST at time; directional HIT)
- [x] ITC-30: gamma=0.96 → -20.333pp DISCARD
- [x] ITC-31: gamma=0.98 → -20.612pp DISCARD
- [x] ITC-32: activation_fn=ReLU → +5.684pp DISCARD (NEW BEST; directional HIT)

## Current train.py state

- STOCKS = ["RELIANCE", "ITC", "HDFCBANK"]
- BUDGET_TIMESTEPS = 60000
- SEED = 42
- INDICATORS: 22-indicator v26 curated set
- ALL PPO_PARAMS at v18 baseline (gamma=0.99, Tanh, etc.)

## Next experiments (priority order)

1. **LR=2e-4**: untried; interpolate between 3e-4 (baseline) and 1e-4 (bad in TATAMOTORS era)
2. **gae_lambda=0.90**: between 0.95 baseline and 0.80 (ITC-7 bad); test shorter credit horizon
3. **n_epochs=4**: interpolate between 5 (baseline) and 3 (ITC-2 bad)
4. **clip_range=0.25**: between 0.2 (baseline) and 0.3 (ITC-10 bad in old era)
5. Do NOT retry: shared_lstm=True (needs enable_critic_lstm=False too → two-variable)

## Patterns observed

Strong hits: ReLU activation (+14.9pp), gamma=0.97 (+12.6pp)
Moderate hits: gamma=0.95 (+5.0pp), LR decay (+4.3pp)
Catastrophic: normalize_advantage=False (-27pp), n_epochs=3 (-99pp), batch=128 (-97pp)
Gate is structurally difficult: RELIANCE val B&H=+300% (2016-2020 bull) makes the stock nearly unbeatable.

## Committed / pushed?

All log.md updates through ITC-32 committed in this session's main commit.
Push pending — do this at next commit point.

## Gotchas

- pandas_ta hma.py already patched for Python 3.11 in this container.
- .ta_cache/ populated — runs are ~8 min each.
- train.py is at BASELINE after each DISCARD (git checkout -- autoresearch/train.py).
- Exposure diagnostic (val_exp) was added to train.py during this session but reverted
  with git checkout when we stopped using the _ConfigurableEnv framework. Not needed for
  current experiments.
- Gate unreachability confirmed: with RELIANCE val B&H = +300%, clearing +16.49pp METRIC2
  requires exceptional policy. Directional hits build evidence; keep experimenting.
