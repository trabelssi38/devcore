# post_tool_hook.ps1 -- DEV_CORE v9.0 -- Full Autonomy
# Declenche par le hook PostToolUse(Bash) / AfterTool(Gemini)
# 1. Verifie si la tache active est complete
# 2. Detecte les commits [T-XX] pour auto-incrementer steps
# 3. Integrity check steps_done vs steps reellement done

$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { $PSScriptRoot }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { (Join-Path (Split-Path -Parent $PSScriptRoot) "DEV_CORE_DATA") }
$tFile         = "$DEV_CORE_DATA\Memory\$(& "$PSScriptRoot\Get-ActiveProject.ps1")\tasks.json"

if (-not (Test-Path $tFile)) { exit 0 }

$board  = Get-Content $tFile -Raw | ConvertFrom-Json
$active = $board.tasks | Where-Object { $_.status -eq "active" } | Select-Object -First 1

if (-not $active) { exit 0 }

# --- Integrity check (4.4) ---
if ($active.steps -and $active.steps.Count -gt 0) {
    $realDone = @($active.steps | Where-Object { $_.done }).Count
    if ($active.steps_done -ne $realDone) {
        $active.steps_done = $realDone
    }
}

# --- Git commit detection (3.2) ---
try {
    $lastMsg = git log -1 --pretty=%B 2>$null
    if ($lastMsg -match '\[T-(\d+)\]') {
        $tagId = "T-{0:D2}" -f [int]$Matches[1]
        if ($tagId -eq $active.id) {
            # Le commit concerne la tache active : marquer la prochaine step
            if ($active.steps -and $active.steps.Count -gt 0) {
                $nextStep = $active.steps | Where-Object { -not $_.done } | Select-Object -First 1
                if ($nextStep) {
                    $nextStep.done = $true
                    $active.steps_done = @($active.steps | Where-Object { $_.done }).Count
                }
            }
        }
    }
} catch {}

# --- Auto-backup avant ecriture (4.3) ---
$bkpDir = "$DEV_CORE_DATA\Backups\auto"
if (-not (Test-Path $bkpDir)) { New-Item -ItemType Directory -Path $bkpDir -Force | Out-Null }
Copy-Item $tFile "$bkpDir\tasks_$(Get-Date -f 'yyyyMMdd_HHmmss').json" -Force -ErrorAction SilentlyContinue

# --- Sauvegarder les corrections d'integrite ---
$board | ConvertTo-Json -Depth 10 | Set-Content $tFile -Encoding UTF8

# --- Auto-completion check ---
if ($active.steps_done -ge $active.steps_total) {
    $flagFile = "$DEV_CORE_DATA\Logs\scripts\task_complete_$($active.id).flag"
    if (-not (Test-Path $flagFile)) {
        New-Item -ItemType File -Path $flagFile -Force | Out-Null
        & "$DEV_CORE\Scripts\task_done.ps1" -Force
    }
} else {
    # Mettre à jour le canvas pour la progression des steps
    & "$DEV_CORE\Scripts\canvas_manager.ps1" -Action Update
}


