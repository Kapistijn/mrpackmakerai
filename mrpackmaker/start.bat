@echo off
REM Thin launcher for the PowerShell start engine (2.5.4).
REM The startup logic lives in scripts\start.ps1 so we avoid the cmd/PowerShell
REM quoting bug that crashed the old inline command with
REM "The ampersand (&) character is not allowed" (AmpersandNotAllowed):
REM cmd does not strip the ^ carets in "2^>^&1" inside a double-quoted -Command,
REM so PowerShell received them verbatim. Running a real .ps1 with -File fixes it.
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start.ps1"
if errorlevel 1 (
    echo.
    echo MrPackMaker exited with an error. See startup-error.log for details.
    pause
)
