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

. (Join-Path $PSScriptRoot "platform_version.ps1")
$pythonExe = Get-DevCorePython

$actionLower = $Action.ToLower()
if ($actionLower -eq "health") {
    & $pythonExe -m devcore_engine plugins health
} elseif ($actionLower -eq "install") {
    & $pythonExe -m devcore_engine plugins install "$ManifestPath"
} elseif ($actionLower -eq "diagnose") {
    & $pythonExe -m devcore_engine plugins diagnose "$Id"
} elseif ($actionLower -eq "check") {
    & $pythonExe -m devcore_engine plugins check "$Id"
} elseif ($actionLower -eq "disable") {
    & $pythonExe -m devcore_engine plugins disable "$Id"
} else {
    & $pythonExe -m devcore_engine plugins list
}
exit $LASTEXITCODE
