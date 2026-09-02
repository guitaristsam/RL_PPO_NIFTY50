"""
autoresearch experiment file — the ONLY file the agent edits.

Pattern adapted from karpathy/autoresearch (MIT): an agent makes ONE change to
this file, runs it, reads a single comparable metric, keeps or discards, repeats.
Here the "model" is a PPO trading policy and the metric is validation
outperformance vs buy-and-hold, averaged over a small stock panel.

It reuses the audited, leak-safe plumbing from the frozen Rl_v18 baseline
(indicator computation, NaN handling, scaling, the integer trading env,
buy-and-hold) so experiments stay directly comparable to production. Do NOT edit
Rl_v18.py or any frozen file — change only the AGENT-EDITABLE block below.

Metric (printed on the last line, machine-parseable):
    METRIC mean_val_outperf_pp=<x> mean_test_outperf_pp=<y>
val is what you optimise; test is REPORT-ONLY (never select on it). A large
val-vs-test gap means the change is overfitting the proxy — treat as a red flag.
"""
import os
# Thread/BLAS caps must be set BEFORE numpy/torch import to take effect. Rl_v18
# sets these too, but it is imported AFTER numpy here, so replicate them at the very
# top so the caps actually apply in the harness (keeps runs deterministic and light).
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "TF_NUM_INTRAOP_THREADS", "TF_NUM_INTEROP_THREADS"):
    os.environ.setdefault(_v, "1")
import sys
import random
import copy
import time

# Import the frozen v18 plumbing. Repo root is one level up from this file.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

import numpy as np
import pandas as pd
import torch
import pandas_ta as ta

from Rl_v18 import (
    handle_nan_per_stock,
    prepare_data_for_finrl,
    create_trading_environment,
    calculate_buy_and_hold,
    list_of_indicators as AUDITED_INDICATORS,  # leak-audited; see CLAUDE.md
    NIFTY50_PATH,
)
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
from sb3_contrib import RecurrentPPO

# =====================================================================
# AGENT-EDITABLE BLOCK — change ONE variable per experiment (see program.md)
# =====================================================================
# Panel of stocks the metric averages over. A 3-stock panel (a clean winner, a
# strong trend, a hard case) is a far lower-variance screen than one stock.
STOCKS = ["RELIANCE", "ITC", "HDFCBANK"]

# Fixed training budget in env timesteps. Deterministic and comparable across
# machines (unlike wall-clock). 200k is production; this is a fast screen.
BUDGET_TIMESTEPS = 60000

SEED = 42

# Indicator set fed to the policy. SAFETY RULE: you may only REMOVE from or
# REORDER this audited list. NEVER add a name that is not already in it — every
# name here has passed test_indicator_causality.py; unaudited names can leak the
# future and silently inflate the metric.
# v26 curated 22-indicator subset — fewer features to reduce overfit
INDICATORS = [
    # trend / direction
    'ADX_14', 'DMP_14', 'DMN_14', 'MACD_12_26_9', 'MACDh_12_26_9',
    'AROONOSC_14', 'SUPERTd_7_3.0',
    # momentum / oscillators
    'RSI_14', 'ROC_10', 'MOM_10', 'CMO_14', 'STOCHk_14_3_3', 'WILLR_14',
    'TSI_13_25_13',
    # volatility
    'ATRr_14', 'NATR_14', 'BBP_5_2.0', 'STDEV_30',
    # volume / flow
    'MFI_14', 'CMF_20', 'EFI_13',
    # returns
    'LOGRET_1',
]

# RecurrentPPO hyperparameters (copied from the v18 baseline). Fair game to tune.
PPO_PARAMS = {
    "learning_rate": 3e-4,
    "n_steps": 512,
    "batch_size": 64,
    "n_epochs": 5,
    "gamma": 0.99,
    "gae_lambda": 0.95,
    "clip_range": 0.2,
    "normalize_advantage": True,
    "ent_coef": 0.01,
    "vf_coef": 0.5,
    "max_grad_norm": 0.5,
    "verbose": 0,
    "seed": SEED,
    "device": "cpu",  # pinned: cloud runners are CPU; keeps the determinism story honest
    "tensorboard_log": None,
    "policy_kwargs": {
        "lstm_hidden_size": 128,
        "n_lstm_layers": 1,
        "shared_lstm": False,
        "enable_critic_lstm": True,
        "net_arch": [128],
        "activation_fn": torch.nn.Tanh,
    },
}
# =====================================================================
# END AGENT-EDITABLE BLOCK — everything below is fixed harness machinery
# =====================================================================

