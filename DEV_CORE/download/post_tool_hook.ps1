# post_tool_hook.ps1 -- DEV_CORE v6
# Declenche par le hook PostToolUse(Bash) de Claude Code
# Verifie apres chaque outil Bash si la mission est complete

$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { "C:\DEV_CORE_DATA" }
$mFile         = "$DEV_CORE_DATA\Memory\missions.json"

if (-not (Test-Path $mFile)) { exit 0 }

$board  = Get-Content $mFile -Raw | ConvertFrom-Json
$active = $board.missions | Where-Object { $_.status -eq "active" } | Select-Object -First 1

if (-not $active) { exit 0 }

# Verifier si toutes les steps sont done
if ($active.steps_done -ge $active.steps_total) {
    $flagFile = "$DEV_CORE_DATA\Logs\scripts\mission_complete_$($active.id).flag"
    if (-not (Test-Path $flagFile)) {
        # Creer le flag pour eviter les doublons
        New-Item -ItemType File -Path $flagFile -Force | Out-Null

        # Declencher mission_done.ps1
        & "$DEV_CORE\Scripts\mission_done.ps1" -Force

        # Ecrire le signal pour Claude Code
        "[DEV_CORE] MISSION_COMPLETE -- $($active.id) done -- Lancer : dc next mission" |
            Set-Content "$DEV_CORE_DATA\Logs\scripts\mission_complete_signal.txt" -Encoding UTF8
    }
}
