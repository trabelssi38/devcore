# new_project.ps1 -- DEV_CORE single client
param(
    [Parameter(Mandatory=$true)][string]$Name,
    [string]$Stack = "generic",
    [string]$Path = "",
    [switch]$InitializeLegacyTaskBoard
)

if (-not $Path) {
    $Path = (Get-Location).Path
}

$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { (Join-Path (Split-Path -Parent $PSScriptRoot) "DEV_CORE_DATA") }
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
$PLATFORM = Get-DevCorePlatformInfo

Write-Host ""
Write-Host "  $($PLATFORM.title) -- Initialisation Projet" -ForegroundColor Cyan
Write-Host "  ====================================" -ForegroundColor DarkGray
Write-Host ""

# 1. Creer .devcore/project.json
$devcoreDir = "$Path\.devcore"
if (-not (Test-Path $devcoreDir)) {
    New-Item -ItemType Directory -Path $devcoreDir -Force | Out-Null
}

$projData = @{
    name = $Name
    stack = $Stack
    path = $Path
    initialized_at = (Get-Date -Format "o")
}
$projData | ConvertTo-Json | Set-Content "$devcoreDir\project.json" -Encoding UTF8
Write-Host "  [OK] .devcore/project.json cree" -ForegroundColor Green

# 1.5. Mettre a jour le registre global des projets DEV_CORE
$registryRoot = if ($env:DEVCORE_CONFIG_ROOT) { $env:DEVCORE_CONFIG_ROOT } else { Join-Path $DEV_CORE "Config" }
$registryPath = Join-Path $registryRoot "projects.json"
$registryDir = Split-Path $registryPath
if (-not (Test-Path $registryDir)) {
    New-Item -ItemType Directory -Path $registryDir -Force | Out-Null
}

if (Test-Path $registryPath) {
    $registry = Get-Content $registryPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $registry = [pscustomobject]@{ projects = @() }
}

$projects = @()
if ($registry.projects) {
    $projects = @($registry.projects | Where-Object { $_.name -ne $Name })
}
$projects += [pscustomobject]@{
    name = $Name
    path = ($Path -replace "\\", "/")
}
[pscustomobject]@{ projects = @($projects | Sort-Object name) } |
    ConvertTo-Json -Depth 5 |
    Set-Content $registryPath -Encoding UTF8
Write-Host "  [OK] Registre projets DEV_CORE mis a jour" -ForegroundColor Green

# 2. Creer CLAUDE.md local si n'existe pas
$claudeMd = "$Path\CLAUDE.md"
if (-not (Test-Path $claudeMd)) {
    @"
# $Name

Stack: $Stack
Initialise avec $($PLATFORM.title).

## Commandes utiles
- \`dc next task\` : charger prochaine tache
- \`dc task done\` : valider la tache active
"@ | Set-Content $claudeMd -Encoding UTF8
    Write-Host "  [OK] CLAUDE.md local cree" -ForegroundColor Green
}

# Les taches actives sont dans SQLite. L'ancien board partage ne se cree que
# pour une migration historique demandee explicitement.
if ($InitializeLegacyTaskBoard) {
    $projDir = Join-Path (Join-Path $DEV_CORE_DATA "Memory") $Name
    New-Item -ItemType Directory -Path $projDir -Force | Out-Null
    $tFile = Join-Path $projDir "tasks.json"
    if (-not (Test-Path -LiteralPath $tFile)) {
        $board = @{
            project = $Name
            current_task = $null
            tasks = @()
            detected_from_git = @()
        }
        $board | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $tFile -Encoding UTF8
        Write-Host "  [OK] Nouveau tasks.json historique initialise pour $Name" -ForegroundColor Green
    }
}

# Synchroniser le workspace Repowise
$SCRIPTS = Split-Path -Parent $MyInvocation.MyCommand.Definition
if (Test-Path "$SCRIPTS\sync_repowise_workspace.py") {
    python "$SCRIPTS\sync_repowise_workspace.py" | Out-Null
    Write-Host "  [OK] Workspace Repowise synchronise pour $Name" -ForegroundColor Green
}

Write-Host ""
Write-Host "  Projet lie avec succes." -ForegroundColor Cyan
Write-Host ""
