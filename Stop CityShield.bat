@echo off
REM Stop the CityShield / VisionScan stack (your data + models are kept).
title Stop CityShield
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop.ps1"
pause
