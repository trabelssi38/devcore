# session_end.ps1 -- DEV_CORE
# Execute a la fin de session Claude Code
# 1. Sync Qdrant
# 2. Sync Obsidian
# 3. Genere metrics
param(
    [string]$Project,
    [string]$RepoPath,
    [switch]$RunLegacyGlobalMaintenance
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

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
$projName = if ($Project) { $Project.Trim() } else { (& "$DEV_CORE\Scripts\Get-ActiveProject.ps1" | Select-Object -Last 1).Trim() }
if (-not $projName) { throw "Un projet est requis pour terminer la session." }
if ($projName -cnotmatch '^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$') { throw "Identifiant de projet invalide." }

$DEV_CORE_LOCAL = if ($env:DEVCORE_LOCAL_ROOT) { $env:DEVCORE_LOCAL_ROOT } elseif ($env:LOCALAPPDATA) { Join-Path $env:LOCALAPPDATA "DEV_CORE_LOCAL" } else { Join-Path ([System.IO.Path]::GetTempPath()) "DEV_CORE_LOCAL" }
$TODAY         = Get-Date -Format "yyyy-MM-dd"
$sha           = [System.Security.Cryptography.SHA256]::Create()
$projectKey    = [System.BitConverter]::ToString($sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($projName))).Replace('-', '').Substring(0, 16)
$sha.Dispose()
$LOG_DIR       = Join-Path (Join-Path $DEV_CORE_LOCAL "Logs\scripts") $projectKey
$LOG           = "$LOG_DIR\session_end_$TODAY.log"
$PLATFORM = Get-DevCorePlatformInfo

New-Item -ItemType Directory -Path $LOG_DIR -Force | Out-Null

function Log {
    param($msg, $color="Cyan")
    Write-Host "  $msg" -ForegroundColor $color
    Add-Content $LOG "[$(Get-Date -f HH:mm:ss)] $msg" -ErrorAction SilentlyContinue
}

Write-Host ""
Log "$($PLATFORM.title) -- Session End" "Cyan"
Log "========================================" "DarkGray"
Log "Date: $TODAY" "White"
Write-Host ""

Log "[1/3] Generation metrics ($projName)..." "Cyan"
$global:LASTEXITCODE = 0
& "$DEV_CORE\Scripts\gen_metrics.ps1" -Project $projName 2>&1 | Tee-Object -FilePath $LOG -Append
if ($LASTEXITCODE -ne 0) { throw "Generation metrics echouee (code $LASTEXITCODE)." }

if (-not $RepoPath) {
    $gitRoot = git rev-parse --show-toplevel 2>$null
    if ($LASTEXITCODE -eq 0 -and $gitRoot) { $RepoPath = ($gitRoot | Select-Object -Last 1).Trim() }
}
if ($RepoPath) {
    Log "[2/3] Task scan ($projName)..." "Cyan"
    $global:LASTEXITCODE = 0
    & "$DEV_CORE\Scripts\task_scan.ps1" -Project $projName -RepoPath $RepoPath 2>&1 | Tee-Object -FilePath $LOG -Append
    if ($LASTEXITCODE -ne 0) { throw "Task scan echoue (code $LASTEXITCODE)." }
} else {
    Log "[2/3] Aucun depot Git pour $projName ; scan ignore." "Yellow"
}

Log "[3/3] Task sync + Dashboard..." "Cyan"
$global:LASTEXITCODE = 0
& "$DEV_CORE\Scripts\task_sync.ps1" 2>&1 | Tee-Object -FilePath $LOG -Append
if ($LASTEXITCODE -ne 0) { throw "Task sync echoue (code $LASTEXITCODE)." }

if ($RunLegacyGlobalMaintenance) {
    Write-Warning "Maintenance globale historique : peut ecrire dans DEVCORE_DATA_ROOT."
    Log "Sync Knowledge / Vector Memory..." "Cyan"
    $global:LASTEXITCODE = 0
    & "$DEV_CORE\Scripts\qdrant_sync.ps1" 2>&1 | Tee-Object -FilePath $LOG -Append
    if ($LASTEXITCODE -ne 0) { throw "Qdrant sync echoue (code $LASTEXITCODE)." }
    Log "Sync Obsidian..." "Cyan"
    $global:LASTEXITCODE = 0
    & "$DEV_CORE\Scripts\obsidian_sync.ps1" -Project $projName 2>&1 | Tee-Object -FilePath $LOG -Append
    if ($LASTEXITCODE -ne 0) { throw "Obsidian sync echoue (code $LASTEXITCODE)." }
    Log "Endday check..." "Cyan"
    $global:LASTEXITCODE = 0
    & "$DEV_CORE\Scripts\endday_check.ps1" 2>&1 | Tee-Object -FilePath $LOG -Append
    if ($LASTEXITCODE -ne 0) { throw "Endday check echoue (code $LASTEXITCODE)." }
}

Write-Host ""
Log "========================================" "Green"
Log "||  Session end complete               ||" "Green"
Log "========================================" "Green"
Write-Host ""
