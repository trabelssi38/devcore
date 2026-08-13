# obsidian_sync.ps1 -- DEV_CORE
# Sync accomplishments vers Obsidian Daily Note

$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { Split-Path -Parent $PSScriptRoot }
if ($DEV_CORE -match '[/\\]Scripts[/\\]?$') {
    $DEV_CORE = Split-Path -Parent $DEV_CORE
}
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { (Join-Path (Split-Path -Parent $PSScriptRoot) "DEV_CORE_DATA") }
$TODAY = Get-Date -Format "yyyy-MM-dd"
$NOTE_PATH = "$DEV_CORE_DATA\Vault\Daily Notes\$TODAY.md"
. "$DEV_CORE\Scripts\platform_version.ps1"
$PLATFORM = Get-DevCorePlatformInfo

function Write-Log {
    param([string]$msg, [string]$color="Gray")
    $l = "[$(Get-Date -f HH:mm:ss)] $msg"
    Write-Host "    $l" -ForegroundColor $color
}

Write-Host ""
Write-Host "  $($PLATFORM.title) -- Obsidian Sync" -ForegroundColor Cyan

# Create daily note if not exists
if (-not (Test-Path $NOTE_PATH)) {
    New-Item -ItemType Directory -Path (Split-Path $NOTE_PATH) -Force | Out-Null
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

## Next actions
- [ ]
"@ | Set-Content $NOTE_PATH -Encoding UTF8
    Write-Log "Daily Note creee" "Green"
}

# Lire le board de taches
$tFile = "$DEV_CORE_DATA\Memory\$(& "$PSScriptRoot\Get-ActiveProject.ps1")\tasks.json"
if (Test-Path $tFile) {
    $board = Get-Content $tFile -Raw | ConvertFrom-Json
    $doneTasks = $board.tasks | Where-Object { $_.status -eq "done" }
    Write-Log "Taches completees: $($doneTasks.Count)" "Green"

    # Update Daily Note with accomplishments
    if ($doneTasks.Count -gt 0) {
        $note = Get-Content $NOTE_PATH -Raw

        # Build accomplishments list
        $accList = "## Taches accomplies`n`n"
        foreach ($t in $doneTasks) {
            $accList += "- [x] **$($t.id)**: $($t.title)`n"
        }

        # Replace or append section
        if ($note -match "## Taches accomplies") {
            $note = $note -replace "## Taches accomplies[\s\S]*?(?=\n##|$)", $accList
        } else {
            $note += "`n$accList"
        }

        $note | Set-Content $NOTE_PATH -Encoding UTF8
        Write-Log "Daily Note mise a jour avec $($doneTasks.Count) taches" "Green"
    }
}

Write-Log "Obsidian sync termine" "Green"
Write-Host ""

