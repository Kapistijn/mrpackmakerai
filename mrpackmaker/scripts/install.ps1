#requires -Version 5.1
<##
    MrPackMaker installer (PowerShell)
    Installs dependencies, builds the frontend, and starts the backend.
##>
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
Set-Location $Root
$Backend = Join-Path $Root 'backend'
$Frontend = Join-Path $Root 'frontend'
$VenvPython = Join-Path $Root 'venv\Scripts\python.exe'
$LogFile = Join-Path $Root 'install-log.txt'
"MrPackMaker install log - $(Get-Date -Format o)" | Out-File -FilePath $LogFile -Encoding utf8
function Fail($Message) { Write-Host "ERROR: $Message" -ForegroundColor Red; Write-Host "See $LogFile" -ForegroundColor Yellow; Read-Host 'Press Enter to close'; exit 1 }
function Invoke-Step { param([string]$Label,[string]$Message,[scriptblock]$Action)
    Write-Host "$Label $Message"
    $job = Start-Job -ScriptBlock $Action
    while ($job.State -eq 'Running') { Start-Sleep -Milliseconds 120 }
    $output = Receive-Job $job -ErrorAction SilentlyContinue 2>&1
    $failed = $job.State -eq 'Failed'
    Remove-Job $job -Force -ErrorAction SilentlyContinue
    if ($output) { $output | Out-File -FilePath $LogFile -Append -Encoding utf8 }
    if ($failed) { $output | Select-Object -Last 20 | ForEach-Object { Write-Host $_ -ForegroundColor DarkGray }; Fail "$Message failed." }
    Write-Host "$Label OK" -ForegroundColor Green
}
function Assert-Command { param([string]$Exe,[string]$Hint); if (-not (Get-Command $Exe -ErrorAction SilentlyContinue)) { Fail "$Exe is missing. $Hint" } }
Assert-Command 'python' 'Install Python 3.10+.'
Assert-Command 'node' 'Install Node.js 18+.'
if (Test-Path (Join-Path $Root 'venv')) { & $VenvPython -c 'import sys' 2>$null; if ($LASTEXITCODE -ne 0) { Remove-Item -Recurse -Force (Join-Path $Root 'venv') } }
if (-not (Test-Path $VenvPython)) { Invoke-Step '[3/7]' 'Creating venv' { & python -m venv (Join-Path $using:Root 'venv') 2>&1 }; if (-not (Test-Path $VenvPython)) { Fail 'venv was not created.' } }
$reqFile = Join-Path $Backend 'requirements.txt'
Invoke-Step '[4/7]' 'Installing backend packages' { & $using:VenvPython -m pip install --no-input --disable-pip-version-check --prefer-binary -r $using:reqFile 2>&1; if ($LASTEXITCODE -ne 0) { throw "pip exited $LASTEXITCODE" } }
Invoke-Step '[5/7]' 'Installing frontend packages' { Set-Location $using:Frontend; & npm install --no-audit --no-fund --prefer-offline 2>&1; if ($LASTEXITCODE -ne 0) { throw "npm exited $LASTEXITCODE" } }
if (-not (Test-Path (Join-Path $Root 'config.json'))) { Copy-Item (Join-Path $Root 'config.example.json') (Join-Path $Root 'config.json') }
Invoke-Step '[7/7]' 'Building frontend' { Set-Location $using:Frontend; & npm run build 2>&1; if ($LASTEXITCODE -ne 0) { throw "npm build exited $LASTEXITCODE" } }
Write-Host 'Installation completed. Run start.bat next.' -ForegroundColor Green
