# lesson_extractor.ps1 — DEV_CORE v6 Auto layer
$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { "C:\DEV_CORE_DATA" }
$TODAY         = Get-Date -Format "yyyy-MM-dd"
$LOG           = "$DEV_CORE_DATA\Logs\scripts\lesson_extractor_$TODAY.log"
function Log { param($msg,$color="Gray"); $l="[$(Get-Date -f HH:mm:ss)] $msg"; Add-Content $LOG $l -ErrorAction SilentlyContinue; Write-Host "    $l" -ForegroundColor $color }
Log "lesson_extractor — extraction leçons de la session" "Cyan"
$sessLog = "$DEV_CORE_DATA\Logs\scripts\session_$TODAY.log"
if (-not (Test-Path $sessLog)) { Log "Pas de session log pour $TODAY" "Yellow"; exit 0 }
$content = Get-Content $sessLog -Raw
# Créer une leçon générique depuis le log
$lessonDir = "$DEV_CORE_DATA\Vault\Lessons\workflow"
New-Item -ItemType Directory -Path $lessonDir -Force | Out-Null
$lesson = @"
---
title: Session $TODAY
date: $TODAY
tags: [lesson, workflow, auto]
score: 0.5
---

# Session $TODAY

## Contexte
Session de travail automatiquement capturée.

## Leçon
[Compléter manuellement si insight important]

## Application
[Action concrète pour la prochaine session]
"@
$lesson | Set-Content "$lessonDir\session_$TODAY.md" -Encoding UTF8
Log "Leçon créée : $lessonDir\session_$TODAY.md" "Green"
