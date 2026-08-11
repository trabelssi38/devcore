# integrity_check.ps1 -- DEV_CORE v7
# Vérifie la cohérence entre Git, tasks.json et le Dashboard
# Appeler: dc check --integrity

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT -and (Test-Path (Join-Path $env:DEVCORE_PLATFORM_ROOT "devcore_engine"))) { $env:DEVCORE_PLATFORM_ROOT } else { (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) }
. "$DEV_CORE\Scripts\platform_version.ps1"
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { (Join-Path $DEV_CORE "DEV_CORE_DATA") }
$DEV_CORE_LOCAL = if ($env:DEVCORE_LOCAL_ROOT) { $env:DEVCORE_LOCAL_ROOT } elseif ($env:LOCALAPPDATA) { "$env:LOCALAPPDATA\DEV_CORE_LOCAL" } else { $DEV_CORE_DATA }
$projName = & "$PSScriptRoot\..\Get-ActiveProject.ps1"
$tFile = "$DEV_CORE_DATA\Memory\$projName\tasks.json"
$issues = @()

if (-not (Test-Path $tFile)) {
    Write-Host "  [!] Le fichier tasks.json est introuvable pour le projet $projName." -ForegroundColor Red
    exit 1
}

# 1. Vérifier l'encodage des titres et détails (caractères corrompus)
try {
    $board = Get-Content $tFile -Raw -Encoding UTF8 | ConvertFrom-Json
} catch {
    $issues += "[CRITICAL] tasks.json corrompu ou illisible: $_"
    $board = $null
}

if ($board) {
    foreach ($task in $board.tasks) {
        # Détecter les caractères arabes erronés (encodage cassé/mojibake)
        if ($task.title -match '[\u0600-\u06FF]' -or 
            ($task.details -and $task.details -match '[\u0600-\u06FF]')) {
            $issues += "[ENCODING] $($task.id): caracteres corrompus (mojibake arabe) detectes dans le titre ou les details"
        }
        # Vérifier les titres vides
        if (-not $task.title -or $task.title.Trim() -eq "") {
            $issues += "[EMPTY] $($task.id): titre vide"
        }
        # Vérifier les dates manquantes sur les tâches done
        if ($task.status -eq "done" -and -not $task.completed_at) {
            $issues += "[DATE] $($task.id): tache terminee (done) sans date de completion completed_at"
        }
    }
}

# 2. Comparer avec Git
$workspaceRoot = Split-Path -Parent $DEV_CORE
Push-Location $workspaceRoot
try {
    $commits = git log --since="30 days ago" --format="%H|%s|%ai" 2>$null
    $gitTags = @{}
    if ($commits) {
        foreach ($line in $commits) {
            if ($line -match '\[T-(\d+)\]') {
                $tag = "T-{0:D2}" -f [int]$Matches[1]
                if (-not $gitTags.ContainsKey($tag)) {
                    $msg = ($line -split '\|')[1] -replace '\[T-\d+\]', ''
                    $gitTags[$tag] = $msg.Trim()
                }
            }
        }
        if ($board) {
            foreach ($tag in $gitTags.Keys) {
                $task = $board.tasks | Where-Object { $_.id -eq $tag }
                if (-not $task) {
                    $issues += "[MISSING] $tag est mentionne dans l'historique Git mais absent de tasks.json"
                } elseif ($task.title -ne $gitTags[$tag] -and $gitTags[$tag]) {
                    $issues += "[MISMATCH] $tag titre dans tasks.json ('$($task.title)') ne correspond pas au message du commit Git ('$($gitTags[$tag])')"
                }
            }
        }
    } else {
        $issues += "[GIT] Impossible de lire l'historique de commits ou aucun commit dans les 30 derniers jours."
    }
} catch {
    $issues += "[GIT] Erreur lors de l'execution de git log: $_"
} finally {
    Pop-Location
}

# 3. Rapport d'intégrité
Write-Host ""
Write-Host "  ========================================" -ForegroundColor Cyan
Write-Host "  DEV_CORE v7 -- DIAGNOSTIC D'INTEGRITE" -ForegroundColor Cyan
Write-Host "  ========================================" -ForegroundColor DarkGray
Write-Host ""

if ($issues.Count -gt 0) {
    Write-Host "  [!] $($issues.Count) probleme(s) d'integrite detecte(s):" -ForegroundColor Yellow
    Write-Host ""
    $issues | ForEach-Object { Write-Host "    $_" -ForegroundColor Yellow }
    Write-Host ""
    exit 1
} else {
    Write-Host "  [OK] Integrite parfaite - 0 probleme detecte" -ForegroundColor Green
    Write-Host "  [OK] Encodage UTF-8 sain, sans mojibake" -ForegroundColor Green
    Write-Host "  [OK] Alignement parfait avec les commits Git" -ForegroundColor Green
    Write-Host ""
    exit 0
}
