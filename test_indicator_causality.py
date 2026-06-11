"""
test_indicator_causality.py — dynamic lookahead-leakage audit.

The static audit (`test_indicator_audit.py`) checks `list_of_indicators`
against a hardcoded known-leakage list. This test is the stronger, dynamic
version proposed in CLAUDE.md: compute every kept indicator on the train
prefix ALONE and on the FULL series, then assert the two agree on the train
prefix. A causal indicator's value at row t depends only on rows <= t, so
appending future rows must not change any prefix value. Any mismatch means
future data is bleeding backwards (lookahead/centering/whole-series fit).

Runtime is dominated by two pandas-ta AllStudy passes (~2 min each), so this
audits ONE representative stock (RELIANCE by default, override via
CAUSALITY_SYMBOL). Run it when bumping pandas-ta or editing the indicator
list, not on every commit:

    python test_indicator_causality.py
"""

import os
import unittest

import numpy as np
import pandas as pd
import pandas_ta as ta

from Rl_v18 import list_of_indicators, NIFTY50_PATH

SYMBOL = os.environ.get("CAUSALITY_SYMBOL", "RELIANCE")
TRAIN_FRAC = 0.70
# Ignore this many rows at the start of the comparison window: indicator
# warmup regions are NaN/seed-dependent and not what we are testing.
WARMUP_ROWS = 300
RTOL, ATOL = 1e-6, 1e-8


def _compute_indicators(df):
    out = df.copy()
    out.ta.cores = 0
    out.ta.study(ta.AllStudy, cores=0)
    return out


class IndicatorCausalityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.path.join(NIFTY50_PATH, f"{SYMBOL}_daily.csv")
        if not os.path.exists(path):
            raise unittest.SkipTest(f"data file not found: {path}")
        df = pd.read_csv(path)
        df["datetime"] = pd.to_datetime(df["datetime"])
        df = df.set_index("datetime").sort_index()
        df = df[["open", "high", "low", "close", "volume"]]

        split = int(len(df) * TRAIN_FRAC)
        cls.full = _compute_indicators(df)
        cls.prefix = _compute_indicators(df.iloc[:split])
        cls.split = split

    def test_kept_indicators_are_causal(self):
        kept = [c for c in list_of_indicators
                if c in self.full.columns and c in self.prefix.columns]
        self.assertGreater(len(kept), 50,
                           "indicator intersection suspiciously small — "
                           "did pandas-ta change its column names?")

        # Compare on the prefix rows past the warmup region.
        idx = self.prefix.index[WARMUP_ROWS:]
        leaky = []
        for col in kept:
            a = self.prefix.loc[idx, col].to_numpy(dtype=np.float64)
            b = self.full.loc[idx, col].to_numpy(dtype=np.float64)
            if not np.allclose(a, b, rtol=RTOL, atol=ATOL, equal_nan=True):
                n_diff = int(np.sum(~np.isclose(a, b, rtol=RTOL, atol=ATOL,
                                                equal_nan=True)))
                leaky.append(f"{col} ({n_diff}/{len(a)} rows differ)")

        self.assertFalse(
            leaky,
            "Lookahead leakage: these kept indicators change on the train "
            "prefix when future rows are appended:\n  " + "\n  ".join(leaky),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
