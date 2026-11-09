@echo off
rem Double-click to start the CAVS-1 bag player + bridge (opens http://localhost:8765/)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-windows.ps1" %*
pause
