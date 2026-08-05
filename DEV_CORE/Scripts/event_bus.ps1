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

if ($Action -eq "Publish") {
    & "C:\Program Files\Python313\python.exe" -m devcore_engine events publish "$Type" "$Payload"
} else {
    & "C:\Program Files\Python313\python.exe" -m devcore_engine events tail --limit $Limit
}
exit $LASTEXITCODE
