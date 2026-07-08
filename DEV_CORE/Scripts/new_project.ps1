# new_project.ps1 -- DEV_CORE v9.0 single client
param(
    [Parameter(Mandatory=$true)][string]$Name,
    [string]$Stack = "generic",
    [string]$Path = ""
)

if (-not $Path) {
    $Path = (Get-Location).Path
}

$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { "C:\devcore\DEV_CORE_DATA" }

Write-Host ""
Write-Host "  DEV_CORE v9.0 -- Initialisation Projet" -ForegroundColor Cyan
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
$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$registryPath = "$DEV_CORE\Config\projects.json"
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
Initialise avec DEV_CORE v9.0.

## Commandes utiles
- \`dc next task\` : charger prochaine tache
- \`dc task done\` : valider la tache active
"@ | Set-Content $claudeMd -Encoding UTF8
    Write-Host "  [OK] CLAUDE.md local cree" -ForegroundColor Green
}

# 3. Gerer tasks.json (chaque projet a son propre dossier isolé)
$projDir = "$DEV_CORE_DATA\Memory\$Name"
if (-not (Test-Path $projDir)) {
    New-Item -ItemType Directory -Path $projDir -Force | Out-Null
}
$tFile = "$projDir\tasks.json"

if (-not (Test-Path $tFile)) {
    # Creer un nouveau fichier vierge
    $board = @{
        project = $Name
        current_task = $null
        tasks = @()
        detected_from_git = @()
    }
    $board | ConvertTo-Json -Depth 5 | Set-Content $tFile -Encoding UTF8
    Write-Host "  [OK] Nouveau tasks.json initialise pour le projet $Name" -ForegroundColor Green
} else {
    Write-Host "  [INFO] Contexte des taches deja actif pour $Name" -ForegroundColor DarkGray
}

# Convertir en TOON immediatement
$SCRIPTS = Split-Path -Parent $MyInvocation.MyCommand.Definition
& "$SCRIPTS\toonify.ps1" -InputFile $tFile | Out-Null

Write-Host ""
Write-Host "  Projet lie avec succes." -ForegroundColor Cyan
Write-Host ""
