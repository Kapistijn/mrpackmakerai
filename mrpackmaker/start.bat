@echo off
setlocal
cd /d "%~dp0"

REM Relaunch MrPackMaker after it has already been installed with installer.bat.
if not exist venv (
    echo Virtual environment not found. Run installer.bat first.
    pause
    exit /b 1
)
if not exist frontend\dist (
    echo Frontend build not found. Run installer.bat first ^(it runs npm run build^).
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

echo Starting MrPackMaker on http://localhost:8000
start "" /b powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 2; Start-Process 'http://localhost:8000'"
cd backend
python run.py

pause
