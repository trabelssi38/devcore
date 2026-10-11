# Start one guarded route; environment settings remain process-local.
param(
    [ValidateSet("native", "auxiliary")][string]$Route = "native",
    [string]$Python = "C:/Python314/python.exe",
    [switch]$Check
)
$ErrorActionPreference = "Stop"
$launcher = Join-Path $PSScriptRoot "headroom_routes.py"
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "Qualified Headroom Python runtime missing: $Python"
}
if ($Check) {
    & $Python $launcher --route $Route --check
    exit $LASTEXITCODE
}
$port = if ($Route -eq "native") { 8787 } else { 8789 }
if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
    throw "Port $port already occupied. Verify route identity before restarting."
}
$arguments = '"' + $launcher + '" --route ' + $Route
$process = Start-Process -FilePath $Python -ArgumentList $arguments -WindowStyle Hidden -PassThru
Write-Output "Started Headroom $Route PID=$($process.Id), port=$port; verify /healthz before use."
