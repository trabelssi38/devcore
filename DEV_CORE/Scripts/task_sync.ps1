# task_sync.ps1 -- DEV_CORE v9.0 -- Synchronise les suggestions via Task Service
param([int]$MaxPerSource = 30)

$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { "C:\devcore\DEV_CORE_DATA" }
$TODAY         = Get-Date -Format "yyyy-MM-dd"
$LOG           = "$DEV_CORE_DATA\Logs\scripts\task_sync_$TODAY.log"

function Log { param($msg,$color="Gray")
    $l = "[$(Get-Date -f HH:mm:ss)] $msg"
    Add-Content $LOG $l -ErrorAction SilentlyContinue
    Write-Host "    $l" -ForegroundColor $color
}

function Get-ContentWithRetry {
    param(
        [string]$Path,
        [switch]$Raw,
        [int]$MaxAttempts = 5,
        [int]$DelayMs = 100
    )
    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        try {
            if ($Raw) {
                return Get-Content $Path -Raw -Encoding UTF8 -ErrorAction Stop
            } else {
                return @(Get-Content $Path -Encoding UTF8 -ErrorAction Stop)
            }
        } catch {
            Log "Read attempt $attempt/$MaxAttempts failed for ${Path}: $_" "Yellow"
            if ($attempt -lt $MaxAttempts) {
                Start-Sleep -Milliseconds $DelayMs
            } else {
                throw
            }
        }
    }
}

Write-Host ""
Write-Host "  DEV_CORE v9.0 -- TASK SYNC" -ForegroundColor Cyan
Write-Host "  ========================================" -ForegroundColor DarkGray
Write-Host ""

# Lire les queues (isolees par projet)
$projName = & "$PSScriptRoot\Get-ActiveProject.ps1"
$projMem = "$DEV_CORE_DATA\Memory\$projName"
$queues = @{
    git = "$projMem\task_git_queue.jsonl"
    spec = "$projMem\task_spec_queue.jsonl"
    prompt = "$projMem\task_prompt_queue.jsonl"
}

$suggestions = @()
foreach ($src in $queues.Keys) {
    $path = $queues[$src]
    if (Test-Path $path) {
        $lines = Get-ContentWithRetry -Path $path
        $selectedLines = $lines | Select-Object -First $MaxPerSource
        foreach ($line in $selectedLines) {
            try {
                $item = $line | ConvertFrom-Json
                $suggestions += $item
            } catch {}
        }
        Log "$($selectedLines.Count) suggestions (sur $($lines.Count)) depuis $src" "Cyan"
    } else {
        Log "0 suggestions depuis $src" "Gray"
    }
}

if ($suggestions.Count -eq 0) {
    Write-Host ""
    Write-Host "  [INFO] Aucune nouvelle suggestion" -ForegroundColor Yellow
    Write-Host ""
    & "$PSScriptRoot\gen_dashboard.ps1"
    return
}

Write-Host ""
Write-Host "  Suggestions trouvees ($($suggestions.Count)) :" -ForegroundColor Green
Write-Host ""

# Limiter le nombre de taches ajoutees par sync
$MAX_ADD = 10
if ($suggestions.Count -gt $MAX_ADD) {
    Write-Host "  [INFO] Limite a $MAX_ADD suggestions par sync" -ForegroundColor Yellow
    $suggestions = $suggestions | Select-Object -First $MAX_ADD
}


$syncInput = Join-Path ([System.IO.Path]::GetTempPath()) ("devcore-task-sync-" + [guid]::NewGuid().ToString("N") + ".json")
try {
    $suggestions | ConvertTo-Json -Depth 10 | Set-Content $syncInput -Encoding UTF8
    $resultJson = & "$PSScriptRoot\task_service.ps1" -Action Sync -InputPath $syncInput -Json | Out-String
    if ($LASTEXITCODE -ne 0) {
        throw "Task Service sync failed with exit code $LASTEXITCODE"
    }
    $result = $resultJson | ConvertFrom-Json
} finally {
    Remove-Item -LiteralPath $syncInput -Force -ErrorAction SilentlyContinue
}

foreach ($task in @($result.tasks)) {
    Write-Host "    + $($task.id) [$($task.mode)] $($task.title)" -ForegroundColor Green
}

# Nettoyer les queues
foreach ($path in $queues.Values) {
    if (Test-Path $path) { Remove-Item $path -Force }
}

Write-Host ""
Write-Host "  ========================================" -ForegroundColor Green
Write-Host "  $($result.added) taches ajoutees a tasks.json" -ForegroundColor Green
Write-Host ""


if ($env:DEVCORE_SKIP_DASHBOARD -ne "1") {
    & "$PSScriptRoot\gen_dashboard.ps1"
}
