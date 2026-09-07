"""Single-stock runner for v21 panel - sets env vars before module import."""
import sys
import os

os.environ["RESULTS_DIR"] = "results_v21"
os.environ["TRAINED_MODEL_DIR"] = "models_v21"
os.environ["CONSOLIDATED_REPORT"] = "consolidated_report_v21.txt"

import Rl_v21

stock = sys.argv[1]
path = os.path.join(Rl_v21.NIFTY50_PATH, f"{stock}_daily.csv")
result = Rl_v21.process_stock(path)
print(f"DONE: {stock} = {result}")
