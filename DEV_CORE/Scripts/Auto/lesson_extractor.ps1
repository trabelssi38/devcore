# lesson_extractor.ps1 -- DEV_CORE Auto layer
# Extrait les lecons depuis : git log, tasks done, MEMORY.md
$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { "C:\devcore\DEV_CORE_DATA" }
$TODAY         = Get-Date -Format "yyyy-MM-dd"
$LOG           = "$DEV_CORE_DATA\Logs\scripts\lesson_extractor_$TODAY.log"
. "$DEV_CORE\Scripts\platform_version.ps1"
$PLATFORM = Get-DevCorePlatformInfo
  function Log { param($msg,$color="Gray"); $l="[$(Get-Date -f HH:mm:ss)] $msg"; Add-Content $LOG $l -ErrorAction SilentlyContinue; Write-Host "    $l" -ForegroundColor $color }
Log "$($PLATFORM.title) lesson_extractor -- extraction multi-source" "Cyan"

$lessonsFile = "$DEV_CORE_DATA\Memory\LESSONS.md"
$tFile       = "$DEV_CORE_DATA\Memory\$(& "$PSScriptRoot\..\Get-ActiveProject.ps1")\tasks.json"
$existed     = Test-Path $lessonsFile

# 1. Creer LESSONS.md si absent
if (-not $existed) {
    @"
# LESSONS.md -- $($PLATFORM.title)
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
            
            $lesson = "- [score: 0.7] [created: $TODAY] [$tag] $($t.title) ($($t.mode)) : $stepsInfo"
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
            $lesson = "- [score: 0.6] [created: $TODAY] [$tag] Semaine : $totalCommits commits ($featCount feat, $fixCount fix)"
            $content += "`n$lesson"
            Log "Stats git ajoutees" "Green"
        }
    }
    Pop-Location
} catch {
    Log "Git log extraction echouee: $_" "Yellow"
}

# 3.5 Apply Score Decay
Log "Application du Score Decay sur LESSONS.md..." "Cyan"
$lines = $content -split "\r?\n"
$updatedLines = @()
$now = Get-Date

foreach ($line in $lines) {
    if ($line -match '^\-\s*\[score:\s*([\d\.]+)\](.*)') {
        $score = [double]$Matches[1]
        $rest = $Matches[2]
        
        # Extrait la date d'origine si présente
        $entryDate = $now
        if ($rest -match '\[created:\s*(\d{4}\-\d{2}\-\d{2})\]') {
            try { $entryDate = [datetime]::Parse($Matches[1]) } catch {}
        } else {
            # Injecte la date créée du jour si manquante
            $rest = " [created: $TODAY]" + $rest
        }

        $ageDays = ($now - $entryDate).TotalDays
        $multiplier = 1.0
        if ($ageDays -gt 180) { $multiplier = 0.5 }
        elseif ($ageDays -gt 90) { $multiplier = 0.7 }
        elseif ($ageDays -gt 30) { $multiplier = 0.9 }

        $newScore = [math]::Round($score * $multiplier, 2)

        if ($newScore -ge 0.3) {
            $updatedLines += "- [score: $newScore]$rest"
        } else {
            Log "  [Decay] Entree supprimee (score $newScore < 0.3, age: $([int]$ageDays)j)" "Yellow"
        }
    } else {
        $updatedLines += $line
    }
}
$content = $updatedLines -join "`n"

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

