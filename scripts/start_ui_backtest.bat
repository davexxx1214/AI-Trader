@echo off
REM AI-Trader Web UI - Backtest Mode
REM Displays data from data\agent_data

echo.
echo ============================================================
echo   AI-Trader Web UI - Backtest Mode
echo ============================================================
echo.

cd /d "%~dp0.."
python scripts/start_ui.py --mode backtest %*

