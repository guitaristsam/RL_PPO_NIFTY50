import os
# Memory / thread caps — must be set BEFORE numpy / torch / TF import.
# Heavy multi-threaded BLAS + multi-process pandas_ta workers were each
# re-importing numpy/pandas/TF and busting the Windows page file.
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
os.environ.setdefault("TF_NUM_INTRAOP_THREADS", "1")
os.environ.setdefault("TF_NUM_INTEROP_THREADS", "1")

import glob
import time
import random
import sys
import warnings
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
import numpy as np
import pandas as pd
import pandas_ta as ta
import torch
torch.set_num_threads(1)
try:
    torch.set_num_interop_threads(1)
except RuntimeError:
    # set_num_interop_threads must be called before any parallel work; ignore if too late.
    pass
import torch.nn as nn
import torch.optim as optim
import matplotlib.pyplot as plt
from datetime import datetime
from tqdm import tqdm
from typing import Optional, Dict, List
from dataclasses import dataclass
from sklearn.preprocessing import RobustScaler
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
from sb3_contrib import RecurrentPPO  # v9: LSTM policy for temporal memory
from stable_baselines3.common.callbacks import BaseCallback
from torch.utils.tensorboard import SummaryWriter
from gymnasium import spaces
import gymnasium as gym
from gymnasium import spaces
from finrl.meta.env_stock_trading.env_stocktrading import StockTradingEnv

# Suppress warnings
warnings.filterwarnings('ignore')

# Configuration
TRAINED_MODEL_DIR = "models"
RESULTS_DIR = "results"
CONSOLIDATED_REPORT = "consolidated_report.txt"
NIFTY50_PATH = r"C:\Users\sambh\OneDrive\Desktop\Nifty50OHLCV" + "\\"
MIN_DATA_ROWS = 252  # Minimum 1 year of data after cleaning

