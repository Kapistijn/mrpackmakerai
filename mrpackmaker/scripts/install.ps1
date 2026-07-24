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
"MrPackMaker 2.5.1 install log - $(Get-Date -Format o)" | Out-File $LogFile -Encoding utf8

function Fail([string]$Message) {
    Write-Host "`nERROR: $Message" -ForegroundColor Red
    Write-Host "Full log: $LogFile" -ForegroundColor Yellow
    Read-Host 'Press Enter to close'
    exit 1
}

function Assert-Command([string]$Exe, [string]$Hint) {
    if (-not (Get-Command $Exe -ErrorAction SilentlyContinue)) { Fail "$Exe is missing. $Hint" }
}

function Invoke-SpinnerStep {
    param([string]$Label, [string]$Message, [scriptblock]$Action)
    Write-Host "$Label $Message" -ForegroundColor White
    $job = Start-Job -ScriptBlock $Action
    $frames = @('|', '/', '-', '\\')
    $index = 0
    $watch = [Diagnostics.Stopwatch]::StartNew()
    while ($job.State -eq 'Running') {
        Write-Host -NoNewline ("`r    {0} {1,4}s   " -f $frames[$index % $frames.Count], [int]$watch.Elapsed.TotalSeconds)
        Start-Sleep -Milliseconds 120
        $index++
    }
    $watch.Stop()
    $output = @(Receive-Job $job -ErrorAction SilentlyContinue 2>&1)
    $failed = $job.State -eq 'Failed'
    if ($output) { $output | Out-File $LogFile -Append -Encoding utf8 }
    Remove-Job $job -Force -ErrorAction SilentlyContinue
    if ($failed) {
        Write-Host ("`r    FAIL ({0}s)                 " -f [int]$watch.Elapsed.TotalSeconds) -ForegroundColor Red
        $output | Select-Object -Last 20 | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkGray }
        Fail "$Message failed."
    }
    Write-Host ("`r    OK   ({0}s)                 " -f [int]$watch.Elapsed.TotalSeconds) -ForegroundColor Green
}

Write-Host '========================================' -ForegroundColor Cyan
Write-Host '   MrPackMaker Installer 2.5.1' -ForegroundColor Cyan
Write-Host '========================================' -ForegroundColor Cyan
Write-Host 'The spinner means installation is still running.' -ForegroundColor DarkGray
Write-Host "Output is saved to $LogFile`n" -ForegroundColor DarkGray

Write-Host '[1/7] Checking Python and Node...'
Assert-Command 'python' 'Install Python 3.10+.'
Assert-Command 'node' 'Install Node.js 18+.'

Write-Host '[2/7] Creating virtual environment...'
if (Test-Path (Join-Path $Root 'venv')) {
    & $VenvPython -c 'import sys' 2>$null
    if ($LASTEXITCODE -ne 0) { Remove-Item -Recurse -Force (Join-Path $Root 'venv') }
}
if (-not (Test-Path $VenvPython)) {
    Invoke-SpinnerStep '[2/7]' 'Creating virtual environment' { & python -m venv (Join-Path $using:Root 'venv') 2>&1 }
}
if (-not (Test-Path $VenvPython)) { Fail 'Virtual environment creation failed.' }

$requirements = Join-Path $Backend 'requirements.txt'
if (-not (Test-Path $requirements)) { Fail "Missing $requirements" }
Invoke-SpinnerStep '[3/7]' 'Installing backend packages' {
    & $using:VenvPython -m pip install --no-input --disable-pip-version-check --prefer-binary -r $using:requirements 2>&1
    if ($LASTEXITCODE -ne 0) { throw "pip exited with code $LASTEXITCODE" }
}

Invoke-SpinnerStep '[4/7]' 'Checking backend import' {
    Set-Location $using:Backend
    & $using:VenvPython -c 'import app.main' 2>&1
    if ($LASTEXITCODE -ne 0) { throw "backend import exited with code $LASTEXITCODE" }
}

Invoke-SpinnerStep '[5/7]' 'Installing frontend packages' {
    Set-Location $using:Frontend
    & npm install --no-audit --no-fund 2>&1
    if ($LASTEXITCODE -ne 0) { throw "npm install exited with code $LASTEXITCODE" }
}

Write-Host '[6/7] Creating config.json...'
if (-not (Test-Path (Join-Path $Root 'config.json'))) {
    if (Test-Path (Join-Path $Root 'config.example.json')) { Copy-Item (Join-Path $Root 'config.example.json') (Join-Path $Root 'config.json') }
    else { Fail 'config.example.json is missing.' }
}

Invoke-SpinnerStep '[7/7]' 'Building frontend' {
    Set-Location $using:Frontend
    & npm run build 2>&1
    if ($LASTEXITCODE -ne 0) { throw "npm run build exited with code $LASTEXITCODE" }
}

Write-Host "`n========================================" -ForegroundColor Green
Write-Host 'Installation completed successfully!' -ForegroundColor Green
Write-Host 'The installer stays open so you can read the result.' -ForegroundColor Cyan
Write-Host 'Run start.bat to launch MrPackMaker.' -ForegroundColor Cyan
Write-Host "Log saved to $LogFile" -ForegroundColor DarkGray
Read-Host 'Press Enter to close'
