@echo off
echo Starting Arzana Outlook Monitor (Delegated Permissions)...
echo.
echo If this is your first time running, a browser will open for login.
echo.
powershell.exe -ExecutionPolicy Bypass -NoExit -File "%~dp0ArzanaGraphMonitor_Delegated.ps1"
pause
