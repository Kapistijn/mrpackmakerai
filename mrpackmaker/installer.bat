@echo off
setlocal enabledelayedexpansion

echo ========================================
echo MrPackMaker Installer
echo ========================================
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
echo [4/7] Installing Python packages...
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r backend\requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install Python packages
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
        echo     "model": "">> config.json
        echo   },>> config.json
        echo   "apis": {>> config.json
        echo     "modrinth_key": "",>> config.json
        echo     "curseforge_key": "">> config.json
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
echo Starting MrPackMaker backend...
echo.
echo The backend will start on http://localhost:8000
echo.
echo Press Ctrl+C to stop the server
echo.

REM Start backend
call venv\Scripts\activate.bat
start "" /b powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 2; Start-Process 'http://localhost:8000'"
cd backend
python run.py

pause
