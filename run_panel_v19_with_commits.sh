#!/bin/bash
# run_panel_v19_with_commits.sh
# Runs v19 on all panel stocks sequentially, committing after each.
# Skip stocks that already have results_v19/{STOCK}/{STOCK}_report.txt

set -e

PANEL="RELIANCE INFY TATAMOTORS ITC ADANIENT HDFCBANK TCS SBIN AXISBANK HINDALCO"

export RESULTS_DIR=results_v19
export TRAINED_MODEL_DIR=models_v19
export CONSOLIDATED_REPORT=consolidated_report_v19.txt

mkdir -p results_v19 models_v19

for STOCK in $PANEL; do
    REPORT="results_v19/${STOCK}/${STOCK}_report.txt"
    if [ -f "$REPORT" ]; then
        echo "=== SKIPPING $STOCK (report exists) ==="
        continue
    fi

    echo "=== STARTING $STOCK at $(date -u) ==="
    python -c "
import os
os.environ['RESULTS_DIR'] = 'results_v19'
os.environ['TRAINED_MODEL_DIR'] = 'models_v19'
os.environ['CONSOLIDATED_REPORT'] = 'consolidated_report_v19.txt'
from Rl_v19 import process_stock, NIFTY50_PATH
result = process_stock(os.path.join(NIFTY50_PATH, '${STOCK}_daily.csv'))
print('${STOCK} result:', result)
" 2>&1

    if [ -f "$REPORT" ]; then
        echo "=== COMMITTING $STOCK results ==="
        git add "results_v19/${STOCK}/" || true
        git commit -m "feat(v19): add ${STOCK} panel result

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01K2omCM9EYQ3dEvv5y1X8oD" || true
        git push origin auto/run-b || git push origin auto/run-b || true
    else
        echo "=== WARNING: $STOCK report not found after training ==="
    fi
    echo "=== DONE $STOCK at $(date -u) ==="
done

echo "=== PANEL COMPLETE. Generating consolidated report... ==="
python -c "
import os
os.environ['RESULTS_DIR'] = 'results_v19'
os.environ['TRAINED_MODEL_DIR'] = 'models_v19'
os.environ['CONSOLIDATED_REPORT'] = 'consolidated_report_v19.txt'
from Rl_v19 import generate_consolidated_report
generate_consolidated_report([])
" 2>&1 || true

echo "=== Summarizing results... ==="
python summarize_results.py results_v19 2>&1 || true

echo "ALL DONE at $(date -u)"
