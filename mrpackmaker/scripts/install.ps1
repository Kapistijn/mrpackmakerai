#requires -Version 5.1
<##
    MrPackMaker installer. Uses npm install rather than npm ci because an
    existing installation may contain a stale lockfile after an upgrade.
#>
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
function Write-Header { Write-Host ''; Write-Host '========================================' -ForegroundColor Cyan; Write-Host '   MrPackMaker Installer' -ForegroundColor Cyan; Write-Host '========================================' -ForegroundColor Cyan; Write-Host '' }
function Fail($Message) { Write-Host ''; Write-Host "ERROR: $Message" -ForegroundColor Red; Write-Host "See the full log at: $LogFile" -ForegroundColor Yellow; Write-Host ''; Read-Host 'Press Enter to close'; exit 1 }
function Invoke-Step { param([string]$Label,[string]$Message,[scriptblock]$Action,[string]$FailHint=''); Write-Host ("{0} {1}" -f $Label,$Message) -ForegroundColor White; $job=Start-Job -ScriptBlock $Action; $frames=@('|','/','-','\\'); $i=0; $sw=[System.Diagnostics.Stopwatch]::StartNew(); while($job.State -eq 'Running'){Write-Host -NoNewline ("`r    {0}  {1,4}s elapsed   " -f $frames[$i % $frames.Count],[int]$sw.Elapsed.TotalSeconds); Start-Sleep -Milliseconds 120; $i++}; $sw.Stop(); $output=Receive-Job $job -ErrorAction SilentlyContinue 2>&1; $failed=($job.State -eq 'Failed'); Remove-Job $job -Force -ErrorAction SilentlyContinue; if($output){$output | Out-File -FilePath $LogFile -Append -Encoding utf8}; if($failed){Write-Host ("`r    FAIL  ({0}s)                 " -f [int]$sw.Elapsed.TotalSeconds) -ForegroundColor Red; if($output){$output | Select-Object -Last 15 | ForEach-Object {Write-Host "    $_" -ForegroundColor DarkGray}}; if($FailHint){Write-Host "    $FailHint" -ForegroundColor Yellow}; Fail "$Message failed."}; Write-Host ("`r    OK    ({0}s)                 " -f [int]$sw.Elapsed.TotalSeconds) -ForegroundColor Green }
function Assert-Command { param([string]$Label,[string]$Exe,[string]$InstallHint); Write-Host ("{0} Checking {1}..." -f $Label,$Exe) -ForegroundColor White; $found=Get-Command $Exe -ErrorAction SilentlyContinue; if(-not $found){Fail "$Exe is not installed or not in PATH. $InstallHint"}; $version=(& $Exe --version 2>&1 | Select-Object -First 1); Write-Host "    Found $version" -ForegroundColor Green }
Write-Header
Assert-Command '[1/7]' 'python' 'Install Python 3.10+ from https://python.org and re-run.'
Assert-Command '[2/7]' 'node' 'Install Node.js 18+ from https://nodejs.org and re-run.'
Write-Host '[3/7] Creating Python virtual environment...' -ForegroundColor White
if(Test-Path (Join-Path $Root 'venv')){& $VenvPython -c 'import sys' 2>$null; if($LASTEXITCODE -ne 0){Remove-Item -Recurse -Force (Join-Path $Root 'venv')}}
if(-not (Test-Path (Join-Path $Root 'venv'))){Invoke-Step '[3/7]' 'Creating venv' {& python -m venv (Join-Path $using:Root 'venv') 2>&1}}
if(-not (Test-Path $VenvPython)){Fail 'Virtual environment python.exe was not created.'}
Write-Host '[4/7] Installing Python packages...' -ForegroundColor White
$reqFile=Join-Path $Backend 'requirements.txt'; if(-not (Test-Path $reqFile)){Fail "requirements.txt not found at $reqFile"}; $reqs=@(Get-Content $reqFile | Where-Object {$_.Trim() -and -not $_.Trim().StartsWith('#')}); $idx=0
foreach($req in $reqs){$idx++; $name=($req -split '[><=\[;\s]')[0]; Invoke-Step '  [4/7]' ("Installing {0}  ({1}/{2})" -f $name,$idx,$reqs.Count) {& $using:VenvPython -m pip install --no-input --disable-pip-version-check --prefer-binary $using:req 2>&1; if($LASTEXITCODE -ne 0){throw "pip exited with code $LASTEXITCODE"}}}
Invoke-Step '  [4/7]' 'Verifying all backend packages' {& $using:VenvPython -m pip install --no-input --disable-pip-version-check --prefer-binary -r (Join-Path $using:Backend 'requirements.txt') 2>&1; if($LASTEXITCODE -ne 0){throw "pip verify exited with code $LASTEXITCODE"}}
Write-Host '[5/7] Installing frontend dependencies...' -ForegroundColor White
Invoke-Step '  [5/7]' 'Installing Node modules (npm)' {Set-Location (Join-Path $using:Root 'frontend'); & npm install --no-audit --no-fund 2>&1; if($LASTEXITCODE -ne 0){throw "npm install exited with code $LASTEXITCODE"}}
Write-Host '[6/7] Creating config.json...' -ForegroundColor White
if(-not (Test-Path (Join-Path $Root 'config.json'))){if(Test-Path (Join-Path $Root 'config.example.json')){Copy-Item (Join-Path $Root 'config.example.json') (Join-Path $Root 'config.json')}else{Fail 'config.example.json is missing; cannot create config.json.'}}
Write-Host '[7/7] Building frontend...' -ForegroundColor White
Invoke-Step '  [7/7]' 'Compiling with vite' {Set-Location (Join-Path $using:Root 'frontend'); & npm run build 2>&1; if($LASTEXITCODE -ne 0){throw "npm run build exited with code $LASTEXITCODE"}}
Write-Host ''; Write-Host 'Installation completed successfully!' -ForegroundColor Green; Write-Host 'Run start.bat next.' -ForegroundColor Cyan
