@echo off
echo Starting Arzana Outlook Monitor (Graph API version)...
echo.
powershell.exe -ExecutionPolicy Bypass -NoExit -File "%~dp0ArzanaGraphMonitor.ps1"
pause
