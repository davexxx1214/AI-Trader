#!/bin/bash
# AI-Trader Web UI Launcher
# 
# Usage:
#   ./scripts/start_ui.sh                    # Default backtest mode
#   ./scripts/start_ui.sh --mode live        # Live trading mode
#   ./scripts/start_ui.sh -m live -p 9000    # Live mode on port 9000
#
# For dedicated scripts:
#   ./scripts/start_ui_backtest.sh           # Backtest mode
#   ./scripts/start_ui_live.sh               # Live trading mode

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/.."

python3 scripts/start_ui.py "$@"

