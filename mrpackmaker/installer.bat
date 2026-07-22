@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ========================================
echo MrPackMaker Installer (beta 1.5.1)
echo ========================================
echo.
echo Tip: if this window ever seems frozen, click inside it and press a key.
echo Windows console "QuickEdit" pauses output when text is selected.
echo.

REM Check Python
echo [1/7] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.10 or higher from https://python.org
    pause
    exit /b 1
)
python --version
echo.

REM Check Node.js
echo [2/7] Checking Node.js installation...
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js is not installed or not in PATH
    echo Please install Node.js 18 or higher from https://nodejs.org
    pause
    exit /b 1
)
node --version
echo.

REM Create virtual environment
echo [3/7] Creating Python virtual environment...
if exist venv (
    venv\Scripts\python.exe -c "import sys" >nul 2>&1
    if errorlevel 1 (
        echo Existing virtual environment is invalid, rebuilding it...
        rmdir /s /q venv
    )
)
if not exist venv (
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo Virtual environment created successfully
)
echo.

REM Install Python packages
REM Use the venv interpreter directly and run pip non-interactively. Invoking
REM pip as `python -m pip` avoids the Windows "To modify pip" self-modify error,
REM and --no-input stops pip from ever blocking on a prompt (a common cause of
REM the installer appearing to hang at "Installing collected packages"). If a
REM previous MrPackMaker server is still running it can lock files in the venv;
REM close it first so pip can replace packages instead of stalling.
echo [4/7] Installing Python packages...
set "VENV_PY=venv\Scripts\python.exe"
"%VENV_PY%" -m pip install --no-input --disable-pip-version-check --upgrade pip
if errorlevel 1 (
    echo ERROR: Failed to upgrade pip
    pause
    exit /b 1
)
"%VENV_PY%" -m pip install --no-input --disable-pip-version-check --timeout 60 --retries 3 -r backend\requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install Python packages
    echo If this happened on a re-install, make sure no MrPackMaker window is
    echo still running (it can lock files in the venv), then run installer.bat again.
    pause
    exit /b 1
)
echo Python packages installed successfully
echo.

REM Install frontend dependencies
echo [5/7] Installing frontend dependencies...
cd frontend
call npm install
if errorlevel 1 (
    echo ERROR: Failed to install frontend dependencies
    cd ..
    pause
    exit /b 1
)
cd ..
echo Frontend dependencies installed successfully
echo.

REM Create config.json
echo [6/7] Creating config.json...
if not exist config.json (
    if exist config.example.json (
        copy config.example.json config.json
        echo config.json created from config.example.json
    ) else (
        echo WARNING: config.example.json not found, creating default config.json
        echo {> config.json
        echo   "ai": {>> config.json
        echo     "provider": "lmstudio",>> config.json
        echo     "base_url": "http://localhost:1234/v1",>> config.json
        echo     "model": "",>> config.json
        echo     "timeout_seconds": 45,>> config.json
        echo     "max_tokens": 4096,>> config.json
        echo     "temperature": 0.2>> config.json
        echo   },>> config.json
        echo   "apis": {},>> config.json
        echo   "voice": {>> config.json
        echo     "whisper_url": "http://localhost:9000",>> config.json
        echo     "tts_provider": "disabled",>> config.json
        echo     "tts_base_url": "",>> config.json
        echo     "tts_model": "",>> config.json
        echo     "tts_voice": "alloy">> config.json
        echo   }>> config.json
        echo }>> config.json
    )
) else (
    echo config.json already exists, skipping...
)
echo.

REM Build frontend
echo [7/7] Building frontend...
cd frontend
call npm run build
if errorlevel 1 (
    echo ERROR: Failed to build frontend
    cd ..
    pause
    exit /b 1
)
cd ..
echo Frontend built successfully
echo.

echo ========================================
echo Installation completed successfully!
echo ========================================
echo.
echo The app will open at http://localhost:8000
echo Tip: next time you can just run start.bat (no reinstall needed).
echo No AI model? In the builder, use "Quick pack (no AI)" to still get a modpack.
echo.
echo Press Ctrl+C to stop the server
echo.

REM Start backend (serves the built frontend at http://localhost:8000)
start "" /b powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 2; Start-Process 'http://localhost:8000'"
cd backend
"..\venv\Scripts\python.exe" run.py

pause
