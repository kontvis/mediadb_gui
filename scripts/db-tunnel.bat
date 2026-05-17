@echo off
REM Run the SSH tunnel via PowerShell (works from CMD or double-click).
cd /d "%~dp0\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0db-tunnel.ps1"
if errorlevel 1 pause