# Leakage guardrail (enforced, not advisory): INDICATORS may only be a REORDER or
# SUBSET of the leak-audited v18 universe. Adding an unaudited name could leak the
# future and silently inflate the metric — the most dangerous failure mode. This
# assert crashes the run instead of letting a leaky "win" reach the leaderboard.
assert set(INDICATORS) <= set(AUDITED_INDICATORS), (
    "INDICATORS must be a subset/reorder of the audited v18 list — no unaudited "
    "names. Offending: " + ", ".join(sorted(set(INDICATORS) - set(AUDITED_INDICATORS)))
)

INITIAL_AMOUNT = 10000
_TA_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".ta_cache")


def _seed_everything(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def _all_indicators_frame(stock):
    """Compute (or load cached) the full pandas-ta AllStudy frame for one stock.

    AllStudy is deterministic, so we cache the ~300-indicator output per stock;
    this is the slow step and recomputing it every experiment would dominate the
    overnight budget. Filtering to INDICATORS happens after load, so the cache is
    valid regardless of which indicators an experiment keeps.
    """
    os.makedirs(_TA_CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(_TA_CACHE_DIR, f"{stock}.pkl")
    if os.path.exists(cache_path):
        return pd.read_pickle(cache_path)

    csv_path = os.path.join(NIFTY50_PATH, f"{stock}_daily.csv")
    df = pd.read_csv(csv_path)
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.set_index("datetime").sort_index()
    df["symbol"] = stock
    try:
        df.ta.cores = 0
    except Exception:
        pass
    df.ta.study(ta.AllStudy, cores=0)
    df.to_pickle(cache_path)
    return df


def _prepare_splits(stock):
    """Mirror Rl_v18.process_stock steps 1-6 exactly: full-series indicators ->
    filter -> NaN handling -> 70/15/15 chronological split -> RobustScaler fit on
    train only. Only tech indicators are scaled; close stays raw (so B&H and hmax
    below are on real prices, matching production)."""
    df_all = _all_indicators_frame(stock).copy()
    basic_cols = ["symbol", "open", "high", "low", "close", "volume"]

    # Pin the NaN-trim start row (and therefore the split dates below) to the FULL
    # audited indicator universe, NOT this experiment's INDICATORS subset.
    # handle_nan_per_stock trims to the first row where ALL kept indicators are
    # non-null; if that depended on the subset, pruning a slow-warmup indicator
    # would move the trim point, shift the 70/15/15 split, and put the validation
    # window on a different market period — making mean_val_outperf_pp incomparable
    # across runs. Anchoring on the audited list keeps the window invariant.
    audited = [c for c in AUDITED_INDICATORS if c in df_all.columns]
    df_fixed, _ = handle_nan_per_stock(df_all[basic_cols + audited])

    # Now restrict to the experiment's indicators (a subset of the audited list, per
    # the assert at import time). Rows/dates are already fixed by the trim above.
    exp_inds = [c for c in INDICATORS if c in df_fixed.columns]
    df = df_fixed[basic_cols + exp_inds]
    processed_raw, _, _ = prepare_data_for_finrl(df, skip_scaling=True)

    dates = sorted(processed_raw["date"].unique())
    train_end = int(len(dates) * 0.70)
    val_end = int(len(dates) * 0.85)
    train_split, val_split = dates[train_end], dates[val_end]

    train_raw = processed_raw[processed_raw["date"] < train_split].reset_index(drop=True)
    val_raw = processed_raw[(processed_raw["date"] >= train_split) &
                            (processed_raw["date"] < val_split)].reset_index(drop=True)
    test_raw = processed_raw[processed_raw["date"] >= val_split].reset_index(drop=True)

    train_df, tech, scalers = prepare_data_for_finrl(train_raw, scalers=None, skip_scaling=False)
    val_df, _, _ = prepare_data_for_finrl(val_raw, scalers=scalers, skip_scaling=False)
    test_df, _, _ = prepare_data_for_finrl(test_raw, scalers=scalers, skip_scaling=False)
    return train_df, val_df, test_df, tech


def _evaluate(model, slice_df, tech, hmax, train_vn):
    """Deterministic LSTM rollout over a slice; returns final portfolio % return.
    Mirrors Rl_v18 ValidationCallback._eval_on_val: fresh env, VecNormalize obs
    stats deep-copied from the trained wrapper and frozen."""
    vec = DummyVecEnv([lambda: create_trading_environment(
        slice_df, tech, initial_amount=INITIAL_AMOUNT, hmax=hmax)])
    vn = VecNormalize(vec, norm_obs=True, norm_reward=False, clip_obs=10.0, gamma=0.99)
    vn.obs_rms = copy.deepcopy(train_vn.obs_rms)
    vn.ret_rms = copy.deepcopy(train_vn.ret_rms)
    vn.training = False
    vn.norm_reward = False
    underlying = vn.venv.envs[0]

    obs = vn.reset()
    lstm_states = None
    episode_starts = np.ones((1,), dtype=bool)
    max_steps = len(sorted(slice_df["date"].unique())) - 1
    done, step = False, 0
    while not done and step < max_steps:
        action, lstm_states = model.predict(
            obs, state=lstm_states, episode_start=episode_starts, deterministic=True)
        episode_starts = np.zeros((1,), dtype=bool)
        obs, _, dones, _ = vn.step(action)
        done = bool(dones[0])
        step += 1
    final = float(getattr(underlying, "total_asset", INITIAL_AMOUNT))
    return (final / INITIAL_AMOUNT - 1.0) * 100.0


def run_stock(stock):
    _seed_everything(SEED)
    train_df, val_df, test_df, tech = _prepare_splits(stock)

    median_price = float(train_df["close"].median())
    hmax = int(max(2, min(200, INITIAL_AMOUNT // median_price))) if median_price > 0 else 10

    train_vec = DummyVecEnv([lambda: create_trading_environment(
        train_df, tech, initial_amount=INITIAL_AMOUNT, hmax=hmax)])
    train_vn = VecNormalize(train_vec, norm_obs=True, norm_reward=False,
                            clip_obs=10.0, gamma=0.99)
    model = RecurrentPPO("MlpLstmPolicy", train_vn, **PPO_PARAMS)
    model.learn(total_timesteps=BUDGET_TIMESTEPS, progress_bar=False)

    val_ret = _evaluate(model, val_df, tech, hmax, train_vn)
    test_ret = _evaluate(model, test_df, tech, hmax, train_vn)
    bh_val = calculate_buy_and_hold(val_df)["total_return_pct"]
    bh_test = calculate_buy_and_hold(test_df)["total_return_pct"]

    val_outperf = val_ret - bh_val
    test_outperf = test_ret - bh_test
    print(f"[{stock}] val {val_ret:+.2f}% vs B&H {bh_val:+.2f}% = {val_outperf:+.2f}pp | "
          f"test {test_ret:+.2f}% vs B&H {bh_test:+.2f}% = {test_outperf:+.2f}pp")
    return val_outperf, test_outperf


def main():
    t0 = time.time()
    print(f"autoresearch experiment | stocks={STOCKS} budget={BUDGET_TIMESTEPS} "
          f"indicators={len(INDICATORS)} seed={SEED}")
    vals, tests = [], []
    for stock in STOCKS:
        v, t = run_stock(stock)
        vals.append(v)
        tests.append(t)
    mean_val = float(np.mean(vals))
    mean_test = float(np.mean(tests))
    print(f"elapsed {time.time() - t0:.0f}s")
    # Final machine-parseable metric line. val is the objective; test is report-only.
    print(f"METRIC mean_val_outperf_pp={mean_val:.3f} mean_test_outperf_pp={mean_test:.3f}")


if __name__ == "__main__":
    main()
