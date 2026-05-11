# session_start.ps1 -- DEV_CORE v6
# Declenche par le hook UserPromptSubmit de Claude Code
# S'execute au premier message de chaque session
# Ne jamais lancer manuellement

$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { "C:\DEV_CORE_DATA" }
$TODAY         = Get-Date -Format "yyyy-MM-dd"
$SESSION_FLAG  = "$DEV_CORE_DATA\Logs\scripts\session_started_$TODAY.flag"

# Eviter de relancer si deja execute aujourd'hui dans cette session
if (Test-Path $SESSION_FLAG) { exit 0 }

$LOG = "$DEV_CORE_DATA\Logs\scripts\session_start_$TODAY.log"
function Log { param($msg)
    $l = "[$(Get-Date -f HH:mm:ss)] $msg"
    Add-Content $LOG $l -ErrorAction SilentlyContinue
}

Log "session_start.ps1 declenche par hook UserPromptSubmit"

# 1. Creer le flag pour eviter les doublons
New-Item -ItemType File -Path $SESSION_FLAG -Force | Out-Null

# 2. Verifier si le projet est initialise
$projectFile = "$(Get-Location)\.devcore\project.json"
if (-not (Test-Path $projectFile)) {
    Log "Projet non initialise -- lancement new_project.ps1"
    $projName = Split-Path (Get-Location) -Leaf

    # Detection stack
    $stack = "generic"
    if ((Get-ChildItem -Filter "*.py" -ErrorAction SilentlyContinue).Count -gt 0 -or (Test-Path "pyproject.toml") -or (Test-Path "requirements.txt")) { $stack = "python" }
    elseif (Test-Path "package.json") { $stack = "web" }
    elseif ((Get-ChildItem -Filter "*.gradle" -ErrorAction SilentlyContinue).Count -gt 0) { $stack = "android" }

    & "$DEV_CORE\Scripts\new_project.ps1" -Name $projName -Stack $stack
    Log "new_project.ps1 termine -- nom: $projName, stack: $stack"
}

# 3. Lancer DEV_CORE (launch.ps1)
Log "Lancement launch.ps1"
& "$DEV_CORE\Scripts\launch.ps1" -QuickStart 2>>$LOG

# 4. Charger la mission active
Log "Chargement mission active"
& "$DEV_CORE\Scripts\dc.ps1" "next mission" 2>>$LOG

# 5. Lire le handoff precedent et l'ecrire dans un fichier contexte
$handoffPath = "$DEV_CORE_DATA\Memory\next_actions.md"
if (Test-Path $handoffPath) {
    $handoff = Get-Content $handoffPath -Raw
    Log "Handoff precedent charge -- $((Get-Content $handoffPath).Count) lignes"
    # Ecrire dans un fichier temporaire que Claude Code peut lire
    $handoff | Set-Content "$DEV_CORE_DATA\Logs\scripts\last_handoff.md" -Encoding UTF8
}

# 6. Lire la mission active et l'ecrire dans le contexte
$mFile = "$DEV_CORE_DATA\Memory\missions.json"
if (Test-Path $mFile) {
    $board  = Get-Content $mFile -Raw | ConvertFrom-Json
    $active = $board.missions | Where-Object { $_.status -eq "active" } | Select-Object -First 1
    if ($active) {
        $ctx = @"
[DEV_CORE] Session demarree -- $(Get-Date -f 'yyyy-MM-dd HH:mm')
[DEV_CORE] Projet  : $($board.project)
[DEV_CORE] Mission : $($active.id) -- $($active.title)
[DEV_CORE] Agent   : $($active.agent)
[DEV_CORE] Steps   : $($active.steps_done)/$($active.steps_total)
[DEV_CORE] Client  : $($board.active_client)
"@
        $ctx | Set-Content "$DEV_CORE_DATA\Logs\scripts\session_context.txt" -Encoding UTF8
        Log "Contexte mission ecrit : $($active.id)"
    }
}

Log "session_start.ps1 termine"
