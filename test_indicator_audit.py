"""
test_indicator_audit.py — static audit of `list_of_indicators` for known
lookahead-leakage names.

Why this exists: v6/v7 silently included DPO_20, AMATe_LR/SR_*, AOBV_LR/SR_*,
PSARr, TTM_TRND_6, STC family, etc. — all of which use `lookahead=True` in
pandas-ta or are centered/forward-shifted by construction. They produced fake
+1946% returns on ADANIPORTS before the leakage was found. The fix in v8 was
to drop them. This test prevents regression by failing if any known-leakage
name reappears in the active list.

Run:
    python test_indicator_audit.py

Or:
    python -m unittest test_indicator_audit

Exit code 0 = clean, 1 = leakage detected.
"""

import unittest
import importlib

# Confirmed-leakage indicator names that must NOT be in list_of_indicators.
# Source: external lookahead audit (see CLAUDE.md "Critical bug history" #3).
KNOWN_LEAKAGE = {
    "DPO_20": "pandas-ta defaults lookahead=True; encodes future close",
    "AMATe_LR_8_21_2": "Archer MAT trend, centered-aligned trend confirmation",
    "AMATe_SR_8_21_2": "same construction",
    "AOBV_LR_2": "Archer OBV calls amat()",
    "AOBV_SR_2": "same",
    "PSARr_0.02_0.2": "PSAR reversal flag set on bar where reversal becomes visible",
    "TTM_TRND_6": "possibly center-aligned trend signal",
    "DEC_1": "some pandas-ta versions compute close.diff(length).shift(-length)",
    "INC_1": "same",
    "STC_10_12_26_0.5": "STC initialises with forward-fill across whole series",
    "STCmacd_10_12_26_0.5": "same",
    "STCstoch_10_12_26_0.5": "same",
    "FISHERTs_9_1": "fisher signal column shifted forward in some versions",
    "EBSW_40_10": "Ehlers super-smoother is non-causal in published form",
    "COPC_11_14_10": "verify pandas-ta isn't applying a center-aligned WMA",
}

# Active version files to audit (CURRENT + recent variants).
# v6/v7 had leakage by design — they are frozen history and intentionally
# exempt from this check.
ACTIVE_MODULES = [
    "Rl_v8", "Rl_v9", "Rl_v10", "Rl_v11", "Rl_v12", "Rl_v13", "Rl_v14",
    "Rl_v15", "Rl_v16", "Rl_v17", "Rl_v18", "Rl_v19", "Rl_v20", "Rl_v21",
    "Rl_v22", "Rl_v23", "Rl_v24",
]


class IndicatorAuditTest(unittest.TestCase):

    def test_no_leakage_in_active_versions(self):
        violations = []  # (module_name, indicator_name, reason)
        for mod_name in ACTIVE_MODULES:
            try:
                mod = importlib.import_module(mod_name)
            except ModuleNotFoundError:
                continue
            indicators = getattr(mod, "list_of_indicators", None)
            if indicators is None:
                continue
            for name in indicators:
                if name in KNOWN_LEAKAGE:
                    violations.append((mod_name, name, KNOWN_LEAKAGE[name]))

        if violations:
            msg_lines = ["Lookahead-leakage indicators detected:"]
            for mod_name, ind, reason in violations:
                msg_lines.append(f"  {mod_name}: '{ind}' — {reason}")
            self.fail("\n".join(msg_lines))

    def test_at_least_one_module_has_indicators(self):
        """Sanity: at least one module should expose `list_of_indicators`.
        Catches the case where renaming/refactoring breaks the import path."""
        found = False
        for mod_name in ACTIVE_MODULES:
            try:
                mod = importlib.import_module(mod_name)
            except ModuleNotFoundError:
                continue
            if hasattr(mod, "list_of_indicators"):
                found = True
                break
        self.assertTrue(found, "No active module exposes `list_of_indicators`.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
