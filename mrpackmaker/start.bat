@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (echo Virtual environment not found. Run installer.vbs first.& pause& exit /b 1)
if not exist "frontend\dist\index.html" (echo Frontend build not found. Run installer.vbs first.& pause& exit /b 1)
set "PYTHON=%~dp0venv\Scripts\python.exe"
set "STARTUP_LOG=%~dp0startup-error.log"
if exist "%STARTUP_LOG%" forfiles /p "%~dp0" /m startup-error.log /c "cmd /c if @fsize GTR 5242880 del @path" >nul 2>&1
> "%STARTUP_LOG%" echo MrPackMaker startup log %DATE% %TIME%
echo Checking backend startup...
cd /d "%~dp0backend"
"%PYTHON%" -c "import app.main; print('Backend import OK')" >> "%STARTUP_LOG%" 2>&1
if errorlevel 1 (echo Backend import failed. Details:& type "%STARTUP_LOG%"& pause& exit /b 1)
echo Backend import OK
echo Starting MrPackMaker on http://localhost:8000
echo Live server logs will appear below and are saved to startup-error.log.
start "" /b powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 2; Start-Process 'http://localhost:8000'"
powershell -NoProfile -ExecutionPolicy Bypass -Command "& '%PYTHON%' 'run.py' 2^>^&1 | Tee-Object -FilePath '%STARTUP_LOG%' -Append"
set "EXIT_CODE=%ERRORLEVEL%"
cd /d "%~dp0"
echo Server exited with code %EXIT_CODE%.
echo Full log: %STARTUP_LOG%
pause
exit /b %EXIT_CODE%
