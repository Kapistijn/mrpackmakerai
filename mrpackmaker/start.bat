@echo off
REM Thin launcher for the PowerShell start engine (2.5.6).
REM Startup uses scripts\start.ps1 to keep native stdout/stderr handling clean.
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start.ps1"
set "exitCode=%errorlevel%"
if not "%exitCode%"=="0" (
    echo.
    echo MrPackMaker exited with an error. See startup-error.log for details.
    pause
)
exit /b %exitCode%
