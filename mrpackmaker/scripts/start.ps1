#requires -Version 5.1
# MrPackMaker launcher engine.
#
# Why this exists: the old start.bat piped the server through PowerShell inline
# with "2^>^&1 | Tee-Object". cmd.exe does NOT strip the ^ carets inside a
# double-quoted -Command string, so PowerShell received "2^>^&1" verbatim and
# crashed with:
#   The ampersand (&) character is not allowed. ... AmpersandNotAllowed
# Running the logic from a real .ps1 file with -File removes all cmd quoting,
# so "2>&1 | Tee-Object" is parsed normally and live logs stream correctly.
#
# IMPORTANT: uvicorn logs to stderr. With 2>&1 those lines become error records,
# and under $ErrorActionPreference='Stop' PowerShell would throw NativeCommandError
# on the first log line and kill the server. We therefore use 'Continue' for the
# native streaming sections and drive control flow from $LASTEXITCODE instead.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
Set-Location $Root

$Version = '2.5.4'
$Backend = Join-Path $Root 'backend'
$VenvPython = Join-Path $Root 'venv\Scripts\python.exe'
$LogFile = Join-Path $Root 'startup-error.log'
$BindHost = if ($env:MRPACK_HOST) { $env:MRPACK_HOST } else { '127.0.0.1' }
$Port = if ($env:MRPACK_PORT) { $env:MRPACK_PORT } else { '8000' }
$Url = "http://localhost:$Port"

function Fail([string]$Message) {
    Write-Host "`nERROR: $Message" -ForegroundColor Red
    Write-Host "Full log: $LogFile" -ForegroundColor Yellow
    Read-Host 'Press Enter to close'
    exit 1
}

Write-Host '========================================' -ForegroundColor Cyan
Write-Host "   MrPackMaker $Version" -ForegroundColor Cyan
Write-Host '========================================' -ForegroundColor Cyan

if (-not (Test-Path $VenvPython)) { Fail 'Virtual environment not found. Run installer.vbs first.' }
if (-not (Test-Path (Join-Path $Root 'frontend\dist\index.html'))) { Fail 'Frontend build not found. Run installer.vbs first.' }

$PyVersion = try { ((& $VenvPython --version 2>&1) | Out-String).Trim() } catch { 'unknown' }
Write-Host ("Python:  {0}" -f $PyVersion) -ForegroundColor Gray
Write-Host ("Host:    {0}" -f $BindHost) -ForegroundColor Gray
Write-Host ("Port:    {0}" -f $Port) -ForegroundColor Gray
Write-Host ("URL:     {0}" -f $Url) -ForegroundColor Gray

# Rotate the startup log if it grew past 5 MB, then write a fresh header.
if ((Test-Path $LogFile) -and ((Get-Item $LogFile).Length -gt 5MB)) { Remove-Item $LogFile -Force }
"MrPackMaker $Version startup log - $(Get-Date -Format o)" | Out-File $LogFile -Encoding utf8

# From here on the native processes write to stderr on purpose (tracebacks,
# uvicorn logs). Switch to Continue so 2>&1 streaming never throws; we check
# $LASTEXITCODE explicitly for real failures.
$ErrorActionPreference = 'Continue'

Write-Host "`nChecking backend startup..." -ForegroundColor White
Set-Location $Backend
& $VenvPython -c 'import app.main; print("Backend import OK")' 2>&1 | Tee-Object -FilePath $LogFile -Append
if ($LASTEXITCODE -ne 0) { Set-Location $Root; Fail 'Backend import failed. See the traceback above and in the log.' }
Write-Host 'Backend import OK' -ForegroundColor Green

Write-Host ("Starting MrPackMaker on {0}" -f $Url) -ForegroundColor Green
Write-Host 'Live server logs appear below and are saved to startup-error.log.' -ForegroundColor Gray
Write-Host 'Press Ctrl+C to stop the server.' -ForegroundColor DarkGray

# Open the browser shortly after the server starts listening.
Start-Job -ScriptBlock { Start-Sleep -Seconds 2; Start-Process $using:Url } | Out-Null

& $VenvPython 'run.py' 2>&1 | Tee-Object -FilePath $LogFile -Append
$ExitCode = $LASTEXITCODE
Set-Location $Root
Write-Host ("`nServer exited with code {0}." -f $ExitCode) -ForegroundColor Yellow
Write-Host ("Full log: {0}" -f $LogFile) -ForegroundColor Gray
Read-Host 'Press Enter to close'
exit $ExitCode
