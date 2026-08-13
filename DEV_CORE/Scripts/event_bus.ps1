# event_bus.ps1 -- Thin wrapper for devcore_engine events
param(
    [ValidateSet("Tail", "Publish", "List")]
    [string]$Action = "Tail",
    [string]$Type = "",
    [string]$Payload = "{}",
    [int]$Limit = 20
)

$DEV_CORE_ROOT = Split-Path -Parent $PSScriptRoot
if (-not $env:PYTHONPATH -or $env:PYTHONPATH -notlike "*$DEV_CORE_ROOT*") {
    $env:PYTHONPATH = "$DEV_CORE_ROOT;$env:PYTHONPATH"
}

. (Join-Path $PSScriptRoot "platform_version.ps1")
$pythonExe = Get-DevCorePython

if ($Action -eq "Publish") {
    & $pythonExe -m devcore_engine events publish "$Type" "$Payload"
} else {
    & $pythonExe -m devcore_engine events tail --limit $Limit
}
exit $LASTEXITCODE
