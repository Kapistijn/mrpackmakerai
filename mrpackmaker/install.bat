@echo off
REM Thin launcher for the PowerShell installer (beta 1.5.2).
REM Using -ExecutionPolicy Bypass means the user does not have to change any
REM system policy for this one script; it does not persist any setting.
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
if errorlevel 1 (
    echo.
    echo The installer reported an error. See install-log.txt for details.
    pause
)
