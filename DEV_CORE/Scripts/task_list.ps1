# task_list.ps1 -- compatibility adapter to Python API ports
param(
    [string]$Project = "",
    [switch]$Json
)

$ErrorActionPreference = "Stop"
$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$adapter = Join-Path $DEV_CORE "API\compat_task_list.py"

if ([string]::IsNullOrWhiteSpace($Project)) {
    $Project = & (Join-Path $PSScriptRoot "Get-ActiveProject.ps1")
}

$arguments = @($adapter, "--project", $Project)
if ($Json) { $arguments += "--json" }

& python @arguments
exit $LASTEXITCODE
