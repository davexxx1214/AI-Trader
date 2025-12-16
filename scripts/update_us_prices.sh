#!/bin/bash
# Auto-update US stock hourly price data
# Usage: bash scripts/update_us_prices.sh

echo ""
echo "============================================================"
echo "  US Stock Price Data Auto-Updater"
echo "============================================================"
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/../data"

python3 update_prices.py "$@"

echo ""
echo "Running merge_jsonl.py to update merged data..."
python3 merge_jsonl.py

echo ""
echo "Done!"

