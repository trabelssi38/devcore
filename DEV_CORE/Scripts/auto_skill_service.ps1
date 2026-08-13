# auto_skill_service.ps1 -- Thin wrapper for devcore_engine skills
param(
    [string]$Action = "List"
)

$DEV_CORE_ROOT = Split-Path -Parent $PSScriptRoot
if (-not $env:PYTHONPATH -or $env:PYTHONPATH -notlike "*$DEV_CORE_ROOT*") {
    $env:PYTHONPATH = "$DEV_CORE_ROOT;$env:PYTHONPATH"
}

. (Join-Path $PSScriptRoot "platform_version.ps1")
$pythonExe = Get-DevCorePython

& $pythonExe -m devcore_engine skills list
exit $LASTEXITCODE
