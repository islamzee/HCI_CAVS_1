@echo off
rem Double-click to stop the CAVS-1 pod
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-windows.ps1" -Stop
pause
