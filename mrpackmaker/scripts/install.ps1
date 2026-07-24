#requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
Set-Location $Root
$Backend = Join-Path $Root 'backend'
$Frontend = Join-Path $Root 'frontend'
$VenvPython = Join-Path $Root 'venv\Scripts\python.exe'
$LogFile = Join-Path $Root 'install-log.txt'
"MrPackMaker install log - $(Get-Date -Format o)" | Out-File $LogFile -Encoding utf8
function Fail([string]$Message) { Write-Host "ERROR: $Message" -ForegroundColor Red; Write-Host "See $LogFile" -ForegroundColor Yellow; Read-Host 'Press Enter to close'; exit 1 }
function Assert-Command([string]$Exe,[string]$Hint) { if(-not (Get-Command $Exe -ErrorAction SilentlyContinue)){Fail "$Exe is missing. $Hint"} }
Write-Host '[1/7] Checking Python and Node...'
Assert-Command 'python' 'Install Python 3.10+.'
Assert-Command 'node' 'Install Node.js 18+.'
Write-Host '[2/7] Creating virtual environment...'
if(Test-Path (Join-Path $Root 'venv')) { & $VenvPython -c 'import sys' 2>$null; if($LASTEXITCODE -ne 0){Remove-Item -Recurse -Force (Join-Path $Root 'venv')} }
if(-not (Test-Path $VenvPython)){ & python -m venv (Join-Path $Root 'venv') 2>&1 | Tee-Object -FilePath $LogFile -Append }
if(-not (Test-Path $VenvPython)){Fail 'Virtual environment creation failed.'}
Write-Host '[3/7] Installing backend packages...'
& $VenvPython -m pip install --no-input --disable-pip-version-check --prefer-binary -r (Join-Path $Backend 'requirements.txt') 2>&1 | Tee-Object -FilePath $LogFile -Append
if($LASTEXITCODE -ne 0){Fail 'Backend package installation failed.'}
Write-Host '[4/7] Checking backend import...'
Push-Location $Backend
& $VenvPython -c 'import app.main' 2>&1 | Tee-Object -FilePath $LogFile -Append
$ImportCode = $LASTEXITCODE
Pop-Location
if($ImportCode -ne 0){Fail 'Backend import failed after package installation.'}
Write-Host '[5/7] Installing frontend packages...'
Push-Location $Frontend
# npm install repairs stale or partially generated lockfiles; npm ci is intentionally not used here.
& npm install --no-audit --no-fund 2>&1 | Tee-Object -FilePath $LogFile -Append
$NpmCode = $LASTEXITCODE
Pop-Location
if($NpmCode -ne 0){Fail 'Frontend package installation failed.'}
Write-Host '[6/7] Creating config.json...'
if(-not (Test-Path (Join-Path $Root 'config.json'))){if(Test-Path (Join-Path $Root 'config.example.json')){Copy-Item (Join-Path $Root 'config.example.json') (Join-Path $Root 'config.json')}else{Fail 'config.example.json is missing.'}}
Write-Host '[7/7] Building frontend...'
Push-Location $Frontend
& npm run build 2>&1 | Tee-Object -FilePath $LogFile -Append
$BuildCode = $LASTEXITCODE
Pop-Location
if($BuildCode -ne 0){Fail 'Frontend build failed.'}
Write-Host 'Installation completed successfully. Run start.bat next.' -ForegroundColor Green
