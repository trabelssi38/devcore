# task_git_scanner.ps1 -- DEV_CORE v6 Auto layer
# Scan git commits pour detecter les tags [T-XX] manquants

$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { "C:\devcore\DEV_CORE_DATA" }
$TODAY         = Get-Date -Format "yyyy-MM-dd"
$LOG           = "$DEV_CORE_DATA\Logs\scripts\task_git_scanner_$TODAY.log"
$projName      = & "$PSScriptRoot\..\Get-ActiveProject.ps1"
$QUEUE         = "$DEV_CORE_DATA\Memory\$projName\task_git_queue.jsonl"

function Log { param($msg,$color="Gray")
    $l = "[$(Get-Date -f HH:mm:ss)] $msg"
    Add-Content $LOG $l -ErrorAction SilentlyContinue
    Write-Host "    $l" -ForegroundColor $color
}

Log "task_git_scanner -- analyse commits" "Cyan"

# Rأ©soudre le dأ©pأ´t du projet actif (pas forcأ©ment C:\devcore)
$gitRoot = git rev-parse --show-toplevel 2>$null
if ($gitRoot) { Push-Location $gitRoot } else { Push-Location (Split-Path -Parent $DEV_CORE) }
try {
    # 1. Lire les commits des 30 derniers jours
    $commits = git log --since="30 days ago" --format="%H|%s|%ai" 2>$null
    if (-not $commits) {
        Log "Aucun commit recent trouve" "Yellow"
        return
    }

    # 2. Extraire les tags [T-XX]
    $foundTags = @{}
    foreach ($line in $commits) {
        if ($line -match '\[T-(\d+)\]') {
            $tag = "T-{0:D2}" -f [int]$Matches[1]
            $foundTags[$tag] = $true
            Log "Commit detecte : $tag" "Gray"
        }
    }

    # 3. Lire tasks.json
    $tFile = "$DEV_CORE_DATA\Memory\$(& "$PSScriptRoot\..\Get-ActiveProject.ps1")\tasks.json"
    if (-not (Test-Path $tFile)) {
        Log "tasks.json absent - creation" "Yellow"
        @{
            project="auto-detected"
            current_task=$null
            tasks=@()
            detected_from_git=@()
        } | ConvertTo-Json -Depth 5 | Set-Content $tFile -Encoding UTF8
        return
    }

    $board = Get-Content $tFile -Raw | ConvertFrom-Json
    if (-not $board.detected_from_git) {
        $board | Add-Member -NotePropertyName "detected_from_git" -NotePropertyValue @() -Force
    }

    # 4. Comparer avec tasks.json
    $missing = @()
    foreach ($tag in $foundTags.Keys) {
        $exists = $board.tasks | Where-Object { $_.id -eq $tag }
        if (-not $exists) {
            $missing += @{
                id = $tag
                source = "git"
                reason = "tag_found_in_commit"
                detected = $TODAY
                worktree = if ($env:DEVCORE_ACTIVE_WORKTREE_NAME) { $env:DEVCORE_ACTIVE_WORKTREE_NAME } else { "main" }
            }
            Log "TAG MANQUANT : $tag" "Yellow"
        }
    }

    # 5. Sauvegarder les tags trouves
    $board.detected_from_git = @($foundTags.Keys)
    $board | ConvertTo-Json -Depth 10 | Set-Content $tFile -Encoding UTF8

    # 6. Ecrire la queue pour traitement
    if ($missing.Count -gt 0) {
        $missing | ForEach-Object {
            Add-Content $QUEUE ($_ | ConvertTo-Json -Compress)
        }
        Log "$($missing.Count) tags manquants ajoutes a la queue" "Green"
    } else {
        Log "Tous les tags git sont dans tasks.json" "Green"
    }

    # 7. Alerter sur les taches sans commit recent
    $stale = @()
    foreach ($task in $board.tasks) {
        if ($task.status -eq "active") {
            $hasCommit = $foundTags.ContainsKey($task.id)
            if (-not $hasCommit) {
                $stale += $task.id
                Log "TACHE SANS COMMIT RECENT : $($task.id) - $($task.title)" "Yellow"
            }
        }
    }

    if ($stale.Count -eq 0) {
        Log "Toutes les taches actives ont des commits recents" "Green"
    }

} catch {
    Log "Erreur git : $_" "Red"
} finally {
    Pop-Location
}


