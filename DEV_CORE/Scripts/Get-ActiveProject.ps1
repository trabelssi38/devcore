# Get-ActiveProject.ps1
# Détecte automatiquement le projet actif sans configuration
# Basé sur le répertoire racine Git, ou à défaut le répertoire courant.
# Utilise un cache en mémoire pour la session PowerShell courante.

$currentPwd = (Get-Location).Path

# Retourner le cache si le dossier courant n'a pas changé
if ($env:DEVCORE_ACTIVE_PROJECT_PWD -eq $currentPwd -and $env:DEVCORE_ACTIVE_PROJECT_NAME) {
    Write-Output $env:DEVCORE_ACTIVE_PROJECT_NAME
    exit 0
}

try {
    # 1. Vérifier si on est dans un dépôt Git
    $gitPath = git rev-parse --show-toplevel 2>$null
    
    if ($LASTEXITCODE -eq 0 -and $gitPath) {
        # Extraire le nom du dossier racine du dépôt
        $projectName = (Get-Item $gitPath).Name
    } else {
        # 2. Fallback: on prend le nom du dossier courant
        $projectName = (Get-Item .).Name
    }

    # Nettoyer le nom pour être un dossier valide (au cas où)
    $projectName = $projectName -replace '[\\/:*?"<>|]', '_'
    
    # Mettre en cache
    $env:DEVCORE_ACTIVE_PROJECT_PWD = $currentPwd
    $env:DEVCORE_ACTIVE_PROJECT_NAME = $projectName

    # Retourner uniquement le nom
    Write-Output $projectName
} catch {
    # Par sécurité, utiliser 'default' en cas d'erreur inattendue
    Write-Output "default_project"
}
