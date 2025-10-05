@echo off
echo Starting Arzana Outlook Monitor as Administrator...
echo.
echo This will monitor your Outlook for PO emails and process them automatically.
echo Press Ctrl+C to stop the monitor.
echo.
pause
powershell -ExecutionPolicy Bypass -Command "Start-Process powershell -Verb RunAs -ArgumentList '-ExecutionPolicy Bypass -File \"%~dp0ArzanaOutlookMonitor.ps1\" -FlaskServerUrl \"https://bx3w2xz6f6.us-east-1.awsapprunner.com\" -CheckIntervalSeconds 60'"
