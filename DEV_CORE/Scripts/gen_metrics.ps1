# gen_metrics.ps1 -- DEV_CORE v9.0
# Genere les metriques de session

$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { $PSScriptRoot }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { (Join-Path (Split-Path -Parent $PSScriptRoot) "DEV_CORE_DATA") }
$TODAY = Get-Date -Format "yyyy-MM-dd"
$METRICS_DIR = "$DEV_CORE_DATA\Metrics"
$METRICS_FILE = "$METRICS_DIR\session_metrics_$TODAY.csv"

if (-not (Test-Path $METRICS_DIR)) {
    New-Item -ItemType Directory -Path $METRICS_DIR -Force | Out-Null
}

# Lire tasks
$tFile = "$DEV_CORE_DATA\Memory\$(& "$PSScriptRoot\Get-ActiveProject.ps1")\tasks.json"
$totalSteps = 0
$doneSteps = 0
$taskCount = 0

if (Test-Path $tFile) {
    $board = Get-Content $tFile -Raw | ConvertFrom-Json
    foreach ($t in $board.tasks) {
        $totalSteps += $t.steps_total
        $doneSteps += $t.steps_done
        $taskCount++
    }
}

# Lire session context
$sessionLog = "$DEV_CORE_DATA\Logs\scripts\session_context.txt"
$activeTask = ""
if (Test-Path $sessionLog) {
    $line = Get-Content $sessionLog | Where-Object { $_ -match "Task active" } | Select-Object -First 1
    if ($line -match "T-\d+") {
        $activeTask = $Matches[0]
    }
}

$progress = if ($totalSteps -gt 0) { [math]::Round(($doneSteps / $totalSteps) * 100) } else { 0 }
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

$header = "date,active_task,tasks_count,steps_done,steps_total,progress_pct"
$row = "$TODAY,$activeTask,$taskCount,$doneSteps,$totalSteps,$progress"

if (-not (Test-Path $METRICS_FILE)) {
    $header | Set-Content $METRICS_FILE -Encoding UTF8
}
$row | Add-Content $METRICS_FILE -Encoding UTF8

Write-Host "  [METRICS] $TODAY | $activeTask | $doneSteps/$totalSteps steps | $progress%" -ForegroundColor Cyan

