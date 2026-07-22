#requires -Version 5.1
<#
    MrPackMaker installer (PowerShell) - beta 1.6.0

    Lives in scripts/ to keep the project root clean. A .bat file cannot
    animate, so this script runs each long step as a background job while
    animating a spinner + elapsed timer, and it breaks the backend install
    into one visible sub-step per package. Full output of every step is
    written to install-log.txt in the project root for troubleshooting.

    Launch it via installer.vbs or install.bat (both in the project root),
    or directly:
        powershell -ExecutionPolicy Bypass -File scripts\install.ps1
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# This script lives in <project>\scripts, so the project root is one level up.
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
Set-Location $Root

$Backend = Join-Path $Root 'backend'
$Frontend = Join-Path $Root 'frontend'
$VenvPython = Join-Path $Root 'venv\Scripts\python.exe'
$LogFile = Join-Path $Root 'install-log.txt'
"MrPackMaker install log - $(Get-Date -Format o)" | Out-File -FilePath $LogFile -Encoding utf8

function Write-Header {
    Write-Host ''
    Write-Host '========================================' -ForegroundColor Cyan
    Write-Host '   MrPackMaker Installer (beta 1.6.0)' -ForegroundColor Cyan
    Write-Host '========================================' -ForegroundColor Cyan
    Write-Host ''
}

function Fail($Message) {
    Write-Host ''
    Write-Host "ERROR: $Message" -ForegroundColor Red
    Write-Host "See the full log at: $LogFile" -ForegroundColor Yellow
    Write-Host ''
    Read-Host 'Press Enter to close'
    exit 1
}

# Run a scriptblock as a background job while animating a spinner and an
# elapsed-seconds counter. All job output is appended to install-log.txt.
function Invoke-Step {
    param(
        [string]$Label,       # e.g. "[4/7]"
        [string]$Message,     # human description
        [scriptblock]$Action, # work to run in the background job
        [string]$FailHint = ''
    )

    Write-Host ("{0} {1}" -f $Label, $Message) -ForegroundColor White

    $job = Start-Job -ScriptBlock $Action
    $frames = @('|', '/', '-', '\')
    $i = 0
    $sw = [System.Diagnostics.Stopwatch]::StartNew()

    while ($job.State -eq 'Running') {
        $frame = $frames[$i % $frames.Count]
        Write-Host -NoNewline ("`r    {0}  {1,4}s elapsed   " -f $frame, [int]$sw.Elapsed.TotalSeconds)
        Start-Sleep -Milliseconds 120
        $i++
    }
    $sw.Stop()

    $output = Receive-Job $job -ErrorAction SilentlyContinue 2>&1
    $failed = ($job.State -eq 'Failed')
    Remove-Job $job -Force -ErrorAction SilentlyContinue
    if ($output) { $output | Out-File -FilePath $LogFile -Append -Encoding utf8 }

    if ($failed) {
        Write-Host ("`r    FAIL  ({0}s)                 " -f [int]$sw.Elapsed.TotalSeconds) -ForegroundColor Red
        if ($output) {
            Write-Host '    --- last lines of output ---' -ForegroundColor Yellow
            $output | Select-Object -Last 15 | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkGray }
        }
        if ($FailHint) { Write-Host "    $FailHint" -ForegroundColor Yellow }
        Fail "$Message failed."
    }

    Write-Host ("`r    OK    ({0}s)                 " -f [int]$sw.Elapsed.TotalSeconds) -ForegroundColor Green
}

function Assert-Command {
    param([string]$Label, [string]$Exe, [string]$InstallHint)
    Write-Host ("{0} Checking {1}..." -f $Label, $Exe) -ForegroundColor White
    $found = Get-Command $Exe -ErrorAction SilentlyContinue
    if (-not $found) { Fail "$Exe is not installed or not in PATH. $InstallHint" }
    $version = (& $Exe --version 2>&1 | Select-Object -First 1)
    Write-Host "    Found $version" -ForegroundColor Green
}

# --------------------------------------------------------------------------
Write-Header
Write-Host 'This window shows a spinner while it works - it is not frozen.' -ForegroundColor DarkGray
Write-Host "Full output is logged to install-log.txt" -ForegroundColor DarkGray
Write-Host ''

# [1/7] Python
Assert-Command '[1/7]' 'python' 'Install Python 3.10+ from https://python.org and re-run.'

# [2/7] Node.js
Assert-Command '[2/7]' 'node' 'Install Node.js 18+ from https://nodejs.org and re-run.'

