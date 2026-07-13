# launch.ps1 -- DEV_CORE platform launcher
param(
    [string]$Client = "auto",
    [string]$Project = "",
    [switch]$QuickStart
)

$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { "C:\devcore\DEV_CORE_DATA" }
$TODAY         = Get-Date -Format "yyyy-MM-dd"
$LOG           = "$DEV_CORE_DATA\Logs\scripts\launch_$TODAY.log"
$LAUNCH_STARTED = Get-Date
$METRICS_SERVICE = "$DEV_CORE\Scripts\metrics_service.ps1"
. "$PSScriptRoot\platform_version.ps1"
$PLATFORM = Get-DevCorePlatformInfo
$PLATFORM_TITLE = $PLATFORM.title

function Log { param($msg,$color="Gray"); $l="[$(Get-Date -f HH:mm:ss)] $msg"; Add-Content $LOG $l -ErrorAction SilentlyContinue; Write-Host "  $l" -ForegroundColor $color }
function Record-Metric { param([string]$MetricType,[double]$Value,[string]$Unit="count",[hashtable]$Payload=@{})
    if (-not (Test-Path $METRICS_SERVICE)) { return }
    try {
        $payloadJson = $Payload | ConvertTo-Json -Depth 8 -Compress
        & $METRICS_SERVICE -Action Record -Source "launch" -Project "devcore" -MetricType $MetricType -Value $Value -Unit $Unit -PayloadJson $payloadJson 6>$null | Out-Null
    } catch {}
}

Write-Host ""
Write-Host "  $PLATFORM_TITLE - LAUNCH" -ForegroundColor Cyan
Write-Host "  =======================================" -ForegroundColor DarkGray

# 1. Adapter le client
Log "1/8 Adaptation client ($Client)" "Cyan"
& "$DEV_CORE\Scripts\adapt_client.ps1" -Client $Client
& "$DEV_CORE\Scripts\ensure_repowise_mcp.ps1" -RepoRoot "C:\devcore"
& "$DEV_CORE\Scripts\ensure_repowise_web_languages.ps1"
& "$DEV_CORE\Scripts\ensure_repowise_web_proxy.ps1"
& "$DEV_CORE\Scripts\ensure_repowise_watch.ps1" -RepoRoot "C:\devcore"

