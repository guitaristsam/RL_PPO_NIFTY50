"""
ensemble_predict.py — companion to Rl_v22.

Loads N saved RecurrentPPO checkpoints for one stock (each trained with a
different seed via `process_stock(..., seed_offset=k)`) and runs the test
loop, averaging the continuous actions across seeds before passing to the
shared environment. The hypothesis (see Rl_v22.py docstring) is that
seed-level variance is the dominant source of test-return variance at
200k timesteps, and action-averaging reduces it.

Usage:
    python -c "from ensemble_predict import ensemble_test; \
      ensemble_test('RELIANCE', seed_offsets=[0, 1, 2])"

This file deliberately reuses the v22 pipeline for data prep / env build /
test logging so the only new thing is the multi-model action averaging.
"""

import os
import numpy as np

from Rl_v22 import (
    NIFTY50_PATH, TRAINED_MODEL_DIR, RESULTS_DIR,
    list_of_indicators, handle_nan_per_stock, prepare_data_for_finrl,
    create_trading_environment, calculate_buy_and_hold,
    create_comprehensive_report, TradeLogger,
)
import pandas as pd
import pandas_ta as ta
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
from sb3_contrib import RecurrentPPO


def ensemble_test(stock_name, seed_offsets=(0, 1, 2), initial_amount=10000):
    """Average continuous actions across N trained seeds, run the test loop."""
    file_path = os.path.join(NIFTY50_PATH, f"{stock_name}_daily.csv")
    df = pd.read_csv(file_path)
    if 'datetime' in df.columns:
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.set_index('datetime').sort_index()
    df['symbol'] = stock_name
    df.ta.cores = 0
    df.ta.study(ta.AllStudy, cores=0)
    keep = ['symbol', 'open', 'high', 'low', 'close', 'volume'] + \
           [c for c in list_of_indicators if c in df.columns]
    df = df[keep]
    df, _ = handle_nan_per_stock(df)
    proc, _, _ = prepare_data_for_finrl(df, skip_scaling=True)
    dates = sorted(proc['date'].unique())
    val_split = dates[int(len(dates) * 0.85)]
    train_raw = proc[proc['date'] < dates[int(len(dates) * 0.70)]]
    test_raw = proc[proc['date'] >= val_split].reset_index(drop=True)
    train_df, _, scalers = prepare_data_for_finrl(train_raw, scalers=None)
    test_df, tech, _ = prepare_data_for_finrl(test_raw, scalers=scalers)
    median_train = float(train_df['close'].median())
    hmax_value = int(max(2, min(200, 10000 // median_train))) if median_train > 0 else 10

    # Load each (model, vecnorm) pair. Each seed has its own VecNormalize stats.
    members = []
    for off in seed_offsets:
        seed = 42 + int(off)
        model_path = os.path.join(TRAINED_MODEL_DIR, f"{stock_name}_seed{seed}_ppo.zip")
        vn_path = os.path.join(TRAINED_MODEL_DIR, f"{stock_name}_seed{seed}_vecnorm.pkl")
        env_vec = DummyVecEnv([lambda: create_trading_environment(
            test_df, tech, initial_amount=initial_amount, hmax=hmax_value)])
        env_vec = VecNormalize.load(vn_path, env_vec)
        env_vec.training = False
        env_vec.norm_reward = False
        model = RecurrentPPO.load(model_path, device="auto")
        members.append((model, env_vec))

    # Run a shared "evaluation" env that we'll step using the averaged action.
    eval_vec = DummyVecEnv([lambda: create_trading_environment(
        test_df, tech, initial_amount=initial_amount, hmax=hmax_value)])
    # Use the FIRST seed's VecNormalize for the eval env (any one will do —
    # action averaging happens before the env step, so the env doesn't care).
    eval_vec = VecNormalize.load(
        os.path.join(TRAINED_MODEL_DIR, f"{stock_name}_seed{42 + int(seed_offsets[0])}_vecnorm.pkl"),
        eval_vec)
    eval_vec.training = False
    eval_vec.norm_reward = False
    underlying = eval_vec.venv.envs[0]
    obs = eval_vec.reset()
    for m, vn in members:
        vn.reset()  # sync each member's underlying env to step 0
    states = [None] * len(members)
    starts = [np.ones((1,), dtype=bool) for _ in members]
    account_values = [float(initial_amount)]
    done = False
    max_steps = len(sorted(test_df['date'].unique())) - 1
    step = 0
    while not done and step < max_steps:
        actions = []
        for i, (m, vn) in enumerate(members):
            # Each member sees the obs from its own VecNormalize; identical
            # underlying state but with that member's training-time obs stats.
            member_obs = vn.normalize_obs(eval_vec.unnormalize_obs(obs))
            a, states[i] = m.predict(member_obs, state=states[i],
                                     episode_start=starts[i], deterministic=True)
            starts[i] = np.zeros((1,), dtype=bool)
            actions.append(a)
        # Average continuous actions (the env will discretize via
        # IntegerTradingEnv._process_action).
        avg_action = np.mean(np.stack(actions, axis=0), axis=0)
        obs, _, dones, _ = eval_vec.step(avg_action)
        done = bool(dones[0])
        cur = float(getattr(underlying, 'total_asset', initial_amount))
        account_values.append(cur)
        step += 1

    final_value = account_values[-1]
    bh = calculate_buy_and_hold(test_df, initial_amount=initial_amount)
    print(f"[ensemble:{stock_name}] seeds={list(seed_offsets)} "
          f"final={final_value:.2f} ({(final_value/initial_amount-1)*100:+.2f}%) "
          f"bh={bh['final_value']:.2f} ({bh['total_return_pct']:+.2f}%)")
    return final_value, account_values