# Create directories if they don't exist
os.makedirs(TRAINED_MODEL_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

# Indicator list — pruned for v8 to remove confirmed and suspected lookahead leaks.
#
# REMOVED in v8 (leakage / suspected leakage):
#   DPO_20                — pandas-ta defaults lookahead=True; encodes future close.
#   AMATe_LR_8_21_2,
#   AMATe_SR_8_21_2       — Archer MAT trend uses centered-aligned trend confirmation.
#   AOBV_LR_2, AOBV_SR_2  — same construction (Archer OBV calls amat()).
#   PSARr_0.02_0.2        — PSAR reversal flag set on bar where reversal becomes visible.
#   TTM_TRND_6            — possibly center-aligned trend signal.
#   DEC_1, INC_1          — some pandas-ta versions compute close.diff(length).shift(-length).
#   STC_10_12_26_0.5,
#   STCmacd_10_12_26_0.5,
#   STCstoch_10_12_26_0.5 — STC initialises with forward-fill across whole series.
#   FISHERTs_9_1          — fisher signal column shifted forward in some versions.
#   EBSW_40_10            — Ehlers super-smoother is non-causal in published form.
#   COPC_11_14_10         — verify pandas-ta isn't applying a center-aligned WMA.
#
# KEPT but worth re-checking later: LR_14, SLOPE_1, FISHERT_9_1, RVI_14.
list_of_indicators = [
    'ABER_ATR_5_15','AD','ADOSC_3_10','ADX_14','DMP_14','DMN_14',
    'APO_12_26','AROOND_14','AROONU_14','AROONOSC_14','ATRr_14','BBB_5_2.0',
    'BBP_5_2.0','BIAS_SMA_26','BOP','AR_26','BR_26','CCI_14_0.015','CDL_DOJI_10_0.1','CDL_INSIDE',
    'open_Z_30_1','high_Z_30_1','low_Z_30_1','close_Z_30_1','CFO_9','CG_10','CMF_20','CMO_14',
    'CTI_12','EFI_13','ER_10','BULLP_13','BEARP_13',
    'FISHERT_9_1','K_9_3','D_9_3','J_9_3','LR_14','LOGRET_1','MACD_12_26_9','MACDh_12_26_9',
    'MACDs_12_26_9','MAD_30','MASSI_9_25','MFI_14','MOM_10','NATR_14','NVI_1','PDIST','PCTRET_1','PGO_14','PPO_12_26_9',
    'PPOh_12_26_9','PPOs_12_26_9','PSARaf_0.02_0.2','PSL_12','PVI_1','PVO_12_26_9','PVOh_12_26_9','PVOs_12_26_9',
    'PVR','PVT','QQE_14_5_4.236','QQE_14_5_4.236_RSIMA','QS_10','ROC_10','RSI_14','RSX_14','RVGI_14_4','RVGIs_14_4','RVI_14',
    'SKEW_30','SLOPE_1','SMI_5_20_5','SMIs_5_20_5','SMIo_5_20_5','SQZ_20_2.0_20_1.5','SQZ_ON','SQZ_OFF','SQZ_NO',
    'SQZPRO_20_2.0_20_2_1.5_1','SQZPRO_ON_WIDE','SQZPRO_ON_NORMAL','SQZPRO_ON_NARROW','SQZPRO_OFF','SQZPRO_NO',
    'STDEV_30','STOCHk_14_3_3','STOCHd_14_3_3','STOCHRSIk_14_14_3_3',
    'STOCHRSId_14_14_3_3','SUPERTd_7_3.0','THERMOl_20_2_0.5','THERMOs_20_2_0.5','TRIX_30_9','TRIXs_30_9','TRUERANGE_1','TSI_13_25_13',
    'TSIs_13_25_13','UI_14','UO_7_14_28','VHF_28','VTXP_14','VTXM_14','WILLR_14','ZS_30'
]

# ======================
# FIXED TRADE LOGGER WITH INTEGER SHARES
# ======================
class TradeLogger:
    def __init__(self):
        self.trades = []
        self.positions = {}  # Track positions for each symbol
        self.winning_trades = 0
        self.losing_trades = 0
        self.current_portfolio_value = 0  # Track current portfolio value
        
    def log_trade(self, date, symbol, action, quantity, price, cost, portfolio_value, prev_positions):
        """
        Log trade with proper buy/sell detection based on position changes
        """
        # Update current portfolio value
        self.current_portfolio_value = portfolio_value
        
        # Enforce integer positions
        current_pos = int(round(quantity))
        prev_pos = int(round(prev_positions.get(symbol, 0)))
        
        # Determine actual action based on position change
        pos_change = current_pos - prev_pos
        
        if abs(pos_change) > 0:  # Only log if significant change
            if pos_change > 0:
                actual_action = "Buy"
                trade_quantity = pos_change
            else:
                actual_action = "Sell"
                trade_quantity = abs(pos_change)
                
                # Calculate win/loss for sell trades
                if symbol in self.positions and self.positions[symbol]['avg_price'] > 0:
                    avg_buy_price = self.positions[symbol]['avg_price']
                    if price > avg_buy_price:
                        self.winning_trades += 1
                    else:
                        self.losing_trades += 1
            
            trade = {
                'trade_id': len(self.trades) + 1,
                'date': date,
                'symbol': symbol,
                'action': actual_action,
                'quantity': trade_quantity,
                'price': price,
                'transaction_cost': cost,
                'total_value': trade_quantity * price,
                'portfolio_value': portfolio_value,
                'position_before': prev_pos,
                'position_after': current_pos
            }
            self.trades.append(trade)
            
            # Update position tracking
            if actual_action == "Buy":
                if symbol not in self.positions:
                    self.positions[symbol] = {'quantity': 0, 'avg_price': 0}
                
                old_qty = self.positions[symbol]['quantity']
                old_avg = self.positions[symbol]['avg_price']
                
                new_qty = old_qty + trade_quantity
                new_avg = ((old_qty * old_avg) + (trade_quantity * price)) / new_qty if new_qty > 0 else 0
                
                self.positions[symbol] = {'quantity': new_qty, 'avg_price': new_avg}
            
            elif actual_action == "Sell" and symbol in self.positions:
                self.positions[symbol]['quantity'] = max(0, self.positions[symbol]['quantity'] - trade_quantity)
        
    def get_trade_logbook(self):
        if not self.trades:
            return pd.DataFrame()
        return pd.DataFrame(self.trades)
    
    def get_trade_summary(self):
        if not self.trades:
            return {}
        
        df = self.get_trade_logbook()
        total_trades = len(df)
        buy_trades = len(df[df['action'] == 'Buy'])
        sell_trades = len(df[df['action'] == 'Sell'])
        total_costs = df['transaction_cost'].sum()
        
        # Calculate win rate
        total_closed_trades = self.winning_trades + self.losing_trades
        win_rate = (self.winning_trades / total_closed_trades * 100) if total_closed_trades > 0 else 0
        
        return {
            'total_trades': total_trades,
            'buy_trades': buy_trades,
            'sell_trades': sell_trades,
            'total_transaction_costs': total_costs,
            'avg_cost_per_trade': total_costs / total_trades if total_trades > 0 else 0,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate_pct': win_rate,
            'total_closed_trades': total_closed_trades
        }

def handle_nan_per_stock(df):
    """
    Apply conservative NaN handling for a single stock
    Returns cleaned DataFrame and indicator columns
    """
    basic_cols = ['symbol', 'open', 'high', 'low', 'close', 'volume']
    indicator_cols = [col for col in df.columns if col not in basic_cols]
    
    # Find rows with no NaN values in ANY indicator column
    no_nan_mask = df[indicator_cols].notna().all(axis=1)
    rows_with_all_indicators = df[no_nan_mask]
    
    if len(rows_with_all_indicators) > 0:
        first_complete_date = rows_with_all_indicators.index[0]
        df_conservative = df.loc[first_complete_date:].copy()
        
        print(f"  Found {len(rows_with_all_indicators)} rows with ALL indicators filled")
        print(f"  First complete date: {first_complete_date}")
        print(f"  Conservative filtered shape: {df_conservative.shape}")
        print(f"  Rows removed: {df.shape[0] - df_conservative.shape[0]}")
        
        # Verify
        remaining_nans = df_conservative[indicator_cols].isnull().sum().sum()
        print(f"  Remaining NaN values: {remaining_nans}")
        
    else:
        print("  No rows found with ALL indicators filled. Using best available row.")
        
        nan_count_per_row = df[indicator_cols].isnull().sum(axis=1)
        min_nan_count = nan_count_per_row.min()
        best_row_idx = nan_count_per_row.idxmin()
        
        print(f"  Best row: {best_row_idx} with {min_nan_count} NaN values")
        print(f"  Starting from this date")
        
        df_conservative = df.loc[best_row_idx:].copy()
        print(f"  Shape: {df_conservative.shape}")
        
        # Check which indicators still have NaN values
        remaining_nan_indicators = df_conservative[indicator_cols].isnull().sum()
        remaining_nan_indicators = remaining_nan_indicators[remaining_nan_indicators > 0]
        
        if len(remaining_nan_indicators) > 0:
            print(f"  Indicators still with NaN values:")
            for indicator, nan_count in remaining_nan_indicators.items():
                print(f"    {indicator}: {nan_count} NaN values")
    
    # =====================================================
    # ADDED: PROTECTION AGAINST ZERO PRICES
    # =====================================================
    print("  Cleaning zero/negative prices...")
    
    # Define price columns to clean
    price_cols = ['open', 'high', 'low', 'close']
    
    for col in price_cols:
        if col in df_conservative.columns:
            # 1. Replace zeros and negative values with NaN
            df_conservative[col] = df_conservative[col].replace([0, -np.inf, np.inf], np.nan)
            
            # 2. Forward fill only — bfill on the unsplit series would leak future
            #    prices into earlier bars across the eventual train/test boundary.
            df_conservative[col] = df_conservative[col].ffill()
            # Any leading NaN (no past value to fill from) gets clipped to 0.01 below.
            
            # 3. Ensure minimum price of 0.01
            df_conservative[col] = df_conservative[col].clip(lower=0.01)
            
            # 4. Report any remaining issues
            if df_conservative[col].isna().any():
                print(f"  ⚠️ Warning: Still have NaN values in {col} after cleaning")
            if (df_conservative[col] <= 0).any():
                print(f"  ⚠️ Warning: Still have non-positive values in {col} after cleaning")
    
    print("  Price cleaning completed. All prices >= 0.01")
    
    return df_conservative, indicator_cols

def prepare_data_for_finrl(df, scalers=None, skip_scaling=False):
    """
    Prepare technical indicators data for FinRL format.

    scalers: dict of {tic: fitted RobustScaler} or None to fit new scalers.
    skip_scaling: if True, skip normalisation entirely (used for the initial
                  format-conversion pass before the train/test split).
    Returns (processed_df, tech_indicators, scalers).
    """
    processed_df = df.copy()
    
    # Handle datetime index properly
    if isinstance(processed_df.index, pd.DatetimeIndex):
        processed_df = processed_df.reset_index()
        processed_df.rename(columns={'datetime': 'date'}, inplace=True)
    elif 'datetime' in processed_df.columns:
        processed_df.rename(columns={'datetime': 'date'}, inplace=True)
    else:
        # If first column looks like datetime
        if processed_df.index.name is not None:
            processed_df = processed_df.reset_index()
            processed_df.rename(columns={processed_df.columns[0]: 'date'}, inplace=True)
    
    # FinRL expects 'tic' column instead of 'symbol'
    if 'symbol' in processed_df.columns:
        processed_df.rename(columns={'symbol': 'tic'}, inplace=True)
    
    # Convert date to proper format
    processed_df['date'] = pd.to_datetime(processed_df['date'])
    processed_df['date'] = processed_df['date'].dt.strftime('%Y-%m-%d')
    
    # Get technical indicator columns (exclude basic OHLCV columns)
    tech_indicators = [col for col in processed_df.columns 
                      if col not in ['date', 'tic', 'open', 'high', 'low', 'close', 'volume']]
    
    # Handle any NaN values in technical indicators
    print("  Handling NaN values in technical indicators...")
    print(f"  NaN count before cleaning: {processed_df[tech_indicators].isna().sum().sum()}")
    
    # Forward-fill only; bfill would leak future indicator values into earlier
    # bars (especially across the train/test split if applied to the union frame,
    # but also within a single split — bfill always pulls future info backward).
    # Any leading NaN (no past value to fill from) is replaced with 0, which is
    # safe because RobustScaler-output indicators have median = 0 by construction.
    processed_df[tech_indicators] = processed_df[tech_indicators].ffill()
    processed_df[tech_indicators] = processed_df[tech_indicators].replace([np.inf, -np.inf], np.nan)
    processed_df[tech_indicators] = processed_df[tech_indicators].fillna(0)
    
    print(f"  NaN count after cleaning: {processed_df[tech_indicators].isna().sum().sum()}")
    
    # Normalise — fit on training data only to prevent data leakage.
    if not skip_scaling:
        is_fitting = scalers is None
        if is_fitting:
            scalers = {}
        normalized_dfs = []
        for tic in processed_df['tic'].unique():
            tic_data = processed_df[processed_df['tic'] == tic].copy()
            if len(tic_data) > 1:
                if is_fitting:
                    scaler = RobustScaler()
                    tic_data[tech_indicators] = scaler.fit_transform(tic_data[tech_indicators])
                    scalers[tic] = scaler
                elif tic in scalers:
                    tic_data[tech_indicators] = scalers[tic].transform(tic_data[tech_indicators])
            normalized_dfs.append(tic_data)
        processed_df = pd.concat(normalized_dfs, ignore_index=True)
        print("  Technical indicators normalised using RobustScaler per symbol")
    
    # Ensure required columns exist
    required_cols = ['date', 'open', 'high', 'low', 'close', 'volume', 'tic']
    for col in required_cols:
        if col not in processed_df.columns:
            raise ValueError(f"Required column '{col}' not found in dataframe")
    
    # Clean OHLCV data — ffill only (no bfill leakage), fall back to median for
    # any leading NaN. Median is computed on the same split, so no cross-split leak.
    for col in ['open', 'high', 'low', 'close', 'volume']:
        processed_df[col] = processed_df[col].replace([np.inf, -np.inf], np.nan)
        processed_df[col] = processed_df[col].ffill()
        processed_df[col] = processed_df[col].fillna(processed_df[col].median())
    
    # Sort by date and tic (crucial for time series)
    processed_df = processed_df.sort_values(['date', 'tic']).reset_index(drop=True)
    
    print(f"  Technical indicators found: {len(tech_indicators)}")
    print(f"  Data date range: {processed_df['date'].min()} to {processed_df['date'].max()}")
    print(f"  Unique symbols: {processed_df['tic'].unique()}")
    
    return processed_df, tech_indicators, scalers

# ======================
# FIXED TRADING ENVIRONMENT WITH INTEGER SHARES
# ======================
# ======================
# FIXED TRADING ENVIRONMENT WITH INTEGER SHARES AND PRICE VALIDATION
# ======================
class IntegerTradingEnv(StockTradingEnv):
    """
    Subclass of FinRL's StockTradingEnv enforcing integer-share positions and a
    strict per-step budget cap on top of FinRL's own internal check.

    CRITICAL — FinRL state layout (see env_stocktrading.py:_buy_stock):
        state[0]                                  = cash
        state[1 : 1 + stock_dim]                  = prices (one per stock)
        state[1 + stock_dim : 1 + 2*stock_dim]    = shares (one per stock)
        state[1 + 2*stock_dim : ...]              = tech-indicator block

    v6, v7, AND early v8 had this layout WRONG — they read shares from index 1
    (which is price) and computed a price_index using a tech-indicator stride.
    Symptom: `price` came out as `shares` (=0 at reset) → near-zero warning fired
    → price clamped to 0.01 → max_affordable became ~1M → our budget clamp was
    a no-op. FinRL's parent _buy_stock still enforced the real budget, so trades
    weren't catastrophic, but the integer guard did nothing useful, and the
    trade log mis-reported state[1] (price) as "position", producing nonsense
    quantities like "bought 1646 shares" (1646 was actually the next-day close).
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # cache index slices for the FinRL layout
        self._price_slice  = slice(1, 1 + self.stock_dim)
        self._shares_slice = slice(1 + self.stock_dim, 1 + 2 * self.stock_dim)
        # Round any non-integer initial position
        self.state[self._shares_slice] = np.round(
            self.state[self._shares_slice]
        ).astype(int)
        self._near_zero_warned = False

        # v12 reward state — v9 baseline (log-return * 100, clipped) + a small
        # drawdown penalty. ISOLATED single change vs v9: only the DD penalty.
        # All hyperparameters and the LSTM architecture are unchanged from v9.
        # v10/v11 conflated multiple interventions and underperformed v9; v12
        # tests a single hypothesis cleanly.
        self._equity_peak = float(self.initial_amount)
        self._dd_threshold = 0.10
        self._dd_lambda    = 1.0

    def reset(self, *args, **kwargs):
        result = super().reset(*args, **kwargs)
        self._equity_peak = float(self.initial_amount)
        self.state[self._shares_slice] = np.round(
            self.state[self._shares_slice]
        ).astype(int)
        return result

    def _process_action(self, raw_action):
        """Convert continuous PPO action in [-1, 1] to validated integer share count.

        Pre-scale to integer shares (matching FinRL's internal `*hmax`), validate
        budget and position limits in shares-space, return integer counts. The
        caller (step) divides by hmax so super().step()'s `*hmax` recovers our
        exact integer share count. Earlier versions rounded the raw [-1,1] action
        to int BEFORE the *hmax scaling, which collapsed every action into a
        coarse {-2,-1,0,1,2} grid — that's what kept v6/v7's policy std stuck at
        ~0.97 (no gradient benefit to producing fine-grained actions).
        """
        action_shares = np.round(
            np.asarray(raw_action, dtype=np.float64) * self.hmax
        ).astype(int)

        prices  = np.asarray(self.state[self._price_slice],  dtype=np.float64).copy()
        shares  = np.asarray(self.state[self._shares_slice], dtype=np.float64).copy()
        cash    = float(self.state[0])

        for i in range(self.stock_dim):
            price = prices[i]
            if price < 1e-6:
                price = 0.01
                self.state[1 + i] = price  # write back into the price slot
                if not self._near_zero_warned:
                    print(f"⚠️ Warning: Near-zero price detected at index {i}, "
                          f"setting to 0.01 (further occurrences suppressed)")
                    self._near_zero_warned = True

            if action_shares[i] > 0:  # Buy — clamp to budget and hmax
                denominator = price * (1 + self.buy_cost_pct[i])
                max_affordable = int(cash // denominator) if denominator > 1e-6 else 0
                action_shares[i] = int(min(action_shares[i], max_affordable, self.hmax))
            elif action_shares[i] < 0:  # Sell — can't sell more than we hold
                action_shares[i] = int(max(action_shares[i], -int(shares[i])))

        return action_shares

    def step(self, action):
        # Snapshot total asset BEFORE the step for the log-return reward.
        prev_prices = np.asarray(self.state[self._price_slice],  dtype=np.float64).copy()
        prev_shares = np.asarray(self.state[self._shares_slice], dtype=np.float64).copy()
        prev_prices = np.where(prev_prices < 1e-6, 0.01, prev_prices)
        prev_total_asset = float(self.state[0]) + float(np.sum(prev_shares * prev_prices))

        # Validate in shares-space, then convert back to [-1,1] so super().step()'s
        # internal `actions * self.hmax` recovers our exact integer share count.
        action_shares = self._process_action(action)
        if self.hmax > 0:
            rescaled = action_shares.astype(np.float32) / float(self.hmax)
        else:
            rescaled = action_shares.astype(np.float32)

        step_result = super().step(rescaled)

        if len(step_result) == 5:
            obs, reward, terminated, truncated, info = step_result
            done = terminated or truncated
        else:
            obs, reward, done, info = step_result
            terminated = done
            truncated = False

        # Round shares back to integer (FinRL stores them as floats internally).
        self.state[self._shares_slice] = np.round(
            self.state[self._shares_slice]
        ).astype(int)
        # Clamp to non-negative (no shorting in this env).
        for i in range(self.stock_dim):
            if self.state[1 + self.stock_dim + i] < 0:
                self.state[1 + self.stock_dim + i] = 0

        # Compute total_asset = cash + sum(shares * prices), with a near-zero guard.
        prices = np.asarray(self.state[self._price_slice],  dtype=np.float64)
        shares = np.asarray(self.state[self._shares_slice], dtype=np.float64)
        prices = np.where(prices < 1e-6, 0.01, prices)
        self.state[self._price_slice] = prices
        self.total_asset = float(self.state[0]) + float(np.sum(shares * prices))

        # v12 REWARD: v9 log_return × 100 (clipped) MINUS a mild drawdown penalty.
        # Single-variable change vs v9 to isolate the DD-penalty hypothesis.
        if prev_total_asset > 1e-6 and self.total_asset > 1e-6:
            log_return = np.log(self.total_asset / prev_total_asset)
        else:
            log_return = -1.0
        primary = float(np.clip(log_return * 100.0, -10.0, 10.0))

        # Drawdown penalty: track running peak equity, subtract λ*(dd − threshold).
        if self.total_asset > self._equity_peak:
            self._equity_peak = self.total_asset
        drawdown = 0.0 if self._equity_peak <= 0 else max(
            0.0, (self._equity_peak - self.total_asset) / self._equity_peak
        )
        dd_penalty = self._dd_lambda * max(0.0, drawdown - self._dd_threshold)

        reward = primary - dd_penalty

        # Return in the same format we received
        if len(step_result) == 5:
            return obs, reward, terminated, truncated, info
        else:
            return obs, reward, done, info

def create_trading_environment(df, tech_indicators, initial_amount=10000, hmax=None):
    """
    Create trading environment with 0.25% transaction costs.

    `hmax` is computed price-aware when not given: floor(initial_amount / median_price),
    clamped to [2, 200]. The fixed hmax=10 from v6 collapsed action resolution on
    expensive stocks (e.g. ₹3000 stock × ₹10k cash → max 3 shares, so most of
    the [-1,1] action range rounded to 0).
    """
    stock_dim = df['tic'].nunique()
    print(f"  Number of stocks: {stock_dim}")

    if hmax is None:
        median_price = float(df['close'].median())
        if median_price > 0:
            hmax = int(max(2, min(200, initial_amount // median_price)))
        else:
            hmax = 10
        print(f"  Price-aware hmax = {hmax} (median close = ₹{median_price:,.2f})")

    # Environment parameters with 0.25% transaction costs
    env_kwargs = {
        "df": df,
        "stock_dim": stock_dim,
        "hmax": hmax,
        "initial_amount": initial_amount,
        "num_stock_shares": [0] * stock_dim,
        "buy_cost_pct": [0.0025] * stock_dim,   # 0.25% transaction cost
        "sell_cost_pct": [0.0025] * stock_dim,  # 0.25% transaction cost
        "reward_scaling": 1e-3,  # 1e-4 made critic rewards too tiny to learn from
        "state_space": 1 + 2*stock_dim + len(tech_indicators)*stock_dim,
        "action_space": stock_dim,
        "tech_indicator_list": tech_indicators,
        "turbulence_threshold": None,
        "make_plots": False,
        "print_verbosity": 1000
    }
    
    print(f"  State space dimension: {env_kwargs['state_space']}")
    print(f"  Action space dimension: {env_kwargs['action_space']}")
    
    try:
        # Use our fixed environment
        env = IntegerTradingEnv(**env_kwargs)
        print("  Environment created successfully")
        return env
    except Exception as e:
        print(f"  Error creating environment: {e}")
        raise

def train_ppo_model(train_df, tech_indicators, stock_name, total_timesteps=200000):
    """
    Train PPO model using FinRL with TensorBoard logging
    """
    print(f"  Creating training environment for {stock_name}...")
    # Compute hmax once on the training data so train and test envs match.
    median_price_train = float(train_df['close'].median())
    hmax_value = int(max(2, min(200, 10000 // median_price_train))) if median_price_train > 0 else 10
    env_train_raw = DummyVecEnv([
        lambda: create_trading_environment(
            train_df, tech_indicators, initial_amount=10000, hmax=hmax_value
        )
    ])
    # Normalize the *full* observation (cash, holdings, prices, indicators).
    # v6 only RobustScaler'd the indicators, so cash (~1e4), prices (1e2-1e3),
    # and holdings (0-200) hit the policy net raw — wildly mixed magnitudes
    # destabilise PPO with Tanh activations. Reward is left un-normalised
    # because reward_scaling is already tuned at the env level.
    env_train = VecNormalize(
        env_train_raw,
        norm_obs=True,
        norm_reward=False,
        clip_obs=10.0,
        gamma=0.99,
    )

    print(f"  Training PPO model for {stock_name} (hmax={hmax_value})...")
    
    # TensorBoard logging setup
    log_dir = f"runs/{stock_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(log_dir, exist_ok=True)
    writer = SummaryWriter(log_dir)
    
    # v9: RecurrentPPO with MlpLstmPolicy. Daily price/indicator features are
    # highly autocorrelated; an MLP has no notion of "where in the trajectory"
    # we are, so it can't condition on regime. An LSTM gives the policy a hidden
    # state that can carry trend/volatility memory across timesteps.
    #
    # Hyperparameters tuned for LSTM:
    #   - n_steps reduced (LSTM gradients explode with very long rollouts)
    #   - batch_size must divide n_steps * n_envs; with n_envs=1, batch_size=64
    #   - n_epochs reduced because LSTM updates are more sensitive to overfitting
    PPO_PARAMS = {
        "learning_rate": 3e-4,
        "n_steps": 512,           # was 1024 in v8; LSTM prefers shorter rollouts
        "batch_size": 64,         # must evenly divide n_steps for RecurrentPPO
        "n_epochs": 5,            # LSTM is more sample-efficient → fewer epochs
        "gamma": 0.99,
        "gae_lambda": 0.95,
        "clip_range": 0.2,
        "normalize_advantage": True,
        "ent_coef": 0.01,
        "vf_coef": 0.5,
        "max_grad_norm": 0.5,
        "verbose": 1,
        "seed": 42,
        "device": "auto",
        "tensorboard_log": log_dir,
        "policy_kwargs": {
            "lstm_hidden_size": 128,    # size of the LSTM hidden state
            "n_lstm_layers": 1,         # 1 layer is plenty; deeper hurts on this size
            "shared_lstm": False,       # separate LSTM for actor & critic
            "enable_critic_lstm": True,
            "net_arch": [128],          # post-LSTM MLP
            "activation_fn": torch.nn.Tanh,
        }
    }

    print(f"  Creating RecurrentPPO model for {stock_name}...")

    try:
        model_ppo = RecurrentPPO("MlpLstmPolicy", env_train, **PPO_PARAMS)
        print(f"  RecurrentPPO model for {stock_name} created successfully")

        print(f"  Starting training for {total_timesteps} timesteps...")

        model_ppo.learn(
            total_timesteps=total_timesteps,
            tb_log_name='recurrent_ppo',
            progress_bar=True
        )
        
        print(f"  Training for {stock_name} completed successfully!")
        return model_ppo, env_train, hmax_value
        
    except Exception as e:
        print(f"  Error during training: {e}")
        raise

def test_ppo_model(trained_model, test_df, tech_indicators, stock_name,
                   vecnorm_path=None, hmax_value=None):
    """
    Test the trained PPO model with enhanced logging.

    Wraps the test env in the saved VecNormalize so observations are scaled
    with the same running stats as training. `training=False` and
    `norm_reward=False` freeze the stats and skip reward normalisation.

    Date alignment (v6 bug): FinRL's step() executes the action at price[t]
    then advances `self.day` to t+1, so `total_asset` AFTER step is the
    portfolio value at t+1. v6 paired that with `unique_dates[step_count]`
    (which equals t before increment) — off by one. v7 records the initial
    value at unique_dates[0] before the loop and pairs each post-step value
    with unique_dates[step_count+1].
    """
    print(f"  Creating testing environment for {stock_name}...")
    initial_amount = 10000

    def _make_test_env():
        return create_trading_environment(
            test_df, tech_indicators, initial_amount=initial_amount, hmax=hmax_value
        )

    env_test_vec = DummyVecEnv([_make_test_env])
    if vecnorm_path is not None and os.path.exists(vecnorm_path):
        env_test_vec = VecNormalize.load(vecnorm_path, env_test_vec)
        env_test_vec.training = False
        env_test_vec.norm_reward = False
        print(f"  Loaded VecNormalize stats from {vecnorm_path}")
    else:
        # Fallback: identity normaliser. Should not happen in normal runs.
        env_test_vec = VecNormalize(env_test_vec, norm_obs=False, norm_reward=False)
        print("  Warning: no VecNormalize stats found; running unnormalised test")

    # Underlying IntegerTradingEnv for state introspection
    underlying_env = env_test_vec.venv.envs[0]

    print(f"  Testing PPO model for {stock_name}...")

    trade_logger = TradeLogger()

    obs = env_test_vec.reset()

    # Record the initial portfolio value at unique_dates[0]
    account_values = [float(initial_amount)]
    actions_taken = []

    # Get actual dates from test data
    unique_dates = sorted(test_df['date'].unique())
    symbols = test_df['tic'].unique()

    done = False
    step_count = 0
    max_steps = len(unique_dates) - 1  # account_values[0] already covers day 0
    prev_positions = {symbol: 0 for symbol in symbols}

    # LSTM hidden state plumbing for RecurrentPPO. Plain PPO ignores these.
    lstm_states = None
    episode_starts = np.ones((1,), dtype=bool)  # episode_start=True only on first step

    print(f"  Starting test with max steps: {max_steps}")
    print(f"  Symbols being traded: {list(symbols)}")

    while not done and step_count < max_steps:
        try:
            action, lstm_states = trained_model.predict(
                obs, state=lstm_states, episode_start=episode_starts, deterministic=True
            )
            episode_starts = np.zeros((1,), dtype=bool)

            obs, rewards, dones, infos = env_test_vec.step(action)
            done = bool(dones[0])
            info = infos[0]

            # total_asset after step reflects positions × price[step_count+1]
            if hasattr(underlying_env, 'total_asset'):
                current_value = underlying_env.total_asset
            elif hasattr(underlying_env, 'asset_memory') and len(underlying_env.asset_memory) > 0:
                current_value = underlying_env.asset_memory[-1]
            else:
                current_value = info.get('total_asset', initial_amount)

            account_values.append(float(current_value))
            actions_taken.append(np.asarray(action).copy())
            
            # Get current positions from underlying env state (post-step).
            # FinRL layout: state[0]=cash, state[1:1+N]=prices, state[1+N:1+2N]=shares.
            # v6/v7/early-v8 read state[1:1+N] thinking it was positions, but that's
            # actually prices — which is why earlier trade logs reported impossibly
            # large "positions" (they were the next-day close prices).
            current_positions = {}
            if hasattr(underlying_env, 'state'):
                stock_dim = len(symbols)
                pos_start_idx = 1 + stock_dim
                pos_end_idx = 1 + 2 * stock_dim
                if len(underlying_env.state) >= pos_end_idx:
                    positions = underlying_env.state[pos_start_idx:pos_end_idx]
                    for i, symbol in enumerate(symbols):
                        if i < len(positions):
                            current_positions[symbol] = int(round(positions[i]))

            # Trade was executed at price[step_count] (the day the action was decided),
            # producing the new positions we just read. Log against that date.
            if step_count < len(unique_dates):
                trade_date = unique_dates[step_count]
                current_date_data = test_df[test_df['date'] == trade_date]
                
                for i, symbol in enumerate(symbols):
                    if i < len(current_positions):
                        symbol_data = current_date_data[current_date_data['tic'] == symbol]
                        
                        if len(symbol_data) > 0:
                            price = symbol_data['close'].iloc[0]
                            current_pos = current_positions[symbol]
                            prev_pos = prev_positions.get(symbol, 0)
                            
                            # Calculate position change
                            pos_change = current_pos - prev_pos
                            
                            # Only log if significant position change
                            if abs(pos_change) > 0:
                                # Calculate transaction cost
                                cost = abs(pos_change) * price * 0.0025
                                
                                # Validate trade doesn't exceed portfolio value
                                trade_value = abs(pos_change) * price
                                if trade_value > current_value * 5:  # 5x leverage check
                                    print(f"  Suspicious trade: {trade_value:,.2f} vs portfolio {current_value:,.2f}")
                                
                                trade_logger.log_trade(
                                    date=trade_date,
                                    symbol=symbol,
                                    action="",  # Determined by logger
                                    quantity=current_pos,
                                    price=price,
                                    cost=cost,
                                    portfolio_value=current_value,
                                    prev_positions=prev_positions.copy()
                                )
            
            # Update previous positions
            prev_positions = current_positions.copy()
            step_count += 1
            
            if step_count % 100 == 0 or step_count == max_steps:
                print(f"  Step {step_count}/{max_steps}, current value: ₹{current_value:,.2f}")
                
        except Exception as e:
            print(f"  Error during testing at step {step_count}: {e}")
            break
    
    print(f"  Testing completed after {step_count} steps")
    
    if len(account_values) == 0:
        print("  Warning: No account values recorded during testing")
        account_values = [10000]
        actions_taken = [np.array([0])]
    
    # account_values[0] is the initial value at unique_dates[0]; each subsequent
    # entry is the post-step value at unique_dates[i]. Truncate to whichever
    # is shorter (env may terminate early).
    n = min(len(account_values), len(unique_dates))
    df_account_value = pd.DataFrame({
        'account_value': account_values[:n],
        'date': pd.to_datetime(unique_dates[:n])
    })
    
    df_actions = pd.DataFrame({
        'actions': actions_taken
    })
    
    print(f"  Account value range: ₹{min(account_values):,.2f} - ₹{max(account_values):,.2f}")
    
    return df_account_value, df_actions, trade_logger

def calculate_yearly_returns(df_account_value):
    """
    Calculate comprehensive yearly returns and metrics
    """
    df = df_account_value.copy()
    
    if 'date' not in df.columns:
        print("Warning: No date column found, using index")
        return {}
    
    df['daily_return'] = df['account_value'].pct_change(1)
    df = df.dropna()
    
    if len(df) == 0:
        print("Warning: No data available for return calculation")
        return {}
    
    # Calculate various return metrics
    total_days = len(df)
    total_return = (df['account_value'].iloc[-1] / df['account_value'].iloc[0]) - 1
    
    # Annualized return (assuming 252 trading days per year)
    if total_days > 0:
        annualized_return = ((1 + total_return) ** (252 / total_days)) - 1
    else:
        annualized_return = 0
    
    # Additional metrics
    volatility = df['daily_return'].std() * np.sqrt(252) if len(df) > 1 else 0
    sharpe_ratio = annualized_return / volatility if volatility != 0 else 0
    
    # Maximum drawdown
    running_max = df['account_value'].expanding().max()
    drawdown = (df['account_value'] - running_max) / running_max
    max_drawdown = drawdown.min()
    
    return {
        'total_return_pct': total_return * 100,
        'annualized_return_pct': annualized_return * 100,
        'volatility_pct': volatility * 100,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown_pct': max_drawdown * 100,
        'trading_days': total_days,
        'start_value': df['account_value'].iloc[0],
        'end_value': df['account_value'].iloc[-1]
    }

def calculate_buy_and_hold(test_df, initial_amount=10000,
                           buy_cost_pct=0.0025, sell_cost_pct=0.0025):
    """
    Buy-and-hold benchmark on the SAME terms as the PPO agent:
      - integer shares only (PPO is integer-constrained, so B&H must be too)
      - transaction costs on entry and exit
      - residual cash kept (not magically assumed away)
    """
    symbols = test_df['tic'].unique()
    allocation_per_stock = initial_amount / len(symbols)
    total_final_value = 0.0

    for symbol in symbols:
        symbol_data = test_df[test_df['tic'] == symbol].sort_values('date')
        if len(symbol_data) == 0:
            continue
        first_price = float(symbol_data['close'].iloc[0])
        last_price  = float(symbol_data['close'].iloc[-1])
        if first_price <= 0:
            continue

        # Buy as many integer shares as the per-stock allocation can afford,
        # accounting for the 0.25% buy cost.
        shares = int(allocation_per_stock // (first_price * (1 + buy_cost_pct)))
        invested = shares * first_price * (1 + buy_cost_pct)
        residual_cash = allocation_per_stock - invested

        # Liquidate at the end at last close, paying the 0.25% sell cost.
        final_position_value = shares * last_price * (1 - sell_cost_pct)
        total_final_value += final_position_value + residual_cash

    buy_hold_return = (total_final_value / initial_amount - 1) * 100

    return {
        'initial_value': initial_amount,
        'final_value': total_final_value,
        'total_return_pct': buy_hold_return,
        'strategy': 'Equal Weight Buy & Hold (integer shares, with costs)'
    }

def create_comprehensive_report(df_account_value, trade_logger, test_df, stock_name, output_dir):
    """
    Create comprehensive performance report with win rate
    """
    report_path = os.path.join(output_dir, f"{stock_name}_report.txt")
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("\n" + "="*80 + "\n")
        f.write(f"COMPREHENSIVE TRADING PERFORMANCE REPORT FOR {stock_name}\n")
        f.write("="*80 + "\n")
        
        # PPO Strategy Performance
        ppo_metrics = calculate_yearly_returns(df_account_value)
        
        f.write("\n📊 PPO STRATEGY PERFORMANCE\n")
        f.write("-" * 40 + "\n")
        f.write(f"Initial Portfolio Value: ₹{ppo_metrics.get('start_value', 0):,.2f}\n")
        f.write(f"Final Portfolio Value: ₹{ppo_metrics.get('end_value', 0):,.2f}\n")
        f.write(f"Total Return: {ppo_metrics.get('total_return_pct', 0):.2f}%\n")
        f.write(f"Annualized Return: {ppo_metrics.get('annualized_return_pct', 0):.2f}%\n")
        f.write(f"Volatility (Annualized): {ppo_metrics.get('volatility_pct', 0):.2f}%\n")
        f.write(f"Sharpe Ratio: {ppo_metrics.get('sharpe_ratio', 0):.3f}\n")
        f.write(f"Maximum Drawdown: {ppo_metrics.get('max_drawdown_pct', 0):.2f}%\n")
        f.write(f"Trading Days: {ppo_metrics.get('trading_days', 0)}\n")
        
        # Buy and Hold Performance
        buy_hold_metrics = calculate_buy_and_hold(test_df, ppo_metrics.get('start_value', 10000))
        
        f.write(f"\n📈 BUY & HOLD STRATEGY PERFORMANCE\n")
        f.write("-" * 40 + "\n")
        f.write(f"Strategy: {buy_hold_metrics['strategy']}\n")
        f.write(f"Initial Portfolio Value: ₹{buy_hold_metrics['initial_value']:,.2f}\n")
        f.write(f"Final Portfolio Value: ₹{buy_hold_metrics['final_value']:,.2f}\n")
        f.write(f"Total Return: {buy_hold_metrics['total_return_pct']:.2f}%\n")
        
        # Strategy Comparison
        f.write(f"\n🔄 STRATEGY COMPARISON\n")
        f.write("-" * 40 + "\n")
        ppo_return = ppo_metrics.get('total_return_pct', 0)
        bh_return = buy_hold_metrics['total_return_pct']
        outperformance = ppo_return - bh_return
        
        f.write(f"PPO Strategy Return: {ppo_return:.2f}%\n")
        f.write(f"Buy & Hold Return: {bh_return:.2f}%\n")
        f.write(f"Outperformance: {outperformance:.2f}%\n")
        
        if outperformance > 0:
            f.write("✅ PPO Strategy OUTPERFORMED Buy & Hold\n")
        else:
            f.write("❌ PPO Strategy UNDERPERFORMED Buy & Hold\n")
        
        # Trade Summary with Win Rate
        trade_summary = trade_logger.get_trade_summary()
        
        f.write(f"\n📋 TRADE SUMMARY & ACCURACY\n")
        f.write("-" * 40 + "\n")
        f.write(f"Total Trades: {trade_summary.get('total_trades', 0)}\n")
        f.write(f"Buy Trades: {trade_summary.get('buy_trades', 0)}\n")
        f.write(f"Sell Trades: {trade_summary.get('sell_trades', 0)}\n")
        f.write(f"Total Transaction Costs: ₹{trade_summary.get('total_transaction_costs', 0):,.2f}\n")
        f.write(f"Average Cost per Trade: ₹{trade_summary.get('avg_cost_per_trade', 0):.2f}\n")
        f.write(f"\n🎯 TRADING ACCURACY:\n")
        f.write(f"Winning Trades: {trade_summary.get('winning_trades', 0)}\n")
        f.write(f"Losing Trades: {trade_summary.get('losing_trades', 0)}\n")
        f.write(f"Win Rate: {trade_summary.get('win_rate_pct', 0):.2f}%\n")
        f.write(f"Total Closed Trades: {trade_summary.get('total_closed_trades', 0)}\n")
    
    print(f"  Report saved to: {report_path}")
    return ppo_metrics, buy_hold_metrics, trade_summary

def process_stock(file_path):
    """
    Process a single stock from file loading to reporting
    Returns stock results for consolidated report
    """
    stock_name = os.path.basename(file_path).split("_")[0]
    stock_result_dir = os.path.join(RESULTS_DIR, stock_name)
    os.makedirs(stock_result_dir, exist_ok=True)

    print(f"\n{'='*50}")
    print(f"PROCESSING {stock_name}")
    print(f"{'='*50}")

    # Resume support: if a final report already exists for this stock,
    # skip everything. Used when re-running after a failure mid-portfolio.
    existing_report = os.path.join(stock_result_dir, f"{stock_name}_report.txt")
    if os.path.exists(existing_report):
        print(f"  Skipping {stock_name} — report already exists at {existing_report}")
        return None

    # Per-stock global seeding so each stock is independently reproducible.
    # v6/v7 only seeded PPO; numpy/random/torch were free-running.
    SEED = 42
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)

    try:
        # Step 1: Load data
        print(f"  Loading data from: {file_path}")
        df = pd.read_csv(file_path)
        
        # Ensure datetime index
        if 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'])
            df = df.set_index('datetime')
            df = df.sort_index()
        
        # Add symbol column
        df['symbol'] = stock_name
        
        # Step 2: Calculate technical indicators on the full OHLCV series.
        #
        # NOTE on leakage: this is safe ONLY because list_of_indicators has been
        # pruned to causal-only names in v8. For a causal indicator, value[t]
        # depends only on bars <= t, so computing on the full series gives the
        # same numbers as computing on train and test separately. If you ever
        # add a non-causal indicator (centered MA, lookahead-default like DPO,
        # etc.), this MUST be replaced with per-split computation (compute on
        # train, then on test with a warmup prefix from train, then drop the
        # warmup rows).
        try:
            df.ta.cores = 0
        except Exception:
            pass
        df.ta.study(ta.AllStudy, cores=0)
        
        # Filter to keep only your desired indicators
        basic_cols = ['symbol', 'open', 'high', 'low', 'close', 'volume']
        existing_indicators = [col for col in list_of_indicators if col in df.columns]
        columns_to_keep = basic_cols + existing_indicators
        df = df[columns_to_keep]
        
        # Step 3: Handle NaN values
        print("  Handling NaN values...")
        df, indicator_cols = handle_nan_per_stock(df)
        
        # Skip stocks with insufficient data
        if len(df) < MIN_DATA_ROWS:
            raise ValueError(f"Insufficient data ({len(df)} rows) after cleaning. Minimum {MIN_DATA_ROWS} required.")
        
        # Step 4: Format conversion only — no scaling yet (needed to determine split date)
        print("  Preparing data for FinRL...")
        processed_raw, tech_indicators, _ = prepare_data_for_finrl(df, skip_scaling=True)

        # Step 5: Split data (80/20 per stock timeline)
        unique_dates = sorted(processed_raw['date'].unique())
        split_index = int(len(unique_dates) * 0.8)
        split_date = unique_dates[split_index]

        train_raw = processed_raw[processed_raw['date'] < split_date].reset_index(drop=True)
        test_raw  = processed_raw[processed_raw['date'] >= split_date].reset_index(drop=True)

        # Fit scaler on training data only, then apply the same scaler to test data.
        # Fitting on all data before splitting leaks future statistics into the model.
        train_df, _, scalers = prepare_data_for_finrl(train_raw, scalers=None,    skip_scaling=False)
        test_df,  _, _       = prepare_data_for_finrl(test_raw,  scalers=scalers, skip_scaling=False)
        
        print(f"  Split at {split_date}:")
        print(f"    Training: {len(train_df)} rows ({len(train_df['date'].unique())} dates)")
        print(f"    Testing:  {len(test_df)} rows ({len(test_df['date'].unique())} dates)")
        
        # Step 6: Train PPO model
        model, vecnorm, hmax_value = train_ppo_model(train_df, tech_indicators, stock_name)

        # Save model and VecNormalize stats so test reproduces train-time obs scaling
        model_path = os.path.join(TRAINED_MODEL_DIR, f"{stock_name}_ppo.zip")
        model.save(model_path)
        vecnorm_path = os.path.join(TRAINED_MODEL_DIR, f"{stock_name}_vecnorm.pkl")
        vecnorm.save(vecnorm_path)
        print(f"  Model saved to: {model_path}")
        print(f"  VecNormalize stats saved to: {vecnorm_path}")

        # Step 7: Test model
        df_account_value, df_actions, trade_logger = test_ppo_model(
            model, test_df, tech_indicators, stock_name,
            vecnorm_path=vecnorm_path, hmax_value=hmax_value
        )
        
        # Step 8: Generate report
        ppo_metrics, buy_hold_metrics, trade_summary = create_comprehensive_report(
            df_account_value, trade_logger, test_df, stock_name, stock_result_dir
        )
        
        # Save outputs
        df_account_value.to_csv(os.path.join(stock_result_dir, "account_value.csv"), index=False)
        trade_logbook = trade_logger.get_trade_logbook()
        if not trade_logbook.empty:
            trade_logbook.to_csv(os.path.join(stock_result_dir, "trades.csv"), index=False)
        
        print(f"  Results saved to: {stock_result_dir}")
        
        # Return results for consolidation
        return {
            'stock': stock_name,
            'final_value': ppo_metrics['end_value'],
            'buy_hold_value': buy_hold_metrics['final_value'],
            'win_rate': trade_summary['win_rate_pct'],
            'transaction_costs': trade_summary['total_transaction_costs'],
            'total_trades': trade_summary['total_trades'],
            'closed_trades': trade_summary['total_closed_trades'],
            'winning_trades': trade_summary['winning_trades']
        }
        
    except Exception as e:
        print(f"  ⚠️ Error processing {stock_name}: {str(e)}")
        return None

def generate_consolidated_report(stock_results):
    """
    Generate consolidated portfolio report
    """
    # Filter out failed stocks
    valid_results = [r for r in stock_results if r is not None]
    
    if not valid_results:
        print("\nNo valid results to consolidate!")
        return
    
    total_final_value = sum(r['final_value'] for r in valid_results)
    total_buy_hold_value = sum(r['buy_hold_value'] for r in valid_results)
    total_transaction_costs = sum(r['transaction_costs'] for r in valid_results)
    
    # Calculate overall win rate
    total_winning_trades = sum(r['winning_trades'] for r in valid_results)
    total_closed_trades = sum(r['closed_trades'] for r in valid_results)
    overall_win_rate = (total_winning_trades / total_closed_trades * 100) if total_closed_trades > 0 else 0
    
    # Portfolio returns
    initial_investment = 10000 * len(valid_results)
    portfolio_return = (total_final_value / initial_investment - 1) * 100
    buy_hold_return = (total_buy_hold_value / initial_investment - 1) * 100
    outperformance = portfolio_return - buy_hold_return
    
    with open(CONSOLIDATED_REPORT, 'w', encoding='utf-8') as f:
        f.write("\n" + "="*80 + "\n")
        f.write("PORTFOLIO PERFORMANCE REPORT (NIFTY50 STOCKS)\n")
        f.write("="*80 + "\n\n")
        
        f.write(f"Stocks Processed: {len(valid_results)} out of 50\n")
        f.write(f"Initial Investment: ₹{initial_investment:,.2f}\n")
        f.write(f"Final Portfolio Value: ₹{total_final_value:,.2f}\n")
        f.write(f"Buy & Hold Value: ₹{total_buy_hold_value:,.2f}\n")
        f.write(f"Total Transaction Costs: ₹{total_transaction_costs:,.2f}\n\n")
        
        f.write(f"Portfolio Return: {portfolio_return:.2f}%\n")
        f.write(f"Buy & Hold Return: {buy_hold_return:.2f}%\n")
        f.write(f"Outperformance: {outperformance:.2f}%\n\n")
        
        f.write(f"Overall Win Rate: {overall_win_rate:.2f}%\n")
        f.write(f"Total Closed Trades: {total_closed_trades}\n")
        f.write(f"Winning Trades: {total_winning_trades}\n")
        f.write(f"Losing Trades: {total_closed_trades - total_winning_trades}\n\n")
        
        f.write("Per Stock Results:\n")
        f.write("-"*50 + "\n")
        for r in valid_results:
            f.write(f"{r['stock']}:\n")
            f.write(f"  Final Value: ₹{r['final_value']:,.2f}\n")
            f.write(f"  Buy&Hold: ₹{r['buy_hold_value']:,.2f}\n")
            f.write(f"  Win Rate: {r['win_rate']:.2f}%\n")
            f.write(f"  Transaction Costs: ₹{r['transaction_costs']:,.2f}\n\n")
    
    print("\n" + "="*80)
    print(f"CONSOLIDATED REPORT SAVED TO: {CONSOLIDATED_REPORT}")
    print("="*80)

def main():
    """
    Main execution function for portfolio processing
    """
    print("\n" + "="*80)
    print("NIFTY50 PORTFOLIO PPO TRADING SYSTEM")
    print("="*80)
    print(f"Data Directory: {NIFTY50_PATH}")
    print(f"Models Directory: {TRAINED_MODEL_DIR}")
    print(f"Results Directory: {RESULTS_DIR}")
    print(f"Minimum Data Requirement: {MIN_DATA_ROWS} rows per stock\n")
    
    # Find all stock files
    stock_files = glob.glob(os.path.join(NIFTY50_PATH, "*_daily.csv"))
    if not stock_files:
        print("No stock files found! Check directory path.")
        return
    
    print(f"Found {len(stock_files)} stock files")
    
    stock_results = []
    processed_count = 0
    start_time = time.time()
    
    for file_path in stock_files:
        stock_start = time.time()
        result = process_stock(file_path)
        
        if result:
            stock_results.append(result)
            processed_count += 1
            print(f"✅ Completed in {time.time() - stock_start:.1f} seconds")
        else:
            print(f"⚠️ Skipped {os.path.basename(file_path)}")
    
    # Generate consolidated report
    generate_consolidated_report(stock_results)
    
    total_time = time.time() - start_time
    print("\n" + "="*80)
    print(f"PORTFOLIO PROCESSING COMPLETE!")
    print(f"Stocks Processed: {processed_count}/{len(stock_files)}")
    print(f"Total Time: {total_time/60:.1f} minutes")
    print(f"Average per Stock: {total_time/processed_count:.1f} seconds" if processed_count else "")
    print("="*80)

if __name__ == "__main__":
    main()