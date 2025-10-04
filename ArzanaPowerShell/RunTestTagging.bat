@echo off
echo Running Test Tagging Script as Administrator...
echo.
powershell -ExecutionPolicy Bypass -Command "Start-Process powershell -Verb RunAs -ArgumentList '-ExecutionPolicy Bypass -File \"%~dp0TestTagging.ps1\"'"
