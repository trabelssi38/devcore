# Get-ActiveProject.ps1
# Détecte automatiquement le projet actif sans configuration
# Basé sur le répertoire racine Git, ou à défaut le répertoire courant.
# Utilise un cache en mémoire pour la session PowerShell courante.

. (Join-Path $PSScriptRoot "platform_version.ps1")

$currentPwd = (Get-Location).Path

# Retourner le cache si le dossier courant n'a pas changé
if ($env:DEVCORE_ACTIVE_PROJECT_PWD -eq $currentPwd -and $env:DEVCORE_ACTIVE_PROJECT_NAME) {
    Write-Output $env:DEVCORE_ACTIVE_PROJECT_NAME
    exit 0
}

try {
    # 0. Vérifier s'il y a un fichier .devcore/project.json dans le dossier courant ou ses parents (très utile en sandbox/worktree)
    $dir = Get-Item .
    $projectName = $null
    $worktreeName = "main"
    while ($dir) {
        $projectJsonPath = Join-Path $dir.FullName ".devcore\project.json"
        if (Test-Path -LiteralPath $projectJsonPath) {
            try {
                $projObj = Get-Content -Raw -LiteralPath $projectJsonPath -ErrorAction SilentlyContinue | ConvertFrom-Json
                if ($projObj -and $projObj.name) {
                    $projectName = $projObj.name
                    break
                }
            } catch {}
        }
        $dir = $dir.Parent
    }

    # 1. Fallback sur le dépôt Git ou le dossier courant
    if (-not $projectName) {
        $dir = Get-Item .
        $gitDir = $null
        while ($dir) {
            $testPath = Join-Path $dir.FullName ".git"
            if (Test-Path -LiteralPath $testPath) {
                $gitDir = $testPath
                break
            }
            $dir = $dir.Parent
        }

        if ($gitDir) {
            if (Test-Path -LiteralPath $gitDir -PathType Container) {
                $projectName = (Get-Item -Force -LiteralPath $gitDir).Parent.Name
            $worktreeName = "main"
        } else {
            # C'est un fichier worktree
            $worktreeName = (Get-Item -Force -LiteralPath $gitDir).Parent.Name
            try {
                $content = Get-Content -Path $gitDir -Raw -ErrorAction SilentlyContinue
                if ($content -match "gitdir:\s*(.*)\.git/worktrees/") {
                    $projectName = (Get-Item -Force -LiteralPath $Matches[1]).Name
                } else {
                    $projectName = $worktreeName
                }
            } catch {
                $projectName = $worktreeName
            }
        }
        } else {
            # 2. Fallback: on prend le nom du dossier courant
            $projectName = (Get-Item -Force .).Name
            $worktreeName = "main"
        }
    }

    # Nettoyer les noms pour être valides
    $projectName = $projectName -replace '[\\/:*?"<>|]', '_'
    $worktreeName = $worktreeName -replace '[\\/:*?"<>|]', '_'
    
    # Exclure les répertoires système et personnels courants du mécanisme de secours
    $systemDirs = @("Documents", "Desktop", "Downloads", "OneDrive", "System32", "Users", "Windows", "Temp", "AppData", "Local", "trb_m", "home")
    if ($env:USERNAME) { $systemDirs += $env:USERNAME }
    if ($systemDirs -contains $projectName) {
        $projectName = "devcore"
    }
    
    # Mettre en cache
    $env:DEVCORE_ACTIVE_PROJECT_PWD = $currentPwd
    $env:DEVCORE_ACTIVE_PROJECT_NAME = $projectName
    $env:DEVCORE_ACTIVE_WORKTREE_NAME = $worktreeName

    # Enregistrer dans un fichier persistant pour les daemons Python
    $devCoreLocal = if ($env:DEVCORE_LOCAL_ROOT) { $env:DEVCORE_LOCAL_ROOT } elseif ($env:LOCALAPPDATA) { "$env:LOCALAPPDATA\DEV_CORE_LOCAL" } else { Join-Path (Split-Path -Parent $PSScriptRoot) "DEV_CORE_DATA" }
    $runtimeDir = "$devCoreLocal\Runtime"
    if (-not (Test-Path $runtimeDir)) {
        New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null
    }
    # Valider le projet par rapport à projects.json
    $isValid = $false
    $configPath = if ($env:DEVCORE_CONFIG_ROOT) { Join-Path $env:DEVCORE_CONFIG_ROOT "projects.json" } else { Join-Path (Split-Path -Parent $PSScriptRoot) "Config\projects.json" }
    if (Test-Path $configPath) {
        try {
            $projectsJson = Get-Content -Raw -Path $configPath -ErrorAction SilentlyContinue | ConvertFrom-Json
            $validNames = $projectsJson.projects.name
            if ($validNames -contains $projectName) {
                $isValid = $true
            }
        } catch {}
    }
    
    # Si le projet détecté est invalide (comme 'app' dans le sandbox), restaurer la valeur précédente si elle est valide
    $activeTxtPath = "$runtimeDir\active_project.txt"
    if (-not $isValid -and (Test-Path $activeTxtPath)) {
        $prevValue = (Get-Content -Path $activeTxtPath -ErrorAction SilentlyContinue).Trim()
        # strip BOM if any
        $prevValue = $prevValue -replace '^\xEF\xBB\xBF'
        if ($validNames -contains $prevValue) {
            $projectName = $prevValue
            $isValid = $true
        }
    }
    
    # Fallback ultime si toujours invalide
    if (-not $isValid) {
        $projectName = "devcore"
    }

    Set-Content -Path "$runtimeDir\active_project.txt" -Value $projectName -Encoding UTF8 -ErrorAction SilentlyContinue

    # Retourner uniquement le nom canonique
    Write-Output $projectName
} catch {
    # Par sécurité, utiliser 'devcore' en cas d'erreur inattendue
    Write-Output "devcore"
}
