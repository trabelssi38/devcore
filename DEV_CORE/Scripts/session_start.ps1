# session_start.ps1 -- DEV_CORE v9.0 -- Single client -- ASCII safe
# Declenche par hook UserPromptSubmit de Claude Code
# Ne relance pas si deja execute aujourd'hui
param([switch]$RunLegacyGlobalMaintenance)

$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT -and (Test-Path (Join-Path $env:DEVCORE_PLATFORM_ROOT "Scripts\platform_version.ps1"))) {
    $env:DEVCORE_PLATFORM_ROOT
} elseif (Test-Path (Join-Path $PSScriptRoot "platform_version.ps1")) {
    Split-Path -Parent $PSScriptRoot
} elseif (Test-Path (Join-Path $PSScriptRoot "Scripts\platform_version.ps1")) {
    $PSScriptRoot
} elseif (Test-Path (Join-Path (Split-Path -Parent $PSScriptRoot) "DEV_CORE\Scripts\platform_version.ps1")) {
    Join-Path (Split-Path -Parent $PSScriptRoot) "DEV_CORE"
} else {
    Split-Path -Parent $PSScriptRoot
}
if ($DEV_CORE -match '[/\\]Scripts[/\\]?$') {
    $DEV_CORE = Split-Path -Parent $DEV_CORE
}
. "$DEV_CORE\Scripts\platform_version.ps1"

$DEV_CORE_DATA  = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { (Join-Path $DEV_CORE "DEV_CORE_DATA") }
$DEV_CORE_LOCAL = if ($env:DEVCORE_LOCAL_ROOT)    { $env:DEVCORE_LOCAL_ROOT }    elseif ($env:LOCALAPPDATA) { "$env:LOCALAPPDATA\DEV_CORE_LOCAL" } else { Join-Path ([System.IO.Path]::GetTempPath()) "DEV_CORE_LOCAL" }
$TODAY          = Get-Date -Format "yyyy-MM-dd"
$detectedProject = & "$PSScriptRoot\Get-ActiveProject.ps1" | Select-Object -Last 1
if ([string]::IsNullOrWhiteSpace($detectedProject)) {
    Write-Error "Session non demarree : aucun projet local explicite."
    exit 1
}
$projName       = $detectedProject.Trim()
if ($projName -cnotmatch '^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$') {
    throw 'Identifiant de projet invalide.'
}
$sha            = [System.Security.Cryptography.SHA256]::Create()
$projectKey     = [System.BitConverter]::ToString($sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($projName))).Replace('-', '').Substring(0, 16)
$sha.Dispose()
$userKey        = ($env:USERNAME -replace '[^A-Za-z0-9_-]', '_')
$LOG_DIR        = Join-Path (Join-Path $DEV_CORE_LOCAL "Logs\scripts") $projectKey
$SESSION_FLAG   = Join-Path $LOG_DIR "session_started_${TODAY}_${userKey}.flag"

New-Item -ItemType Directory -Path $LOG_DIR -Force | Out-Null
$LOG = "$LOG_DIR\session_start_$TODAY.log"
function Log { param($msg) Add-Content $LOG "[$(Get-Date -f HH:mm:ss)] $msg" -ErrorAction SilentlyContinue }

# 1. Reutiliser les metadonnees du projet parent ou initialiser sa racine Git.
$projectPath = (Get-Location).Path
$cursor = Get-Item -LiteralPath $projectPath
while ($cursor) {
    if (Test-Path -LiteralPath (Join-Path $cursor.FullName ".devcore\project.json")) {
        $projectPath = $cursor.FullName
        break
    }
    if (Test-Path -LiteralPath (Join-Path $cursor.FullName ".git")) {
        $projectPath = $cursor.FullName
        break
    }
    $cursor = $cursor.Parent
}
$projectFile = Join-Path $projectPath ".devcore\project.json"
if (-not (Test-Path $projectFile)) {
    $stack = "generic"
    if ((Get-ChildItem -LiteralPath $projectPath -Filter "*.py" -ErrorAction SilentlyContinue).Count -gt 0 -or
        (Test-Path (Join-Path $projectPath "pyproject.toml")) -or (Test-Path (Join-Path $projectPath "requirements.txt"))) { $stack = "python" }
    elseif (Test-Path (Join-Path $projectPath "package.json")) { $stack = "web" }
    elseif ((Get-ChildItem -LiteralPath $projectPath -Filter "*.gradle" -ErrorAction SilentlyContinue).Count -gt 0) { $stack = "android" }
    Log "Initialisation projet : $projName ($stack)"
    
    # Creer .devcore/project.json et enregistrer le projet
    $global:LASTEXITCODE = 0
    & "$PSScriptRoot\new_project.ps1" -Name $projName -Stack $stack -Path $projectPath 2>>$LOG
    if ($LASTEXITCODE -ne 0) { throw "Initialisation du projet echouee (code $LASTEXITCODE)." }
}

