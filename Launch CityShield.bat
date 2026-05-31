@echo off
REM ============================================================
REM  CityShield / VisionScan - one double-click launcher.
REM  Double-click this file to:
REM    1. start Docker Desktop (if it isn't running),
REM    2. build + start the whole stack,
REM    3. open the platform in your browser.
REM  First run can take 10-15 min (downloads AI models). Later
REM  runs take seconds. Leave this window open while it works.
REM ============================================================
title CityShield Launcher
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"

echo.
echo ------------------------------------------------------------
echo  This window can be closed - the app keeps running in Docker.
echo  To stop it later, double-click "Stop CityShield.bat".
echo ------------------------------------------------------------
pause
