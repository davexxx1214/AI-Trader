@echo off
REM Auto-update US stock hourly price data
REM Usage: scripts\update_us_prices.bat

echo.
echo ============================================================
echo   US Stock Price Data Auto-Updater
echo ============================================================
echo.

cd /d "%~dp0..\data"
python update_prices.py %*

echo.
echo Running merge_jsonl.py to update merged data...
python merge_jsonl.py

echo.
echo Done!
pause

