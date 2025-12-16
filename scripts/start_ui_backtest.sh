#!/bin/bash
# AI-Trader Web UI - Backtest Mode
# Displays data from data/agent_data

echo ""
echo "============================================================"
echo "  AI-Trader Web UI - Backtest Mode"
echo "============================================================"
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/.."

python3 scripts/start_ui.py --mode backtest "$@"

