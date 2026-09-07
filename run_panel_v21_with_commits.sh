#!/bin/bash
# Run v21 panel one stock at a time, committing after each
# Skips stocks that already have results_v21/{STOCK}/{STOCK}_report.txt
set -e

PANEL="RELIANCE INFY TATAMOTORS ITC ADANIENT HDFCBANK TCS SBIN AXISBANK HINDALCO"

for STOCK in $PANEL; do
    REPORT="results_v21/$STOCK/${STOCK}_report.txt"
    if [ -f "$REPORT" ]; then
        echo "=== SKIP $STOCK (report exists) ==="
        continue
    fi
    echo "=== START $STOCK at $(date -u) ==="
    python run_one_v21.py "$STOCK"
    EXIT=$?
    echo "=== END $STOCK exit=$EXIT at $(date -u) ==="

    if [ $EXIT -eq 0 ] && [ -f "$REPORT" ]; then
        git add "results_v21/$STOCK/" 2>/dev/null || true
        git add "autoresearch/HANDOFF.run-b.md" 2>/dev/null || true
        git commit -m "auto/run-b: v21 panel - ${STOCK} done

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01Hze4AATiZsWLs1Qi1M5VSc" || true
        git push origin auto/run-b || true
        echo "=== COMMITTED $STOCK ==="
    else
        echo "=== WARNING: $STOCK may have failed (exit=$EXIT, report exists=$([ -f $REPORT ] && echo yes || echo no)) ==="
    fi
done

echo "=== PANEL COMPLETE at $(date -u) ==="
