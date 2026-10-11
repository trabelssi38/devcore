# Marque une étape dans le projet donné, via le service transactionnel.
param(
    [int]$StepNumber = 0,
    [Parameter(Mandatory=$true)]
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$')]
    [ValidateNotNullOrEmpty()]
    [string]$Project,
    [string]$TaskId,
    [int]$ExpectedVersion
)

$ErrorActionPreference = "Stop"
if ($StepNumber -lt 0) { throw "StepNumber doit être positif ou nul." }

$platformRoot = if ($env:DEVCORE_PLATFORM_ROOT -and (Test-Path -LiteralPath (Join-Path $env:DEVCORE_PLATFORM_ROOT "Scripts\platform_version.ps1"))) {
    $env:DEVCORE_PLATFORM_ROOT
} else {
    Split-Path -Parent $PSScriptRoot
}
if ([string]::IsNullOrWhiteSpace($Project)) { throw "Projet requis." }

if (-not $env:PYTHONPATH -or $env:PYTHONPATH -notlike "*$platformRoot*") {
    $env:PYTHONPATH = if ($env:PYTHONPATH) { "$platformRoot;$env:PYTHONPATH" } else { $platformRoot }
}
. (Join-Path $PSScriptRoot "platform_version.ps1")
$pythonExe = Get-DevCorePython
$stepArgs = @("--project", $Project, "--json")
if ($TaskId) { $stepArgs += $TaskId }
if ($StepNumber -gt 0) { $stepArgs += @("--step-number", [string]$StepNumber) }
if ($PSBoundParameters.ContainsKey("ExpectedVersion")) { $stepArgs += @("--expected-version", [string]$ExpectedVersion) }

$resultJson = & $pythonExe -m devcore_engine.cli task step @stepArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$result = ($resultJson | Out-String) | ConvertFrom-Json
if (-not $result.task) {
    Write-Host "  Aucune tâche active ou en attente pour $Project." -ForegroundColor Yellow
    return
}

Write-Host "  [OK] $($result.task.id) : $($result.task.steps_done)/$($result.task.steps_total) étapes" -ForegroundColor Green
if ($result.complete) {
    Write-Host "  [OK] Tâche terminée dans SQLite." -ForegroundColor Cyan
}
