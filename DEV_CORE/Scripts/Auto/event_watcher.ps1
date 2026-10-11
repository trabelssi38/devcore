# Consomme les evenements locaux avec un projet explicite.
# Les anciens fichiers DEV_CORE_DATA/Bus ne sont pas une file transactionnelle.
$ErrorActionPreference = "Stop"
$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { Split-Path -Parent (Split-Path -Parent $PSScriptRoot) }
. (Join-Path $DEV_CORE "Scripts\platform_version.ps1")
$localRoot = if ($env:DEVCORE_LOCAL_ROOT) { $env:DEVCORE_LOCAL_ROOT } elseif ($env:LOCALAPPDATA) { Join-Path $env:LOCALAPPDATA "DEV_CORE_LOCAL" } else { Join-Path ([System.IO.Path]::GetTempPath()) "DEV_CORE_LOCAL" }
$busRoot = Join-Path $localRoot "Bus"
$eventsDir = Join-Path $busRoot "events"
$processingDir = Join-Path $busRoot "processing"
$processedDir = Join-Path $busRoot "processed"
$rejectedDir = Join-Path $busRoot "rejected"
$logDir = Join-Path $localRoot "Logs\scripts"
foreach ($dir in @($eventsDir, $processingDir, $processedDir, $rejectedDir, $logDir)) {
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
}
$logPath = Join-Path $logDir ("event_watcher_" + (Get-Date -Format "yyyy-MM-dd") + ".log")
function Log([string]$message) {
    Add-Content -LiteralPath $logPath -Value "[$(Get-Date -Format HH:mm:ss)] $message"
}
function Require-EventField($event, [string]$name) {
    $value = [string]$event.$name
    if ([string]::IsNullOrWhiteSpace($value)) { throw "INVALID: champ $name absent" }
    return $value.Trim()
}

$python = Get-DevCorePython
if (-not $env:PYTHONPATH -or $env:PYTHONPATH -notlike "*$DEV_CORE*") {
    $env:PYTHONPATH = if ($env:PYTHONPATH) { "$DEV_CORE;$env:PYTHONPATH" } else { $DEV_CORE }
}
$configRoot = if ($env:DEVCORE_CONFIG_ROOT) { $env:DEVCORE_CONFIG_ROOT } else { Join-Path $DEV_CORE "Config" }
$registryPath = Join-Path $configRoot "projects.json"

foreach ($file in @(Get-ChildItem -LiteralPath $eventsDir -Filter "*.json" -File | Sort-Object LastWriteTime)) {
    $claimed = Join-Path $processingDir $file.Name
    try {
        [System.IO.File]::Move($file.FullName, $claimed)
    } catch [System.IO.IOException] {
        # Une autre instance a pris ce fichier ou un ancien traitement attend une revue.
        continue
    }
    try {
        try {
            $event = Get-Content -LiteralPath $claimed -Raw -Encoding UTF8 | ConvertFrom-Json
        } catch {
            throw "INVALID: JSON illisible"
        }
        $project = Require-EventField $event "project"
        switch ((Require-EventField $event "type")) {
            "task_completed" {
                $taskId = Require-EventField $event "task_id"
                & $python -m devcore_engine.cli task complete $taskId --project $project | Out-Null
                if ($LASTEXITCODE -ne 0) { throw "Completion SQL echouee pour $project/$taskId" }
            }
            "post-commit" {
                if (-not (Test-Path -LiteralPath $registryPath)) { throw "Registre projets absent" }
                $registry = Get-Content -LiteralPath $registryPath -Raw -Encoding UTF8 | ConvertFrom-Json
                $matches = @($registry.projects | Where-Object { $_.name -eq $project })
                if ($matches.Count -ne 1 -or -not $matches[0].path) { throw "INVALID: projet non enregistre : $project" }
                & (Join-Path $DEV_CORE "Scripts\task_scan.ps1") -Project $project -RepoPath $matches[0].path | Out-Null
                if ($LASTEXITCODE -ne 0) { throw "Scan Git echoue pour $project" }
            }
            default {
                throw "INVALID: type d'evenement non pris en charge : $($event.type)"
            }
        }
        [System.IO.File]::Move($claimed, (Join-Path $processedDir $file.Name))
        Log "Traite : $($file.Name) [$project]"
    } catch {
        $message = [string]$_
        Log "Echec : $($file.Name) - $message"
        $destination = if ($message -like '*INVALID:*') { Join-Path $rejectedDir $file.Name } else { $file.FullName }
        if (-not (Test-Path -LiteralPath $destination)) {
            [System.IO.File]::Move($claimed, $destination)
        }
    }
}
