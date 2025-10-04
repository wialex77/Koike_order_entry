@echo off
echo Installing required packages...
pip install -r requirements.txt

echo.
echo Starting Arzana Outlook Monitor...
echo If this is your first time, a browser will open for login.
echo.

python graph_monitor.py
pause
