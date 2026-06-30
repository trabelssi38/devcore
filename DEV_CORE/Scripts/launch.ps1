# launch.ps1 -- DEV_CORE v7.3
param(
    [string]$Client = "auto",
    [string]$Project = "",
    [switch]$QuickStart
)

$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { "C:\devcore\DEV_CORE_DATA" }
$TODAY         = Get-Date -Format "yyyy-MM-dd"
$LOG           = "$DEV_CORE_DATA\Logs\scripts\launch_$TODAY.log"

function Log { param($msg,$color="Gray"); $l="[$(Get-Date -f HH:mm:ss)] $msg"; Add-Content $LOG $l -ErrorAction SilentlyContinue; Write-Host "  $l" -ForegroundColor $color }

Write-Host ""
Write-Host "  DEV_CORE v7.3 - LAUNCH" -ForegroundColor Cyan
Write-Host "  =======================================" -ForegroundColor DarkGray

# 1. Adapter le client
Log "1/8 Adaptation client ($Client)" "Cyan"
& "$DEV_CORE\Scripts\adapt_client.ps1" -Client $Client

# 2. Services check & launch (Qdrant, 9Router)
Log "2/8 Verification des services (Qdrant, 9Router)" "Cyan"

function Check-Port {
    param([int]$Port)
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $result = $tcp.BeginConnect("127.0.0.1", $Port, $null, $null)
        $success = $result.AsyncWaitHandle.WaitOne(200, $true)
        if ($success) { $tcp.EndConnect($result) }
        $tcp.Close()
        return $success
    } catch {
        return $false
    }
}

# 2.1 Qdrant / Docker
if (-not (Check-Port 6333)) {
    Log "  Qdrant (Port 6333) est hors-ligne. Tentative de demarrage..." "Yellow"
    $dockerInfo = docker info 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $dockerInfo) {
        Log "  [WARN] Docker Desktop ne semble pas etre demarre. Veuillez le lancer." "Yellow"
    } else {
        $qdrantContainers = docker ps -a --filter "ancestor=qdrant/qdrant" --format "{{.ID}} {{.Names}} {{.Status}}"
        if ($qdrantContainers) {
            $cId = ($qdrantContainers | Select-Object -First 1).Split(" ")[0]
            $cName = ($qdrantContainers | Select-Object -First 1).Split(" ")[1]
            Log "  Conteneur Qdrant existant trouve : $cName ($cId). Demarrage..." "Gray"
            docker start $cId | Out-Null
            Start-Sleep -Seconds 3
        } else {
            Log "  Aucun conteneur Qdrant trouve. Lancement d'un nouveau conteneur..." "Gray"
            docker run -d -p 6333:6333 -v C:/devcore/DEV_CORE_DATA/qdrant_storage:/qdrant/storage qdrant/qdrant | Out-Null
            Start-Sleep -Seconds 5
        }
    }
}

if (Check-Port 6333) {
    try {
        $q = Invoke-RestMethod "http://localhost:6333/collections" -TimeoutSec 3
        Log "  Qdrant OK - $($q.result.collections.Count) collections" "Green"
    } catch {
        Log "  Qdrant disponible mais erreur lors du chargement des collections" "Yellow"
    }
} else {
    Log "  Qdrant non disponible" "Red"
}

# 2.2 9Router (Port 20128) - Fallback
if (-not (Check-Port 20128)) {
    Log "  9Router (Port 20128) est hors-ligne. Tentative de demarrage..." "Yellow"
    if (Test-Path "C:\src\9router") {
        Log "  Demarrage de 9Router..." "Gray"
        Start-Process -FilePath "npm" -ArgumentList "run dev" -WorkingDirectory "C:\src\9router" -WindowStyle Hidden -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 5
        if (Check-Port 20128) {
            Log "  9Router lance avec succes sur le port 20128" "Green"
        } else {
            Log "  [WARN] 9Router lance mais le port 20128 reste ferme." "Yellow"
        }
    } else {
        Log "  [WARN] Dossier C:\src\9router introuvable." "Yellow"
    }
} else {
    Log "  9Router OK (Port 20128 actif)" "Green"
}

# 2.2.5 Gemini Router (Port 20129) - Primary
if (-not (Check-Port 20129)) {
    Log "  Gemini Router (Port 20129) est hors-ligne. Tentative de demarrage..." "Yellow"
    if (Test-Path "$DEV_CORE\Scripts\gemini_router.py") {
        Log "  Demarrage de Gemini Router..." "Gray"
        $logOut = "$DEV_CORE_DATA\Logs\scripts\gemini_router.log"
        $logErr = "$DEV_CORE_DATA\Logs\scripts\gemini_router_err.log"
        Start-Process -FilePath "python" -ArgumentList "$DEV_CORE\Scripts\gemini_router.py" -WorkingDirectory "C:\devcore" -WindowStyle Hidden -RedirectStandardOutput $logOut -RedirectStandardError $logErr -ErrorAction SilentlyContinue
        
        # Attendre que le port s'ouvre (timeout 10s)
        $routerOpen = $false
        for ($i = 0; $i -lt 20; $i++) {
            Start-Sleep -Milliseconds 500
            if (Check-Port 20129) {
                $routerOpen = $true
                break
            }
        }
        
        if ($routerOpen) {
            Log "  Gemini Router lance avec succes sur le port 20129" "Green"
        } else {
            Log "  [WARN] Gemini Router lance mais le port 20129 reste ferme." "Yellow"
        }
    } else {
        Log "  [WARN] Script gemini_router.py introuvable." "Yellow"
    }
} else {
    Log "  Gemini Router OK (Port 20129 actif)" "Green"
}

