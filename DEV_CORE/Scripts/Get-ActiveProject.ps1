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
    # 1. Vérifier si on est dans un dépôt Git et identifier le projet canonique
    $gitCommonDir = git rev-parse --git-common-dir 2>$null
    if ($LASTEXITCODE -eq 0 -and $gitCommonDir) {
        $absoluteCommonDir = (Resolve-Path $gitCommonDir -ErrorAction SilentlyContinue).Path
        if ($absoluteCommonDir -match "\\.git$") {
            $projectName = (Get-Item -Force $absoluteCommonDir).Parent.Name
        } else {
            $projectName = (Get-Item -Force $absoluteCommonDir).Name
        }

        # Détecter si on est dans un worktree
        $topLevel = git rev-parse --show-toplevel 2>$null
        $worktreeName = "main"
        if ($LASTEXITCODE -eq 0 -and $topLevel) {
            $wtFolder = (Get-Item -Force $topLevel).Name
            if ($wtFolder -ne $projectName) {
                $worktreeName = $wtFolder
            }
        }
    } else {
        # 2. Fallback: on prend le nom du dossier courant
        $projectName = (Get-Item -Force .).Name
        $worktreeName = "main"
    }

    # Nettoyer les noms pour être valides
    $projectName = $projectName -replace '[\\/:*?"<>|]', '_'
    $worktreeName = $worktreeName -replace '[\\/:*?"<>|]', '_'
    
    # Mettre en cache
    $env:DEVCORE_ACTIVE_PROJECT_PWD = $currentPwd
    $env:DEVCORE_ACTIVE_PROJECT_NAME = $projectName
    $env:DEVCORE_ACTIVE_WORKTREE_NAME = $worktreeName

    # Retourner uniquement le nom canonique
    Write-Output $projectName
} catch {
    # Par sécurité, utiliser 'default' en cas d'erreur inattendue
    Write-Output "default_project"
}
