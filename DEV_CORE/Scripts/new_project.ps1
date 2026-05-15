# new_project.ps1 -- DEV_CORE v6 single client
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
Write-Host "  DEV_CORE v6 -- Initialisation Projet" -ForegroundColor Cyan
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
    initialized_at = (Get-Date -Format "o")
}
$projData | ConvertTo-Json | Set-Content "$devcoreDir\project.json" -Encoding UTF8
Write-Host "  [OK] .devcore/project.json cree" -ForegroundColor Green

# 2. Creer CLAUDE.md local si n'existe pas
$claudeMd = "$Path\CLAUDE.md"
if (-not (Test-Path $claudeMd)) {
    @"
# $Name

Stack: $Stack
Initialise avec DEV_CORE v6.

## Commandes utiles
- \`dc next task\` : charger prochaine tache
- \`dc task done\` : valider la tache active
"@ | Set-Content $claudeMd -Encoding UTF8
    Write-Host "  [OK] CLAUDE.md local cree" -ForegroundColor Green
}

# 3. Initialiser tasks.json
$tFile = "$DEV_CORE_DATA\Memory\tasks.json"
if (-not (Test-Path $tFile)) {
    $board = @{
        project = $Name
        current_task = $null
        tasks = @()
        detected_from_git = @()
    }
    $board | ConvertTo-Json -Depth 5 | Set-Content $tFile -Encoding UTF8
    Write-Host "  [OK] tasks.json initialise pour le projet $Name" -ForegroundColor Green
} else {
    # Mettre a jour le nom du projet dans tasks.json
    $board = Get-Content $tFile -Raw | ConvertFrom-Json
    $board.project = $Name
    $board | ConvertTo-Json -Depth 10 | Set-Content $tFile -Encoding UTF8
    Write-Host "  [OK] tasks.json mis a jour pour le projet $Name" -ForegroundColor Green
}

Write-Host ""
Write-Host "  Projet lie avec succes." -ForegroundColor Cyan
Write-Host ""
