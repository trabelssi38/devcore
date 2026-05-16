# task_sync.ps1 -- DEV_CORE v6 -- Synchronise les suggestions dans tasks.json
param([int]$MaxPerSource = 3)

$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { "C:\devcore\DEV_CORE_DATA" }
$TODAY         = Get-Date -Format "yyyy-MM-dd"
$LOG           = "$DEV_CORE_DATA\Logs\scripts\task_sync_$TODAY.log"

function Log { param($msg,$color="Gray")
    $l = "[$(Get-Date -f HH:mm:ss)] $msg"
    Add-Content $LOG $l -ErrorAction SilentlyContinue
    Write-Host "    $l" -ForegroundColor $color
}

Write-Host ""
Write-Host "  DEV_CORE v6 -- TASK SYNC" -ForegroundColor Cyan
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
        $lines = @(Get-Content $path -ErrorAction SilentlyContinue)
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
    Write-Host "  [INFO] Aucune suggestion -- d'abord dc task scan" -ForegroundColor Yellow
    Write-Host ""
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


# Lire tasks.json
$tFile = "$DEV_CORE_DATA\Memory\$(& "$PSScriptRoot\Get-ActiveProject.ps1")\tasks.json"
if (-not (Test-Path $tFile)) {
    @{
        project="auto-detected"
        current_task=$null
        tasks=@()
    } | ConvertTo-Json -Depth 5 | Set-Content $tFile -Encoding UTF8
    $board = Get-Content $tFile -Raw | ConvertFrom-Json
} else {
    $board = Get-Content $tFile -Raw | ConvertFrom-Json
}

# Ajouter les suggestions comme taches
$added = 0
$existingIds = $board.tasks | ForEach-Object { $_.id }
$nextNum = 1

foreach ($s in $suggestions) {
    $id = $s.id
    # Pour les suggestions spec/prompt, generer un ID
    if (-not $id -or ($id -eq "")) {
        $nums = $board.tasks | Where-Object { $_.id -match "^T-(\d+)$" } |
                 ForEach-Object { [int]($_.id -replace "T-","") }
        $nextNum = if ($nums) { ($nums | Measure-Object -Maximum).Maximum + 1 } else { $nextNum }
        $id = "T-" + ($nextNum.ToString().PadLeft(2,'0'))
    }

    # Ne pas dupliquer
    if ($id -notin $existingIds) {
        $mode = if ($s.mode) { $s.mode } else { "coding" }
        $title = if ($s.title) { $s.title } else { $s.reason }

        $t = [PSCustomObject]@{
            id         = $id
            title      = $title
            mode       = $mode
            status     = "todo"
            steps_total= 1
            steps_done = 0
            depends_on = $null
            source     = $s.source
            worktree   = if ($s.worktree) { $s.worktree } elseif ($env:DEVCORE_ACTIVE_WORKTREE_NAME) { $env:DEVCORE_ACTIVE_WORKTREE_NAME } else { "main" }
        }
        $board.tasks += $t
        $existingIds += $id
        $added++
        Write-Host "    + $id [$mode] $title" -ForegroundColor Green
        $nextNum++
    }
}

# Sauvegarder
$board | ConvertTo-Json -Depth 10 | Set-Content $tFile -Encoding UTF8

# Nettoyer les queues
foreach ($path in $queues.Values) {
    if (Test-Path $path) { Remove-Item $path -Force }
}

Write-Host ""
Write-Host "  ========================================" -ForegroundColor Green
Write-Host "  $added taches ajoutees a tasks.json" -ForegroundColor Green
Write-Host ""


& \gen_dashboard.ps1
