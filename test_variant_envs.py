"""
test_variant_envs.py — env-level checks for the unrun variant forks.

Verifies, without any training:
  1. v19's B&H-relative reward matches a from-scratch recomputation at every
     step: clip((log(eq_t/eq_{t-1}) - log(close_t/close_{t-1})) * 100, ±10)
     minus the v12 drawdown penalty.
  2. v21's target-exposure action mapping: a=+1 buys toward 100% exposure
     (capped by hmax and budget), a=-1 sells the whole position.

Runs on a 300-date RELIANCE slice; one pandas-ta pass (~15 s).

    python test_variant_envs.py
"""

import os
import unittest

import numpy as np
import pandas as pd
import pandas_ta as ta


def _prepare_slice(mod, n_dates=300):
    """Run the variant's own data pipeline and return (slice_df, tech)."""
    path = os.path.join(mod.NIFTY50_PATH, "RELIANCE_daily.csv")
    df = pd.read_csv(path)
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.set_index("datetime").sort_index()
    df["symbol"] = "RELIANCE"
    df.ta.cores = 0
    df.ta.study(ta.AllStudy, cores=0)
    keep = ["symbol", "open", "high", "low", "close", "volume"] + [
        c for c in mod.list_of_indicators if c in df.columns
    ]
    df, _ = mod.handle_nan_per_stock(df[keep])
    proc, tech, _ = mod.prepare_data_for_finrl(df, skip_scaling=True)
    dates = sorted(proc["date"].unique())[-n_dates:]
    return proc[proc["date"].isin(dates)].reset_index(drop=True), tech


def _reset(env):
    out = env.reset()
    return out[0] if isinstance(out, tuple) else out


def _step(env, action):
    out = env.step(np.array([action], dtype=np.float32))
    if len(out) == 5:
        obs, reward, terminated, truncated, info = out
        return reward, terminated or truncated
    obs, reward, done, info = out
    return reward, done


class V19RewardTest(unittest.TestCase):
    """Recompute v19's reward from env internals at every step."""

    def test_bh_relative_reward(self):
        import Rl_v19 as v19

        slice_df, tech = _prepare_slice(v19)
        import io, contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            env = v19.create_trading_environment(
                slice_df, tech, initial_amount=10000, hmax=10)
        _reset(env)

        peak = 10000.0
        actions = [0.8, 0.3, -0.2, 1.0, 0.0, -0.5, 0.6, -1.0] * 30
        for k, a in enumerate(actions):
            prev_prices = np.maximum(
                np.asarray(env.state[env._price_slice], dtype=np.float64), 0.01)
            prev_shares = np.asarray(env.state[env._shares_slice], dtype=np.float64)
            prev_eq = float(env.state[0]) + float(np.sum(prev_shares * prev_prices))
            prev_close = float(prev_prices[0])

            reward, done = _step(env, a)

            cur_eq = float(env.total_asset)
            cur_close = max(float(env.state[1]), 0.01)
            primary = float(np.clip(
                (np.log(cur_eq / prev_eq) - np.log(cur_close / prev_close)) * 100.0,
                -10.0, 10.0))
            peak = max(peak, cur_eq)
            dd = max(0.0, (peak - cur_eq) / peak)
            expected = primary - 1.0 * max(0.0, dd - 0.10)

            self.assertAlmostEqual(
                reward, expected, places=9,
                msg=f"step {k}: reward {reward} != expected {expected}")
            if done:
                break
        self.assertGreater(k, 50, "episode ended suspiciously early")


class V21TargetExposureTest(unittest.TestCase):
    """a=+1 must buy toward full exposure; a=-1 must liquidate."""

    def test_full_in_full_out(self):
        import Rl_v21 as v21

        slice_df, tech = _prepare_slice(v21)
        import io, contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            env = v21.create_trading_environment(
                slice_df, tech, initial_amount=10000, hmax=10)
        _reset(env)

        # Expected buy: target 100% of the (all-cash) portfolio at pre-step price.
        price = max(float(env.state[1]), 0.01)
        cash = float(env.state[0])
        desired = int((cash) // price)
        affordable = int(cash // (price * 1.0025))
        expected_buy = min(desired, affordable, 10)

        _step(env, 1.0)
        shares = int(env.state[1 + env.stock_dim])
        # FinRL's actions*hmax float round-trip can truncate by one share.
        self.assertLessEqual(abs(shares - expected_buy), 1,
                             f"bought {shares}, expected ~{expected_buy}")
        self.assertGreater(shares, 0, "a=+1 bought nothing")

        # a=-1 -> target zero exposure -> sell everything (position <= hmax).
        _step(env, -1.0)
        shares_after = int(env.state[1 + env.stock_dim])
        self.assertEqual(shares_after, 0,
                         f"a=-1 left {shares_after} shares (expected 0)")

        # a=0 -> target 50% exposure from all-cash: roughly half the portfolio.
        price = max(float(env.state[1]), 0.01)
        port = float(env.state[0])
        expected_half = min(int((0.5 * port) // price), 10)
        _step(env, 0.0)
        shares_half = int(env.state[1 + env.stock_dim])
        self.assertLessEqual(abs(shares_half - expected_half), 1,
                             f"a=0 bought {shares_half}, expected ~{expected_half}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
