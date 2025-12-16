@echo off
REM AI-Trader Web UI - Live Trading Mode
REM Displays data from data\agent_data_live

echo.
echo ============================================================
echo   AI-Trader Web UI - Live Trading Mode
echo ============================================================
echo.

cd /d "%~dp0.."
python scripts/start_ui.py --mode live %*

