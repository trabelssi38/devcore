# Génère un relevé des tâches SQL pour un seul projet dans le runtime local.
param(
    [Parameter(Mandatory=$true)]
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$')]
    [string]$Project
)

$ErrorActionPreference = "Stop"
$platformRoot = if ($env:DEVCORE_PLATFORM_ROOT -and (Test-Path -LiteralPath (Join-Path $env:DEVCORE_PLATFORM_ROOT "Scripts\platform_version.ps1"))) {
    $env:DEVCORE_PLATFORM_ROOT
} else {
    Split-Path -Parent $PSScriptRoot
}
if ([string]::IsNullOrWhiteSpace($Project)) { throw "Projet requis." }

$localRoot = if ($env:DEVCORE_LOCAL_ROOT) {
    $env:DEVCORE_LOCAL_ROOT
} elseif ($env:LOCALAPPDATA) {
    Join-Path $env:LOCALAPPDATA "DEV_CORE_LOCAL"
} else {
    Join-Path ([System.IO.Path]::GetTempPath()) "DEV_CORE_LOCAL"
}
if (-not $env:PYTHONPATH -or $env:PYTHONPATH -notlike "*$platformRoot*") {
    $env:PYTHONPATH = if ($env:PYTHONPATH) { "$platformRoot;$env:PYTHONPATH" } else { $platformRoot }
}
. (Join-Path $PSScriptRoot "platform_version.ps1")
$pythonExe = Get-DevCorePython
$boardJson = & $pythonExe -m devcore_engine.cli task board --project $Project --json
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$board = ($boardJson | Out-String) | ConvertFrom-Json

$totalSteps = 0
$doneSteps = 0
$taskCount = 0
foreach ($task in @($board.tasks)) {
    $totalSteps += [int]$task.steps_total
    $doneSteps += [int]$task.steps_done
    $taskCount++
}
$progress = if ($totalSteps -gt 0) { [math]::Round(($doneSteps / $totalSteps) * 100) } else { 0 }
$activeTask = if ($board.current_task) { [string]$board.current_task } else { "" }
$today = Get-Date -Format "yyyy-MM-dd"
$metricsDir = Join-Path (Join-Path $localRoot "Metrics") $Project
New-Item -ItemType Directory -Path $metricsDir -Force | Out-Null
$metricsFile = Join-Path $metricsDir "session_metrics_$today.csv"
if (-not (Test-Path -LiteralPath $metricsFile)) {
    "date,project,active_task,tasks_count,steps_done,steps_total,progress_pct" | Set-Content -LiteralPath $metricsFile -Encoding UTF8
}
"$today,$Project,$activeTask,$taskCount,$doneSteps,$totalSteps,$progress" | Add-Content -LiteralPath $metricsFile -Encoding UTF8
Write-Host "  [METRICS] $Project | $activeTask | $doneSteps/$totalSteps steps | $progress%" -ForegroundColor Cyan
