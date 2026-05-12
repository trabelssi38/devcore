# launch.ps1 -- DEV_CORE v6
param(
    [string]$Client = "auto",
    [string]$Project = "",
    [switch]$QuickStart
)

$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { "C:\devcore\DEV_CORE_DATA" }
$TODAY         = Get-Date -Format "yyyy-MM-dd"
$LOG           = "$DEV_CORE_DATA\Logs\scripts\launch_$TODAY.log"

function Log { param($msg,$color="Gray"); $l="[$(Get-Date -f HH:mm:ss)] $msg"; Add-Content $LOG $l -ErrorAction SilentlyContinue; Write-Host "  $l" -ForegroundColor $color }

Write-Host ""
Write-Host "  DEV_CORE v6 - LAUNCH" -ForegroundColor Cyan
Write-Host "  =======================================" -ForegroundColor DarkGray

# 1. Adapter le client
Log "1/8 Adaptation client ($Client)" "Cyan"
& "$DEV_CORE\Scripts\adapt_client.ps1" -Client $Client

# 2. Qdrant check
Log "2/8 Qdrant" "Cyan"
try {
    $q = Invoke-RestMethod "http://localhost:6333/collections" -TimeoutSec 3
    Log "  Qdrant OK - $($q.result.collections.Count) collections" "Green"
} catch { Log "  Qdrant non disponible (docker run -p 6333:6333 -v C:/devcore/DEV_CORE_DATA/qdrant_storage:/qdrant/storage qdrant/qdrant)" "Yellow" }

# 3. Memory
Log "3/8 Memoire" "Cyan"
$memPath = "$DEV_CORE_DATA\Memory\MEMORY.md"
if (Test-Path $memPath) { Log "  MEMORY.md OK - $((Get-Content $memPath).Count) lignes" "Green" }
else { Log "  MEMORY.md absent - sera cree a endday" "Yellow" }

# 4. Tasks
Log "4/8 Tasks" "Cyan"
$tFile = "$DEV_CORE_DATA\Memory\tasks.json"
if (Test-Path $tFile) {
    $b = Get-Content $tFile -Raw | ConvertFrom-Json
    $active = $b.tasks | Where-Object { $_.status -eq "active" }
    $todo   = $b.tasks | Where-Object { $_.status -eq "todo" }
    Log "  Board: $($b.project) | Active: $($active.Count) | Todo: $($todo.Count)" "Green"
    if ($active) { Log "  Task active : $($active[0].id) - $($active[0].title) [$($active[0].mode)]" "Cyan" }
} else { Log "  Pas de tasks.json - dc new task 'titre' -mode pour commencer" "Yellow" }

# 5. Task Detection (git scanner)
Log "5/8 Task detection" "Cyan"
if (-not $QuickStart) {
    & "$DEV_CORE\Scripts\Auto\task_git_scanner.ps1" 2>$null
}

# 6. Daily Note
Log "6/8 Daily Note" "Cyan"
if (-not $QuickStart) {
    $notePath = "$DEV_CORE_DATA\Vault\Daily Notes\$TODAY.md"
    if (-not (Test-Path $notePath)) {
        New-Item -ItemType Directory -Path (Split-Path $notePath) -Force | Out-Null
@"
---
title: Daily Note $TODAY
date: $TODAY
tags: [daily, devcore]
---

# $TODAY

## Resume
<!-- Auto-complete par endday -->

## Taches accomplies

## Decisions

## Lecons

## Metriques tokens
<!-- Auto-complete par endday -->

## Next actions
- [ ]
"@ | Set-Content $notePath -Encoding UTF8
        Log "  Daily Note creee" "Green"
    } else { Log "  Daily Note existante" "Gray" }
}

# 7. Skills registry
Log "7/8 Skills" "Cyan"
$regPath = "$DEV_CORE\Skills\skills_registry.json"
if (Test-Path $regPath) {
    $reg = Get-Content $regPath | ConvertFrom-Json
    Log "  $($reg.skills.Count) skills disponibles" "Green"
}

# 8. Token report veille
Log "8/8 Rapport token" "Cyan"
$yesterday = (Get-Date).AddDays(-1).ToString("yyyy-MM-dd")
$rpt = "$DEV_CORE_DATA\Logs\token_reports\$yesterday-report.html"
if (Test-Path $rpt) { Log "  Rapport veille disponible : $rpt" "Green" }
else { Log "  Pas de rapport pour $yesterday" "Gray" }

$activeClient = Get-Content "$DEV_CORE\Config\active_client.txt" -ErrorAction SilentlyContinue
Write-Host ""
Write-Host "  ========================================" -ForegroundColor Green
Write-Host "  ||  DEV_CORE v6 - PRET                 ||" -ForegroundColor Green
Write-Host "  ========================================" -ForegroundColor Green
Write-Host "  ||  Client : $($activeClient.PadRight(29))||" -ForegroundColor White
Write-Host "  ||  Date   : $($TODAY.PadRight(29))||" -ForegroundColor White
if ($Project) { Write-Host "  ||  Projet : $($Project.PadRight(29))||" -ForegroundColor White }
Write-Host "  ||  dc help pour la liste des commandes  ||" -ForegroundColor Gray
Write-Host "  ========================================" -ForegroundColor Green
Write-Host ""