# Auto-installer ou mettre a jour le hook post-commit si .git existe
$gitHooksDir = Join-Path $projectPath ".git\hooks"
if (Test-Path $gitHooksDir) {
    $targetHook = "$gitHooksDir\post-commit"
    $sourceHook = "$DEV_CORE\Scripts\post-commit.hook"
    if (-not (Test-Path $targetHook) -or (Get-Item $sourceHook).LastWriteTime -gt (Get-Item $targetHook).LastWriteTime) {
        Copy-Item -Path $sourceHook -Destination $targetHook -Force
        Log "Hook post-commit installe ou mis a jour"
    }
}

try {
    $flagHandle = [System.IO.File]::Open($SESSION_FLAG, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
    $flagHandle.Dispose()
} catch [System.IO.IOException] {
    if (Test-Path -LiteralPath $SESSION_FLAG) { exit 0 }
    throw
}

$LOG = "$LOG_DIR\session_start_$TODAY.log"
try {
Log "session_start.ps1 -- hook auto"

# 2. Launch
Log "launch.ps1 (project: $projName)"
$global:LASTEXITCODE = 0
& "$DEV_CORE\Scripts\launch.ps1" -QuickStart --project $projName 2>>$LOG
if ($LASTEXITCODE -ne 0) {
    throw "Lancement de session echoue (code $LASTEXITCODE)."
}

# 2b. Verification base vectorielle unifiee SQLite-Vec
$dbFile = Join-Path $DEV_CORE_LOCAL "devcore.db"
if (Test-Path $dbFile) {
    Log "Base vectorielle sqlite-vec active"
}

# 3. Charger la tâche active depuis SQLite, sans utiliser le JSON partagé.
$platformPython = Get-DevCorePython
if (-not $env:PYTHONPATH -or $env:PYTHONPATH -notlike "*$DEV_CORE*") {
    $env:PYTHONPATH = if ($env:PYTHONPATH) { "$DEV_CORE;$env:PYTHONPATH" } else { $DEV_CORE }
}
$boardJson = & $platformPython -m devcore_engine.cli task board --project $projName --json 2>>$LOG
if ($LASTEXITCODE -ne 0) {
    Log "Lecture du board SQLite impossible ; aucune tâche automatique créée."
    Remove-Item -LiteralPath $SESSION_FLAG -Force -ErrorAction SilentlyContinue
    exit 1
} else {
    $board = ($boardJson | Out-String) | ConvertFrom-Json
    if ([string]$board.project -cne $projName) {
        throw "Board du mauvais projet : attendu $projName."
    }
    $pending = @($board.tasks | Where-Object { $_.status -in @("todo", "in_progress", "paused") })
    if ($pending.Count -eq 0) {
        Log "Aucune tâche en attente dans SQLite ; création de la tâche de session."
        $global:LASTEXITCODE = 0
        & "$PSScriptRoot\task_add.ps1" -Title "Session de travail auto ($TODAY)" -Mode "coding" -Project $projName 2>>$LOG
        if ($LASTEXITCODE -ne 0) { throw "Creation de tâche echouee (code $LASTEXITCODE)." }
    }
    Log "task_next.ps1 (project: $projName)"
    $global:LASTEXITCODE = 0
    & "$PSScriptRoot\task_next.ps1" --project $projName 2>>$LOG
    if ($LASTEXITCODE -ne 0) { throw "Selection de tâche echouee (code $LASTEXITCODE)." }
}

# 4. Auto-scan + sync en background (2.2)
Log "Auto-scan background"
$scanBlock = {
    param($dc, $project, $repo)
    & "$dc\Scripts\task_scan.ps1" -Project $project -RepoPath $repo 2>&1 | Out-Null
    & "$dc\Scripts\task_sync.ps1" 2>&1 | Out-Null
}
if (Test-Path -LiteralPath (Join-Path $projectPath ".git")) {
    Start-Job -ScriptBlock $scanBlock -ArgumentList $DEV_CORE, $projName, $projectPath | Out-Null
}

if ($RunLegacyGlobalMaintenance) {
    Write-Warning "Maintenance globale historique : peut ecrire dans DEVCORE_DATA_ROOT."
    $global:LASTEXITCODE = 0
    & "$DEV_CORE\Scripts\endday_check.ps1" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Maintenance globale echouee (code $LASTEXITCODE)." }
}

# Gen session context
Write-Host "  Session context" -ForegroundColor Cyan
$global:LASTEXITCODE = 0
& "$DEV_CORE\Scripts\gen_session_context.ps1" -Project $projName 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Generation du contexte echouee (code $LASTEXITCODE)." }
Log "session_start.ps1 termine"

} catch {
    Remove-Item -LiteralPath $SESSION_FLAG -Force -ErrorAction SilentlyContinue
    throw
}