# [3/7] Virtual environment
Write-Host '[3/7] Creating Python virtual environment...' -ForegroundColor White
if (Test-Path (Join-Path $Root 'venv')) {
    & $VenvPython -c 'import sys' 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host '    Existing venv is invalid, rebuilding...' -ForegroundColor Yellow
        Remove-Item -Recurse -Force (Join-Path $Root 'venv')
    }
}
if (-not (Test-Path (Join-Path $Root 'venv'))) {
    Invoke-Step '[3/7]' 'Creating venv' { & python -m venv (Join-Path $using:Root 'venv') 2>&1 }
} else {
    Write-Host '    venv already exists, reusing it' -ForegroundColor Green
}
if (-not (Test-Path $VenvPython)) { Fail 'Virtual environment python.exe was not created.' }

# [4/7] Backend packages - one visible sub-step per requirement.
# requirements.txt stays the single source of truth; we simply install each
# line individually so progress is granular, then a final pass verifies the
# whole file resolved. No `pip install --upgrade pip` (self-modify errors on
# Windows). --prefer-binary avoids slow source builds; --no-input never blocks.
Write-Host '[4/7] Installing Python packages...' -ForegroundColor White
$reqFile = Join-Path $Backend 'requirements.txt'
if (-not (Test-Path $reqFile)) { Fail "requirements.txt not found at $reqFile" }
$reqs = @(Get-Content $reqFile | Where-Object { $_.Trim() -and -not $_.Trim().StartsWith('#') })
$total = $reqs.Count
$idx = 0
foreach ($req in $reqs) {
    $idx++
    $name = ($req -split '[><=\[;\s]')[0]
    Invoke-Step '  [4/7]' ("Installing {0}  ({1}/{2})" -f $name, $idx, $total) {
        & $using:VenvPython -m pip install --no-input --disable-pip-version-check --prefer-binary $using:req 2>&1
        if ($LASTEXITCODE -ne 0) { throw "pip exited with code $LASTEXITCODE for $using:req" }
    } 'If this is a re-install, close any running MrPackMaker window (it locks files in venv) and try again.'
}
Invoke-Step '  [4/7]' 'Verifying all backend packages' {
    & $using:VenvPython -m pip install --no-input --disable-pip-version-check --prefer-binary -r (Join-Path $using:Backend 'requirements.txt') 2>&1
    if ($LASTEXITCODE -ne 0) { throw "pip verify exited with code $LASTEXITCODE" }
}
Write-Host '    Python packages installed successfully' -ForegroundColor Green

# [5/7] Frontend dependencies. npm ci is faster + deterministic with a lockfile.
Write-Host '[5/7] Installing frontend dependencies...' -ForegroundColor White
Invoke-Step '  [5/7]' 'Installing Node modules (npm)' {
    Set-Location (Join-Path $using:Root 'frontend')
    if (Test-Path 'package-lock.json') {
        & npm ci --no-audit --no-fund --prefer-offline 2>&1
    } else {
        & npm install --no-audit --no-fund --prefer-offline 2>&1
    }
    if ($LASTEXITCODE -ne 0) { throw "npm exited with code $LASTEXITCODE" }
}

# [6/7] config.json
Write-Host '[6/7] Creating config.json...' -ForegroundColor White
if (-not (Test-Path (Join-Path $Root 'config.json'))) {
    if (Test-Path (Join-Path $Root 'config.example.json')) {
        Copy-Item (Join-Path $Root 'config.example.json') (Join-Path $Root 'config.json')
        Write-Host '    config.json created from config.example.json' -ForegroundColor Green
    } else {
        Fail 'config.example.json is missing; cannot create config.json.'
    }
} else {
    Write-Host '    config.json already exists, skipping' -ForegroundColor Green
}

# [7/7] Build frontend
Write-Host '[7/7] Building frontend...' -ForegroundColor White
Invoke-Step '  [7/7]' 'Compiling with vite' {
    Set-Location (Join-Path $using:Root 'frontend')
    & npm run build 2>&1
    if ($LASTEXITCODE -ne 0) { throw "npm run build exited with code $LASTEXITCODE" }
}

Write-Host ''
Write-Host '========================================' -ForegroundColor Green
Write-Host '   Installation completed successfully!' -ForegroundColor Green
Write-Host '========================================' -ForegroundColor Green
Write-Host ''
Write-Host 'Starting MrPackMaker at http://localhost:8000' -ForegroundColor Cyan
Write-Host 'Next time you can just run start.bat (no reinstall needed).' -ForegroundColor DarkGray
Write-Host 'No AI model? Use "Quick pack (no AI)" in the builder.' -ForegroundColor DarkGray
Write-Host 'Press Ctrl+C to stop the server.' -ForegroundColor DarkGray
Write-Host ''

Start-Job { Start-Sleep -Seconds 2; Start-Process 'http://localhost:8000' } | Out-Null

Set-Location $Backend
& $VenvPython 'run.py'
