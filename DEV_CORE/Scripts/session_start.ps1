# session_start.ps1 -- DEV_CORE v6 -- Single client -- ASCII safe
# Declenche par hook UserPromptSubmit de Claude Code
# Ne relance pas si deja execute aujourd'hui

$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { "C:\DEV_CORE_DATA" }
$TODAY         = Get-Date -Format "yyyy-MM-dd"
$LOG_DIR       = "$DEV_CORE_DATA\Logs\scripts"
$SESSION_FLAG  = "$LOG_DIR\session_started_$TODAY.flag"

New-Item -ItemType Directory -Path $LOG_DIR -Force | Out-Null
$LOG = "$LOG_DIR\session_start_$TODAY.log"
function Log { param($msg) Add-Content $LOG "[$(Get-Date -f HH:mm:ss)] $msg" -ErrorAction SilentlyContinue }

# 1. Init projet si absent
$projectFile = "$(Get-Location)\.devcore\project.json"
if (-not (Test-Path $projectFile)) {
    $projName = Split-Path (Get-Location) -Leaf
    $stack = "generic"
    if ((Get-ChildItem -Filter "*.py" -ErrorAction SilentlyContinue).Count -gt 0 -or
        (Test-Path "pyproject.toml") -or (Test-Path "requirements.txt")) { $stack = "python" }
    elseif (Test-Path "package.json") { $stack = "web" }
    elseif ((Get-ChildItem -Filter "*.gradle" -ErrorAction SilentlyContinue).Count -gt 0) { $stack = "android" }
    Log "Initialisation projet : $projName ($stack)"
    
    # Creer .devcore/project.json
    New-Item -ItemType Directory -Path "$(Get-Location)\.devcore" -Force | Out-Null
    @{ name = $projName; stack = $stack; initialized_at = (Get-Date -f "o") } | ConvertTo-Json | Set-Content $projectFile -Encoding UTF8
    
    # Auto-installer le hook post-commit si .git existe
    $gitHooksDir = "$(Get-Location)\.git\hooks"
    if (Test-Path $gitHooksDir) {
        Copy-Item -Path "$DEV_CORE\Scripts\post-commit.hook" -Destination "$gitHooksDir\post-commit" -Force
        Log "Hook post-commit installe automatiquement"
    }
}

if (Test-Path $SESSION_FLAG) { exit 0 }
New-Item -ItemType File -Path $SESSION_FLAG -Force | Out-Null

$LOG = "$LOG_DIR\session_start_$TODAY.log"
Log "session_start.ps1 -- hook UserPromptSubmit"

# 2. Launch
Log "launch.ps1"
& "$DEV_CORE\Scripts\launch.ps1" -QuickStart 2>>$LOG

# 3. Charger la tache active (tasks.json en priorite, missions.json en fallback)
$tFile = "$DEV_CORE_DATA\Memory\tasks.json"
$mFile = "$DEV_CORE_DATA\Memory\missions.json"

if (Test-Path $tFile) {
    Log "task_next.ps1"
    & "$DEV_CORE\Scripts\task_next.ps1" 2>>$LOG
} elseif (Test-Path $mFile) {
    Log "mission_next.ps1 (fallback)"
    & "$DEV_CORE\Scripts\mission_next.ps1" 2>>$LOG
} else {
    Log "Aucun board de taches -- dc new task ou dc new project"
}

Log "session_start.ps1 termine"

# 9. Endday check
Write-Host "  9/9 Endday verification" -ForegroundColor Cyan
& "$DEV_CORE\Scripts\endday_check.ps1" 2>$null

# 10. Gen session context
Write-Host "  10/10 Session context" -ForegroundColor Cyan
& "$DEV_CORE\Scripts\gen_session_context.ps1" 2>$null
