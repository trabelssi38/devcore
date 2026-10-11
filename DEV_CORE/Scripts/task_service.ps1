# Structured PowerShell adapter for project-scoped SQLite task operations.
param(
    [Parameter(Mandatory=$true)][ValidateSet("Edit", "Pause", "Skip", "Resume")][string]$Action,
    [Parameter(Mandatory=$true)][ValidateNotNullOrEmpty()][string]$Project,
    [string]$Id,
    [string]$Title,
    [ValidateSet("coding", "reasoning", "bulk")][string]$Mode,
    [int]$Steps,
    [int]$ExpectedVersion,
    [string]$Reason = ""
)

$ErrorActionPreference = "Stop"
$platformRoot = Split-Path -Parent $PSScriptRoot
if (-not $env:PYTHONPATH -or $env:PYTHONPATH -notlike "*$platformRoot*") {
    $env:PYTHONPATH = if ($env:PYTHONPATH) { "$platformRoot;$env:PYTHONPATH" } else { $platformRoot }
}
. (Join-Path $PSScriptRoot "platform_version.ps1")
$pythonExe = Get-DevCorePython

$taskArgs = @("-m", "devcore_engine.cli", "task", $Action.ToLowerInvariant())
if ($Id) { $taskArgs += $Id }
$taskArgs += @("--project", $Project)
if ($Action -eq "Edit") {
    if (-not $Id) { throw "Id requis pour Edit." }
    if ($PSBoundParameters.ContainsKey("Title")) { $taskArgs += @("--title", $Title) }
    if ($PSBoundParameters.ContainsKey("Mode")) { $taskArgs += @("--mode", $Mode) }
    if ($PSBoundParameters.ContainsKey("Steps")) { $taskArgs += @("--steps", [string]$Steps) }
} elseif ($Action -eq "Skip" -and $Reason) {
    $taskArgs += @("--reason", $Reason)
}
if ($PSBoundParameters.ContainsKey("ExpectedVersion")) { $taskArgs += @("--expected-version", [string]$ExpectedVersion) }

& $pythonExe @taskArgs
exit $LASTEXITCODE
