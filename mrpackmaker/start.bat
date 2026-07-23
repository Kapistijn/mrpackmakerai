@echo off
setlocal
cd /d "%~dp0"

REM Relaunch MrPackMaker after it has already been installed.
if not exist venv (
    echo Virtual environment not found. Run installer.vbs (or install.bat) first.
    pause
    exit /b 1
)
if not exist frontend\dist (
    echo Frontend build not found. Run installer.vbs first ^(it runs npm run build^).
    pause
    exit /b 1
)

echo Starting MrPackMaker on http://localhost:8000
start "" /b powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 2; Start-Process 'http://localhost:8000'"
cd backend
"..\venv\Scripts\python.exe" run.py

pause
