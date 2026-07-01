# lesson_extractor.ps1 -- DEV_CORE v9.0 Auto layer
# Extrait les lecons depuis : git log, tasks done, MEMORY.md
$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { "C:\devcore\DEV_CORE_DATA" }
$TODAY         = Get-Date -Format "yyyy-MM-dd"
$LOG           = "$DEV_CORE_DATA\Logs\scripts\lesson_extractor_$TODAY.log"
  function Log { param($msg,$color="Gray"); $l="[$(Get-Date -f HH:mm:ss)] $msg"; Add-Content $LOG $l -ErrorAction SilentlyContinue; Write-Host "    $l" -ForegroundColor $color }
Log "lesson_extractor v9.0 -- extraction multi-source" "Cyan"

$lessonsFile = "$DEV_CORE_DATA\Memory\LESSONS.md"
$tFile       = "$DEV_CORE_DATA\Memory\$(& "$PSScriptRoot\..\Get-ActiveProject.ps1")\tasks.json"
$existed     = Test-Path $lessonsFile

# 1. Creer LESSONS.md si absent
if (-not $existed) {
    @"
# LESSONS.md — DEV_CORE v9.0
<!-- Auto-genere par lesson_extractor.ps1 -->
<!-- Score min inclusion : 0.5 | Derniere maj : $TODAY -->

## Architecture

## Chemins & Configuration

## Debugging

## Workflow
"@ | Set-Content $lessonsFile -Encoding UTF8
    Log "LESSONS.md cree" "Green"
}

$content = Get-Content $lessonsFile -Raw

# 2. Extraire depuis les taches done
if (Test-Path $tFile) {
    $board = Get-Content $tFile -Raw | ConvertFrom-Json
    $doneTasks = $board.tasks | Where-Object { $_.status -eq "done" }
    
    foreach ($t in $doneTasks) {
        $tag = "lesson:$($t.id)"
        if ($content -notmatch [regex]::Escape($tag)) {
            $stepsInfo = if ($t.steps) {
                ($t.steps | ForEach-Object { $_.title }) -join " â†’ "
            } else { "$($t.steps_total) steps" }
            
            $lesson = "- [score: 0.7] [$tag] $($t.title) ($($t.mode)) : $stepsInfo"
            $content += "`n$lesson"
            Log "Lecon ajoutee depuis $($t.id)" "Green"
        }
    }
}

# 3. Extraire depuis le git log (patterns de commits)
try {
    Push-Location (Split-Path -Parent $DEV_CORE)
    $recentCommits = git log --since="7 days ago" --format="%s" 2>$null
    if ($recentCommits) {
        $fixCount = ($recentCommits | Where-Object { $_ -match "^fix:" }).Count
        $featCount = ($recentCommits | Where-Object { $_ -match "^feat:" }).Count
        $totalCommits = $recentCommits.Count
        
        $tag = "lesson:git-stats-$TODAY"
        if ($content -notmatch [regex]::Escape($tag)) {
            $lesson = "- [score: 0.6] [$tag] Semaine : $totalCommits commits ($featCount feat, $fixCount fix)"
            $content += "`n$lesson"
            Log "Stats git ajoutees" "Green"
        }
    }
    Pop-Location
} catch {
    Log "Git log extraction echouee: $_" "Yellow"
}

# 4. Sauvegarder
$content = $content -replace "Derniere maj : \d{4}-\d{2}-\d{2}", "Derniere maj : $TODAY"
$content | Set-Content $lessonsFile -Encoding UTF8

# 5. Creer une note Obsidian si necessaire
$lessonDir = "$DEV_CORE_DATA\Vault\Lessons\workflow"
New-Item -ItemType Directory -Path $lessonDir -Force | Out-Null
$noteFile = "$lessonDir\session_$TODAY.md"
if (-not (Test-Path $noteFile)) {
    @"
---
title: Session $TODAY
date: $TODAY
tags: [lesson, workflow, auto]
score: 0.5
---

# Session $TODAY

## Taches completees
$(if (Test-Path $tFile) {
    $board = Get-Content $tFile -Raw | ConvertFrom-Json
    $done = $board.tasks | Where-Object { $_.status -eq "done" }
    ($done | ForEach-Object { "- [x] $($_.id): $($_.title) ($($_.mode))" }) -join "`n"
} else { "Aucune" })

## Lecons
Voir LESSONS.md pour les lecons consolidees.

## Next actions
- [ ] Continuer les taches en attente
"@ | Set-Content $noteFile -Encoding UTF8
    Log "Note Obsidian creee : $noteFile" "Green"
}

Log "lesson_extractor termine" "Green"


