@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-CVPilot.ps1"
if errorlevel 1 (
  echo CV Pilot could not start. See the error above.
  pause
)
