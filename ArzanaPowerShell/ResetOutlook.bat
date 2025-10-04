@echo off
echo Resetting Outlook...
echo.

REM Try common Outlook installation paths
if exist "C:\Program Files\Microsoft Office\root\Office16\OUTLOOK.EXE" (
    "C:\Program Files\Microsoft Office\root\Office16\OUTLOOK.EXE" /resetnavpane
    goto :done
)

if exist "C:\Program Files (x86)\Microsoft Office\root\Office16\OUTLOOK.EXE" (
    "C:\Program Files (x86)\Microsoft Office\root\Office16\OUTLOOK.EXE" /resetnavpane
    goto :done
)

if exist "C:\Program Files\Microsoft Office\Office16\OUTLOOK.EXE" (
    "C:\Program Files\Microsoft Office\Office16\OUTLOOK.EXE" /resetnavpane
    goto :done
)

if exist "C:\Program Files (x86)\Microsoft Office\Office16\OUTLOOK.EXE" (
    "C:\Program Files (x86)\Microsoft Office\Office16\OUTLOOK.EXE" /resetnavpane
    goto :done
)

echo Could not find Outlook installation
echo Please open Outlook manually and then try running the monitor
pause
exit

:done
echo Outlook reset command sent
echo.
echo Now:
echo 1. Wait for Outlook to open
echo 2. Close this window
echo 3. Run Start-ArzanaMonitor.bat as Administrator
pause
