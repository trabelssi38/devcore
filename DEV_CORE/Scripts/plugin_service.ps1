# plugin_service.ps1 -- Thin wrapper for devcore_engine plugins
param(
    [string]$Action = "List",
    [string]$Id = "",
    [string]$ManifestPath = "",
    [switch]$Json
)

$DEV_CORE_ROOT = Split-Path -Parent $PSScriptRoot
if (-not $env:PYTHONPATH -or $env:PYTHONPATH -notlike "*$DEV_CORE_ROOT*") {
    $env:PYTHONPATH = "$DEV_CORE_ROOT;$env:PYTHONPATH"
}

$actionLower = $Action.ToLower()
if ($actionLower -eq "health") {
    & "C:\Program Files\Python313\python.exe" -m devcore_engine plugins health
} elseif ($actionLower -eq "install") {
    & "C:\Program Files\Python313\python.exe" -m devcore_engine plugins install "$ManifestPath"
} elseif ($actionLower -eq "diagnose") {
    & "C:\Program Files\Python313\python.exe" -m devcore_engine plugins diagnose "$Id"
} elseif ($actionLower -eq "check") {
    & "C:\Program Files\Python313\python.exe" -m devcore_engine plugins check "$Id"
} elseif ($actionLower -eq "disable") {
    & "C:\Program Files\Python313\python.exe" -m devcore_engine plugins disable "$Id"
} else {
    & "C:\Program Files\Python313\python.exe" -m devcore_engine plugins list
}
exit $LASTEXITCODE