# 2. Services check & launch (Qdrant, Gemini Router)
Log "2/8 Verification des services (Qdrant, Gemini Router)" "Cyan"

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
    $dockerOk = ($LASTEXITCODE -eq 0 -and $dockerInfo)
    
    if (-not $dockerOk) {
        Log "  Docker Desktop ne semble pas etre demarre. Tentative de lancement..." "Yellow"
        $dockerPath = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
        if (Test-Path $dockerPath) {
            Start-Process -FilePath $dockerPath -ErrorAction SilentlyContinue
            Log "  Docker Desktop lance. Attente du demarrage (max 60s)..." "Gray"
            for ($attempt = 1; $attempt -le 30; $attempt++) {
                Start-Sleep -Seconds 2
                $dockerInfo = docker info 2>$null
                if ($LASTEXITCODE -eq 0 -and $dockerInfo) {
                    $dockerOk = $true
                    Log "  Docker Desktop demarre avec succes." "Green"
                    break
                }
            }
        } else {
            Log "  [WARN] Impossible de trouver l'executable Docker Desktop a l'emplacement par defaut." "Yellow"
        }
    }
    
    if ($dockerOk) {
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
    } else {
        Log "  [ERROR] Docker Desktop n'est pas actif. Impossible de demarrer Qdrant." "Red"
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


# 2.2.5 Gemini Router (Port 20130) - Primary
if (-not (Check-Port 20130)) {
    Log "  Gemini Router (Port 20130) est hors-ligne. Tentative de demarrage..." "Yellow"
    if (Test-Path "$DEV_CORE\Scripts\gemini_router.py") {
        $maxStartAttempts = 2
        $routerOpen = $false
        for ($attempt = 1; $attempt -le $maxStartAttempts; $attempt++) {
            Log "  Demarrage de Gemini Router (tentative $attempt/$maxStartAttempts)..." "Gray"
            $logOut = "$DEV_CORE_DATA\Logs\scripts\gemini_router.log"
            $logErr = "$DEV_CORE_DATA\Logs\scripts\gemini_router_err.log"
            
            $proc = Start-Process -FilePath "python" -ArgumentList "$DEV_CORE\Scripts\gemini_router.py" -WorkingDirectory "C:\devcore" -WindowStyle Hidden -RedirectStandardOutput $logOut -RedirectStandardError $logErr -PassThru -ErrorAction SilentlyContinue
            
            # Attendre que le port s'ouvre (timeout 10s)
            for ($i = 0; $i -lt 20; $i++) {
                Start-Sleep -Milliseconds 500
                if (Check-Port 20130) {
                    $routerOpen = $true
                    break
                }
            }
            
            if ($routerOpen) {
                Log "  Gemini Router lance avec succes sur le port 20130" "Green"
                break
            } else {
                Log "  [WARN] Gemini Router n'a pas repondu sur le port 20130 apres 10s. Fermeture du processus orphelin..." "Yellow"
                try {
                    if ($proc -and -not $proc.HasExited) {
                        $proc.Kill()
                        Start-Sleep -Seconds 1
                    }
                } catch {
                    Log "  [WARN] Erreur lors de l'arret du processus orphelin: $_" "Yellow"
                }
            }
        }
        if (-not $routerOpen) {
            Log "  [ERROR] Impossible de demarrer Gemini Router apres $maxStartAttempts tentatives." "Red"
        }
    } else {
        Log "  [WARN] Script gemini_router.py introuvable." "Yellow"
    }
} else {
    Log "  Gemini Router OK (Port 20130 actif)" "Green"
}

# 2.2.6 Dashboard API Server (Port 20129)
if (-not (Check-Port 20129)) {
    Log "  Dashboard API Server (Port 20129) est hors-ligne. Tentative de demarrage..." "Yellow"
    if (Test-Path "$DEV_CORE\Scripts\dashboard_api.py") {
        $maxStartAttempts = 2
        $apiOpen = $false
        for ($attempt = 1; $attempt -le $maxStartAttempts; $attempt++) {
            Log "  Demarrage de Dashboard API Server (tentative $attempt/$maxStartAttempts)..." "Gray"
            $logOut = "$DEV_CORE_DATA\Logs\scripts\dashboard_api.log"
            $logErr = "$DEV_CORE_DATA\Logs\scripts\dashboard_api_err.log"
            
            $proc = Start-Process -FilePath "python" -ArgumentList "$DEV_CORE\Scripts\dashboard_api.py" -WorkingDirectory "C:\devcore" -WindowStyle Hidden -RedirectStandardOutput $logOut -RedirectStandardError $logErr -PassThru -ErrorAction SilentlyContinue
            
            # Attendre que le port s'ouvre (timeout 10s)
            for ($i = 0; $i -lt 20; $i++) {
                Start-Sleep -Milliseconds 500
                if (Check-Port 20129) {
                    $apiOpen = $true
                    break
                }
            }
            
            if ($apiOpen) {
                Log "  Dashboard API Server lance avec succes sur le port 20129" "Green"
                break
            } else {
                Log "  [WARN] Dashboard API Server n'a pas repondu sur le port 20129 apres 10s. Fermeture du processus orphelin..." "Yellow"
                try {
                    if ($proc -and -not $proc.HasExited) {
                        $proc.Kill()
                        Start-Sleep -Seconds 1
                    }
                } catch {
                    Log "  [WARN] Erreur lors de l'arret du processus orphelin: $_" "Yellow"
                }
            }
        }
        if (-not $apiOpen) {
            Log "  [ERROR] Impossible de demarrer Dashboard API Server apres $maxStartAttempts tentatives." "Red"
        }
    } else {
        Log "  [WARN] Script dashboard_api.py introuvable." "Yellow"
    }
} else {
    Log "  Dashboard API Server OK (Port 20129 actif)" "Green"
}

# 2.3 Headroom Proxy
if (-not (Check-Port 8787)) {
    Log "  Headroom Proxy (Port 8787) est hors-ligne. Tentative de demarrage..." "Yellow"
    & "$DEV_CORE\Scripts\headroom_start.ps1"
    if (Check-Port 8787) {
        Log "  Headroom Proxy lance avec succes" "Green"
    } else {
        Log "  [WARN] Impossible de lancer Headroom Proxy. Fallback direct sur Gemini Router." "Yellow"
    }
} else {
    Log "  Headroom Proxy OK (Port 8787 actif)" "Green"
}

# 2.4 Repowise Server (Port 7337)
if (-not (Check-Port 7337)) {
    Log "  Repowise Server (Port 7337) est hors-ligne. Tentative de demarrage..." "Yellow"
    $repowisePath = "C:\Users\trb_m\AppData\Roaming\Python\Python313\Scripts\repowise.exe"
    if (-not (Test-Path $repowisePath)) { $repowisePath = "repowise" }
    
    $logOut = "$DEV_CORE_DATA\Logs\scripts\repowise.log"
    $logErr = "$DEV_CORE_DATA\Logs\scripts\repowise_err.log"
    
    # Set mock embedder env var to bypass prompting on serve
    $env:REPOWISE_EMBEDDER = "mock"
    & "$DEV_CORE\Scripts\ensure_repowise_web_proxy.ps1"
    
    $proc = Start-Process -FilePath $repowisePath -ArgumentList "serve --host 127.0.0.1 --port 7337 --ui-port 3101" -WorkingDirectory "C:\devcore" -WindowStyle Hidden -RedirectStandardOutput $logOut -RedirectStandardError $logErr -PassThru -ErrorAction SilentlyContinue
    
    # Attendre que le port s'ouvre (timeout 15s)
    $repowiseOpen = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Milliseconds 500
        if (Check-Port 7337) {
            $repowiseOpen = $true
            break
        }
    }
    
    if ($repowiseOpen) {
        & "$DEV_CORE\Scripts\ensure_repowise_web_proxy.ps1"
        Log "  Repowise Server lance avec succes (API: 7337, UI: 3101)" "Green"
    } else {
        Log "  [WARN] Repowise Server n'a pas repondu sur le port 7337 apres 15s." "Yellow"
    }
} else {
    Log "  Repowise Server OK (Port 7337 actif)" "Green"
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

$activeClient = Get-Content "$DEV_CORE_DATA\Runtime\active_client.txt" -ErrorAction SilentlyContinue
if (-not $activeClient) {
    $activeClient = Get-Content "$DEV_CORE\Config\active_client.txt" -ErrorAction SilentlyContinue
}
if (-not $activeClient) { $activeClient = "unknown" }
Write-Host ""
Write-Host "  ========================================" -ForegroundColor Green
Write-Host ("  ||  {0} - PRET{1}||" -f $PLATFORM_TITLE, (" " * [Math]::Max(1, 26 - ($PLATFORM_TITLE.Length)))) -ForegroundColor Green
Write-Host "  ========================================" -ForegroundColor Green
Write-Host "  ||  Client : $($activeClient.PadRight(29))||" -ForegroundColor White
Write-Host "  ||  Date   : $($TODAY.PadRight(29))||" -ForegroundColor White
if ($Project) { Write-Host "  ||  Projet : $($Project.PadRight(29))||" -ForegroundColor White }
Write-Host "  ||  dc help pour la liste des commandes  ||" -ForegroundColor Gray
Write-Host "  ========================================" -ForegroundColor Green
Write-Host ""

$launchElapsed = ((Get-Date) - $LAUNCH_STARTED).TotalSeconds
Record-Metric -MetricType "duration" -Value $launchElapsed -Unit "seconds" -Payload @{ status = "success"; component = "launch" }
Record-Metric -MetricType "success" -Value 1 -Unit "count" -Payload @{ component = "launch" }
