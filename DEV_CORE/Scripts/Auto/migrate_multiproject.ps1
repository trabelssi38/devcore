# migrate_multiproject.ps1
# Ce script migre l'état global (tasks.json) vers le sous-dossier du projet correspondant.

$DEV_CORE = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
. "$DEV_CORE\Scripts\platform_version.ps1"

$DATA_ROOT = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { Join-Path $DEV_CORE "DEV_CORE_DATA" }
$MEM_DIR = "$DATA_ROOT\Memory"

Write-Host "Recherche de tâches globales à migrer..." -ForegroundColor Cyan

if (Test-Path "$MEM_DIR\tasks.json") {
    $tasks = Get-Content "$MEM_DIR\tasks.json" -Raw | ConvertFrom-Json
    $projName = $tasks.project
    
    if ([string]::IsNullOrWhiteSpace($projName)) { 
        $projName = "default_project" 
    }
    
    $projDir = "$MEM_DIR\$projName"
    
    if (-not (Test-Path $projDir)) {
        New-Item -ItemType Directory -Path $projDir | Out-Null
        Write-Host "Dossier projet créé: $projDir" -ForegroundColor DarkGray
    }
    
    Write-Host "Migration de '$projName' vers $projDir..." -ForegroundColor Yellow
    
    # Déplacement des fichiers
    Move-Item "$MEM_DIR\tasks.json" "$projDir\tasks.json" -Force
    
    if (Test-Path "$MEM_DIR\tasks.toon") {
        Move-Item "$MEM_DIR\tasks.toon" "$projDir\tasks.toon" -Force
    }
    
    Write-Host "Migration terminée pour le projet '$projName' !" -ForegroundColor Green
} else {
    Write-Host "Aucun fichier tasks.json global trouvé. Migration déjà effectuée ?" -ForegroundColor Yellow
}
