# task_add.ps1 -- Thin wrapper for devcore_engine task add
param(
    [Parameter(Mandatory=$true)]
    [string]$Title,
    [ValidateSet("coding", "reasoning", "bulk")]
    [string]$Mode = "coding",
    [int]$Steps = 1,
    [string]$Project,
    [string]$DependsOn
)

$DEV_CORE_ROOT = Split-Path -Parent $PSScriptRoot
if (-not $env:PYTHONPATH -or $env:PYTHONPATH -notlike "*$DEV_CORE_ROOT*") {
    $env:PYTHONPATH = "$DEV_CORE_ROOT;$env:PYTHONPATH"
}

. (Join-Path $PSScriptRoot "platform_version.ps1")
$pythonExe = Get-DevCorePython

$taskArgs = @("-m", "devcore_engine", "task", "add", $Title, "--mode", $Mode, "--steps", [string]$Steps)
if ($Project) { $taskArgs += @("--project", $Project) }
if ($DependsOn) { $taskArgs += @("--depends-on", $DependsOn) }
& $pythonExe @taskArgs
exit $LASTEXITCODE
