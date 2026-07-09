# task_done.ps1 -- DEV_CORE v9.0 single client
param([switch]$Force)
$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { "C:\devcore\DEV_CORE_DATA" }
$AUTO          = "$DEV_CORE\Scripts\Auto"
$TODAY         = Get-Date -Format "yyyy-MM-dd"
$tFile         = "$DEV_CORE_DATA\Memory\$(& "$PSScriptRoot\Get-ActiveProject.ps1")\tasks.json"

if (-not (Test-Path $tFile)) { Write-Host "  Aucun tasks.json." -ForegroundColor Red; exit 1 }
$board = Get-Content $tFile -Raw -Encoding UTF8 | ConvertFrom-Json
$current = $board.tasks | Where-Object { $_.status -eq "active" } | Select-Object -First 1
if (-not $current) { Write-Host "  Aucune tache active -- dc next task" -ForegroundColor Yellow; exit 0 }

$stepsTotal = if ($current.PSObject.Properties["steps_total"]) { $current.steps_total } else { 1 }
$stepsDone  = if ($current.PSObject.Properties["steps_done"])  { $current.steps_done  } else { 1 }

if ($stepsDone -lt $stepsTotal -and -not $Force) {
    Write-Host "  $stepsDone/$stepsTotal etapes completees" -ForegroundColor Yellow
    $c = Read-Host "  Valider quand meme ? (o/N)"
    if ($c -notmatch "^o|^y") { Write-Host "  Tache non validee." -ForegroundColor DarkGray; exit 0 }
}

# Garde d'integrite (si force)
if ($current.steps_done -lt $current.steps_total) {
    Write-Host "  [WARN] $($current.id) force done : steps_done corrige $($current.steps_done) -> $($current.steps_total)" -ForegroundColor Yellow
}

$completeJson = & "$PSScriptRoot\task_service.ps1" -Action Complete -Force -Json
$completeResult = if ($completeJson -and (($completeJson -join "`n").Trim()) -ne "null") {
    ($completeJson | Out-String) | ConvertFrom-Json
} else {
    $null
}
if (-not $completeResult) { Write-Host "  Aucune tache active -- dc next task" -ForegroundColor Yellow; exit 0 }
$current = $completeResult.completed
$nextTask = $completeResult.next
$board = Get-Content $tFile -Raw -Encoding UTF8 | ConvertFrom-Json

Write-Host ""; Write-Host "  DEV_CORE v9.0 -- TASK DONE" -ForegroundColor Green; Write-Host ""
Write-Host "  1/5 Lecons..." -ForegroundColor Cyan
if (Test-Path "$AUTO\lesson_extractor.ps1") { & "$AUTO\lesson_extractor.ps1" }

Write-Host "  2/5 Qdrant..." -ForegroundColor Cyan
if (Test-Path "$DEV_CORE\Scripts\qdrant_sync.ps1") { & "$DEV_CORE\Scripts\qdrant_sync.ps1" }

Write-Host "  3/5 Obsidian..." -ForegroundColor Cyan
if (Test-Path "$DEV_CORE\Scripts\obsidian_sync.ps1") { & "$DEV_CORE\Scripts\obsidian_sync.ps1" }

Write-Host "  4/5 Memoire + Refs..." -ForegroundColor Cyan
if (Test-Path "$AUTO\memory_rotate.ps1") { & "$AUTO\memory_rotate.ps1" }

# Archiver les refs de la tâche terminée
$projName = & "$DEV_CORE\Scripts\Get-ActiveProject.ps1"
$refsTaskDir = "$DEV_CORE_DATA\Refs\$projName\$($current.id)"
if (Test-Path $refsTaskDir) {
    $archiveDir = "$DEV_CORE_DATA\Refs\$projName\_archive"
    if (-not (Test-Path $archiveDir)) { New-Item -ItemType Directory -Path $archiveDir -Force | Out-Null }
    Move-Item $refsTaskDir "$archiveDir\$($current.id)" -Force -ErrorAction SilentlyContinue
    Write-Host "    [Refs] Fichiers déchargés archivés dans _archive/$($current.id)" -ForegroundColor DarkGray
}

# Mettre à jour le canvas du projet
& "$DEV_CORE\Scripts\canvas_manager.ps1" -Action Update

Write-Host "  5/5 Notification..." -ForegroundColor Cyan
try {
    Add-Type -AssemblyName System.Windows.Forms
    $n = New-Object System.Windows.Forms.NotifyIcon
    $n.Icon = [System.Drawing.SystemIcons]::Information; $n.Visible = $true
    $nextInfo = if ($nextTask) { "Suivant : $($nextTask.id) [$($nextTask.mode)]" } else { "Projet termine !" }
    $n.ShowBalloonTip(5000, "DEV_CORE v9.0", "$($current.id) done. $nextInfo", [System.Windows.Forms.ToolTipIcon]::Info)
    Start-Sleep -Seconds 1; $n.Dispose()
} catch {}

$done  = ($board.tasks | Where-Object { $_.status -eq "done" }).Count
$total = $board.tasks.Count
Write-Host ""
Write-Host "  [OK] $($current.id) done | $done/$total taches" -ForegroundColor Green

# Auto-chainage (2.1) -- charge automatiquement la tache suivante
if ($nextTask) {
    Write-Host "  [AUTO] Chargement $($nextTask.id)..." -ForegroundColor Cyan
    & "$DEV_CORE\Scripts\task_next.ps1"
} else {
    Write-Host "  Toutes les taches sont terminees !" -ForegroundColor Green
}
Write-Host ""


& "$PSScriptRoot\gen_dashboard.ps1"
