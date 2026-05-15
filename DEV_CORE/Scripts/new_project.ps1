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

# 3. Gerer tasks.json (changement de contexte projet)
$tFile = "$DEV_CORE_DATA\Memory\tasks.json"
$archiveDir = "$DEV_CORE_DATA\Memory\Projects"
if (-not (Test-Path $archiveDir)) { New-Item -ItemType Directory -Path $archiveDir -Force | Out-Null }

if (Test-Path $tFile) {
    $currentBoard = Get-Content $tFile -Raw | ConvertFrom-Json
    $oldProject = $currentBoard.project
    
    if ($oldProject -and $oldProject -ne $Name) {
        # Archiver les taches de l'ancien projet
        $oldArchiveFile = "$archiveDir\tasks_$oldProject.json"
        Copy-Item -Path $tFile -Destination $oldArchiveFile -Force
        Write-Host "  [OK] Contexte de l'ancien projet ($oldProject) sauvegarde" -ForegroundColor Yellow
        Remove-Item -Path $tFile -Force
    }
}

# 4. Restaurer ou creer le tasks.json du nouveau projet
$newArchiveFile = "$archiveDir\tasks_$Name.json"
if (-not (Test-Path $tFile)) {
    if (Test-Path $newArchiveFile) {
        # Restaurer l'historique existant
        Copy-Item -Path $newArchiveFile -Destination $tFile -Force
        Write-Host "  [OK] Historique des taches restaure pour le projet $Name" -ForegroundColor Green
    } else {
        # Creer un nouveau fichier vierge
        $board = @{
            project = $Name
            current_task = $null
            tasks = @()
            detected_from_git = @()
        }
        $board | ConvertTo-Json -Depth 5 | Set-Content $tFile -Encoding UTF8
        Write-Host "  [OK] Nouveau tasks.json initialise pour le projet $Name" -ForegroundColor Green
    }
} else {
    Write-Host "  [INFO] Contexte des taches deja actif pour $Name" -ForegroundColor DarkGray
}

# Convertir en TOON immediatement
$SCRIPTS = Split-Path -Parent $MyInvocation.MyCommand.Definition
& "$SCRIPTS\toonify.ps1" -InputFile $tFile | Out-Null

Write-Host ""
Write-Host "  Projet lie avec succes." -ForegroundColor Cyan
Write-Host ""
