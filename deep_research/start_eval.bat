@echo off
rem DeepResearch eval launcher (double-click me)
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0eval_run.ps1"
echo.
pause