# 2.3 Headroom Proxy
if (-not (Check-Port 8787)) {
    Log "  Headroom Proxy (Port 8787) est hors-ligne. Tentative de demarrage..." "Yellow"
    & "$DEV_CORE\Scripts\headroom_start.ps1"
    if (Check-Port 8787) {
        Log "  Headroom Proxy lance avec succes" "Green"
    } else {
        Log "  [WARN] Impossible de lancer Headroom Proxy. Fallback direct sur 9Router." "Yellow"
    }
} else {
    Log "  Headroom Proxy OK (Port 8787 actif)" "Green"
}

# 3. Memory
Log "3/8 Memoire" "Cyan"
$memPath = "$DEV_CORE_DATA\Memory\MEMORY.md"
if (Test-Path $memPath) { Log "  MEMORY.md OK - $((Get-Content $memPath).Count) lignes" "Green" }
else { Log "  MEMORY.md absent - sera cree a endday" "Yellow" }

# 4. Tasks
Log "4/8 Tasks" "Cyan"
$tFile = "$DEV_CORE_DATA\Memory\$(& "$PSScriptRoot\Get-ActiveProject.ps1")\tasks.json"
if (Test-Path $tFile) {
    $b = Get-Content $tFile -Raw | ConvertFrom-Json
    $active = $b.tasks | Where-Object { $_.status -eq "active" }
    $todo   = $b.tasks | Where-Object { $_.status -eq "todo" }
    Log "  Board: $($b.project) | Active: $($active.Count) | Todo: $($todo.Count)" "Green"
    if ($active) { Log "  Task active : $($active[0].id) - $($active[0].title) [$($active[0].mode)]" "Cyan" }
} else { Log "  Pas de tasks.json - dc new task 'titre' -mode pour commencer" "Yellow" }

# 5. Task Detection (git scanner)
Log "5/8 Task detection" "Cyan"
if (-not $QuickStart) {
    & "$DEV_CORE\Scripts\Auto\task_git_scanner.ps1" 2>$null
}

# 6. Daily Note
Log "6/8 Daily Note" "Cyan"
if (-not $QuickStart) {
    $notePath = "$DEV_CORE_DATA\Vault\Daily Notes\$TODAY.md"
    if (-not (Test-Path $notePath)) {
        New-Item -ItemType Directory -Path (Split-Path $notePath) -Force | Out-Null
@"
---
title: Daily Note $TODAY
date: $TODAY
tags: [daily, devcore]
---

# $TODAY

## Resume
<!-- Auto-complete par endday -->

## Taches accomplies

## Decisions

## Lecons

## Metriques tokens
<!-- Auto-complete par endday -->

## Next actions
- [ ]
"@ | Set-Content $notePath -Encoding UTF8
        Log "  Daily Note creee" "Green"
    } else { Log "  Daily Note existante" "Gray" }
}

# 7. Skills registry
Log "7/8 Skills" "Cyan"
$regPath = "$DEV_CORE\Skills\skills_registry.json"
if (Test-Path $regPath) {
    $reg = Get-Content $regPath | ConvertFrom-Json
    Log "  $($reg.skills.Count) skills disponibles" "Green"
}

# 8. Token report veille
Log "8/8 Rapport token" "Cyan"
$yesterday = (Get-Date).AddDays(-1).ToString("yyyy-MM-dd")
$rpt = "$DEV_CORE_DATA\Logs\token_reports\$yesterday-report.html"
if (Test-Path $rpt) { Log "  Rapport veille disponible : $rpt" "Green" }
else { Log "  Pas de rapport pour $yesterday" "Gray" }

$activeClient = Get-Content "$DEV_CORE\Config\active_client.txt" -ErrorAction SilentlyContinue
Write-Host ""
Write-Host "  ========================================" -ForegroundColor Green
Write-Host "  ||  DEV_CORE v7.3 - PRET               ||" -ForegroundColor Green
Write-Host "  ========================================" -ForegroundColor Green
Write-Host "  ||  Client : $($activeClient.PadRight(29))||" -ForegroundColor White
Write-Host "  ||  Date   : $($TODAY.PadRight(29))||" -ForegroundColor White
if ($Project) { Write-Host "  ||  Projet : $($Project.PadRight(29))||" -ForegroundColor White }
Write-Host "  ||  dc help pour la liste des commandes  ||" -ForegroundColor Gray
Write-Host "  ========================================" -ForegroundColor Green
Write-Host ""


