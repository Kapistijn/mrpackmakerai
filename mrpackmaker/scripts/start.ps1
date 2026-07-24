#requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
Set-Location $Root
$Version = '2.5.4'
$Backend = Join-Path $Root 'backend'
$BackendRun = Join-Path $Backend 'run.py'
$VenvPython = Join-Path $Root 'venv\Scripts\python.exe'
$LogFile = Join-Path $Root 'startup-error.log'
$BindHost = if ($env:MRPACK_HOST) { $env:MRPACK_HOST } else { '127.0.0.1' }
$PortText = if ($env:MRPACK_PORT) { $env:MRPACK_PORT } else { '8000' }
$Port = 0
if (-not [int]::TryParse($PortText, [ref]$Port) -or $Port -lt 1 -or $Port -gt 65535) { Write-Host "ERROR: MRPACK_PORT must be between 1 and 65535 (received '$PortText')." -ForegroundColor Red; Read-Host 'Press Enter to close'; exit 1 }
$Url = "http://localhost:$Port"
function Fail([string]$Message) { Write-Host "`nERROR: $Message" -ForegroundColor Red; Write-Host "Full log: $LogFile" -ForegroundColor Yellow; Read-Host 'Press Enter to close'; exit 1 }
function Quote-NativeArgument([string]$Value) { return '"' + ($Value -replace '(\\*)"','$1$1\"' -replace '(\\+)$','$1$1') + '"' }
function Invoke-NativeLogged([string]$FilePath,[string[]]$ArgumentList,[string]$WorkingDirectory) {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $FilePath
    $psi.WorkingDirectory = $WorkingDirectory
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.Arguments = (($ArgumentList | ForEach-Object { Quote-NativeArgument $_ }) -join ' ')
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $psi
    [void]$process.Start()
    $stdout = $process.StandardOutput.ReadToEndAsync()
    $stderr = $process.StandardError.ReadToEndAsync()
    $process.WaitForExit()
    $outText = $stdout.Result
    $errText = $stderr.Result
    if ($outText) { Add-Content -Path $LogFile -Value $outText -Encoding UTF8; Write-Host $outText.TrimEnd() }
    if ($errText) { Add-Content -Path $LogFile -Value $errText -Encoding UTF8; Write-Host $errText.TrimEnd() -ForegroundColor DarkGray }
    return $process.ExitCode
}
Write-Host '========================================' -ForegroundColor Cyan
Write-Host "   MrPackMaker $Version" -ForegroundColor Cyan
Write-Host '========================================' -ForegroundColor Cyan
if (-not (Test-Path $VenvPython)) { Fail 'Virtual environment not found. Run installer.vbs first.' }
if (-not (Test-Path (Join-Path $Root 'frontend\dist\index.html'))) { Fail 'Frontend build not found. Run installer.vbs first.' }
if (-not (Test-Path $BackendRun)) { Fail 'Backend launcher not found: backend\run.py.' }
$PyVersion = ((& $VenvPython --version 2>&1) | Out-String).Trim()
Write-Host "Python: $PyVersion`nHost: $BindHost`nPort: $Port`nURL: $Url" -ForegroundColor Gray
if ((Test-Path $LogFile) -and ((Get-Item $LogFile).Length -gt 5MB)) { Remove-Item $LogFile -Force }
"MrPackMaker $Version startup log - $(Get-Date -Format o)" | Out-File $LogFile -Encoding utf8
Write-Host "`nChecking backend startup..." -ForegroundColor White
$importExit = Invoke-NativeLogged $VenvPython @('-c','import app.main; print(1)') $Backend
if ($importExit -ne 0) { Fail 'Backend import failed. See the traceback above and in the log.' }
Write-Host 'Backend import OK' -ForegroundColor Green
Write-Host "Starting MrPackMaker on $Url" -ForegroundColor Green
Write-Host 'Live server logs appear below and are saved to startup-error.log.' -ForegroundColor Gray
Write-Host 'Press Ctrl+C to stop the server.' -ForegroundColor DarkGray
Start-Job -ScriptBlock { Start-Sleep -Seconds 2; Start-Process $using:Url } | Out-Null
$serverExit = Invoke-NativeLogged $VenvPython @('run.py') $Backend
Set-Location $Root
Write-Host "`nServer exited with code $serverExit." -ForegroundColor Yellow
Write-Host "Full log: $LogFile" -ForegroundColor Gray
Read-Host 'Press Enter to close'
exit $serverExit
