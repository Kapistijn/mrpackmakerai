@echo off
REM Thin launcher for the PowerShell installer (beta 1.6.0).
REM The installer engine lives in scripts\install.ps1 to keep the root clean.
REM -ExecutionPolicy Bypass is scoped to this single run and changes nothing
REM system-wide.
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install.ps1"
if errorlevel 1 (
    echo.
    echo The installer reported an error. See install-log.txt for details.
    pause
)
