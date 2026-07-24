@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo Virtual environment not found. Run installer.vbs or install.bat first.
    pause
    exit /b 1
)
if not exist "frontend\dist\index.html" (
    echo Frontend build not found. Run installer.vbs first.
    pause
    exit /b 1
)

set "PYTHON=%~dp0venv\Scripts\python.exe"
set "PYTHONUNBUFFERED=1"
set "STARTUP_LOG=%~dp0startup-error.log"

echo Checking backend startup...
cd /d "%~dp0backend"
"%PYTHON%" -c "import app.main; print('Backend import OK')" > "%STARTUP_LOG%" 2>&1
if errorlevel 1 (
    echo.
    echo Backend import failed. Details are in startup-error.log
    type "%STARTUP_LOG%"
    pause
    exit /b 1
)

cd /d "%~dp0"
echo Starting MrPackMaker on http://localhost:8000
start "" /b powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 2; Start-Process 'http://localhost:8000'"
cd /d "%~dp0backend"
"%PYTHON%" run.py >> "%~dp0startup-error.log" 2>&1
set "EXIT_CODE=%ERRORLEVEL%"
cd /d "%~dp0"
if not "%EXIT_CODE%"=="0" (
    echo.
    echo MrPackMaker stopped with exit code %EXIT_CODE%.
    echo Details are in startup-error.log
    type "%STARTUP_LOG%"
)
pause
exit /b %EXIT_CODE%
