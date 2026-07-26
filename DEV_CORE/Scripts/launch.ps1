# launch.ps1 -- DEV_CORE platform launcher
param(
    [string]$Client = "auto",
    [string]$Project = "",
    [switch]$QuickStart
)

$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { $PSScriptRoot }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { (Join-Path (Split-Path -Parent $PSScriptRoot) "DEV_CORE_DATA") }
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
# & "$DEV_CORE\Scripts\ensure_repowise_web_proxy.ps1"
# & "$DEV_CORE\Scripts\ensure_repowise_ipv6_proxy.ps1"
# & "$DEV_CORE\Scripts\ensure_repowise_watch.ps1" -RepoRoot "C:\devcore"

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

function Get-DockerDesktopPath {
    $candidates = @(
        "C:\Program Files\Docker\Docker\Docker Desktop.exe",
        "$env:LOCALAPPDATA\Programs\DockerDesktop\Docker Desktop.exe",
        "$env:LOCALAPPDATA\Docker\Docker Desktop.exe"
    )

    $dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
    if ($dockerCmd -and $dockerCmd.Source) {
        $dockerRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $dockerCmd.Source))
        $candidates += (Join-Path $dockerRoot "Docker Desktop.exe")
        $candidates += (Join-Path $dockerRoot "frontend\Docker Desktop.exe")
        $candidates += (Join-Path $dockerRoot "resources\Docker desktop.exe")
    }

    foreach ($candidate in ($candidates | Where-Object { $_ } | Select-Object -Unique)) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }
    return $null
}

function Test-DockerReady {
    try {
        $dockerInfo = docker info 2>$null
        return ($LASTEXITCODE -eq 0 -and $dockerInfo)
    } catch {
        return $false
    }
}

function Wait-DockerReady {
    param([int]$TimeoutSeconds = 60)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-DockerReady) { return $true }
        Start-Sleep -Seconds 2
    }
    return (Test-DockerReady)
}

function Wait-QdrantReady {
    param([int]$TimeoutSeconds = 60)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $lastError = ""
    while ((Get-Date) -lt $deadline) {
        try {
            $q = Invoke-RestMethod "http://localhost:6333/collections" -TimeoutSec 5
            if ($q -and $q.status -eq "ok") { return $q }
        } catch {
            $lastError = $_.Exception.Message
        }
        Start-Sleep -Seconds 2
    }
    if ($lastError) {
        Log "  Qdrant readiness timeout: $lastError" "Yellow"
    }
    return $null
}

$REPO_ROOT     = Split-Path -Parent $DEV_CORE

# 2.1 Docker Compose up -d
Log "  Demarrage de la pile Docker Compose..." "Yellow"
$isContainer = (Test-Path "/.dockerenv") -or ($env:DEVCORE_PLATFORM_ROOT -eq "/app/DEV_CORE")
if ($isContainer) {
    Log "  Environnement conteneurise detecte -- pile Compose geree par l'hote." "Green"
    $dockerOk = $false
} else {
    $dockerOk = Test-DockerReady
    if (-not $dockerOk) {
        Log "  Docker Desktop ne semble pas etre demarre. Tentative de lancement..." "Yellow"
        $dockerPath = Get-DockerDesktopPath
        if ($dockerPath) {
            Start-Process -FilePath $dockerPath -WindowStyle Hidden -ErrorAction SilentlyContinue
            Log "  Docker Desktop lance. Attente du demarrage (max 120s)..." "Gray"
            if (Wait-DockerReady -TimeoutSeconds 120) {
                $dockerOk = $true
                Log "  Docker Desktop demarre avec succes." "Green"
            }
        } else {
            Log "  [WARN] Impossible de trouver l'executable Docker Desktop." "Yellow"
        }
    }
}

$composeFile = "$REPO_ROOT\docker-compose.yml"

if ($dockerOk) {
    Log "  Execution de docker compose up -d..." "Gray"
    if (Test-Path $composeFile) {
        docker compose -f $composeFile up -d
    } else {
        docker compose up -d
    }
    if ($LASTEXITCODE -ne 0) {
        Log "  [WARN] docker compose up -d a retourne un code d'erreur." "Yellow"
    }
} else {
    Log "  [ERROR] Docker Desktop non actif. Impossible de lancer la pile Compose." "Red"
}

function Check-Port {
    param([int]$Port, [string]$TargetHost = "127.0.0.1")
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $result = $tcp.BeginConnect($TargetHost, $Port, $null, $null)
        $success = $result.AsyncWaitHandle.WaitOne(200, $true)
        if ($success) { $tcp.EndConnect($result) }
        $tcp.Close()
        return $success
    } catch {
        return $false
    }
}

# Wait for container services
Log "  Verification de l'ouverture des ports de la pile Compose..." "Gray"
$ports = if ($isContainer) {
    @(
        @{ name = "PostgreSQL"; port = 5432; host = "postgres" }
        @{ name = "Qdrant"; port = 6333; host = "qdrant" }
        @{ name = "Gemini Router"; port = 20130; host = "gemini-router" }
        @{ name = "FastAPI API"; port = 20131; host = "api" }
    )
} else {
    @(
        @{ name = "PostgreSQL"; port = 5432; host = "127.0.0.1" }
        @{ name = "Qdrant"; port = 6333; host = "127.0.0.1" }
        @{ name = "Gemini Router"; port = 20130; host = "127.0.0.1" }
        @{ name = "FastAPI API"; port = 20131; host = "127.0.0.1" }
    )
}

foreach ($p in $ports) {
    $portOpen = $false
    for ($i = 0; $i -lt 10; $i++) {
        if (Check-Port -Port $p.port -TargetHost $p.host) {
            $portOpen = $true
            break
        }
        Start-Sleep -Seconds 1
    }
    if ($portOpen) {
        Log "  Service $($p.name) OK (Port $($p.port) actif)" "Green"
    } else {
        Log "  [WARN] Le service $($p.name) n'a pas repondu sur le port $($p.port) apres 10s." "Yellow"
    }
}

# Run DB Migrations
if ($dockerOk) {
    Log "  Execution des migrations de la base de donnees..." "Gray"
    if (Test-Path $composeFile) {
        docker compose -f $composeFile exec -w /app/DEV_CORE/Database api alembic upgrade head
    } else {
        docker compose exec -w /app/DEV_CORE/Database api alembic upgrade head
    }
    if ($LASTEXITCODE -eq 0) {
        Log "  Migrations Alembic completees avec succes" "Green"
    } else {
        Log "  [WARN] Erreur lors de l'execution des migrations Alembic dans le conteneur." "Yellow"
    }
}


# 2.3 Headroom Proxy
$headroomHost = if ($isContainer) { "host.docker.internal" } else { "127.0.0.1" }
if (-not (Check-Port -Port 8787 -TargetHost $headroomHost)) {
    if (-not $isContainer) {
        Log "  Headroom Proxy (Port 8787) est hors-ligne. Tentative de demarrage..." "Yellow"
        & "$DEV_CORE\Scripts\headroom_start.ps1"
    }
    if (Check-Port -Port 8787 -TargetHost $headroomHost) {
        Log "  Headroom Proxy lance avec succes" "Green"
    } else {
        Log "  [WARN] Headroom Proxy hors-ligne sur $headroomHost. Fallback direct sur Gemini Router." "Yellow"
    }
} else {
    Log "  Headroom Proxy OK (Port 8787 actif)" "Green"
}

# 2.3.5 Anthropic Adapter (Port 8788)
if (-not (Check-Port 8788)) {
    Log "  Anthropic Adapter (Port 8788) est hors-ligne. Tentative de demarrage..." "Yellow"
    $adapterLog = "$DEV_CORE_DATA\Logs\scripts\anthropic_adapter.log"
    $adapterErr = "$DEV_CORE_DATA\Logs\scripts\anthropic_adapter_err.log"
    $spParams = @{
        FilePath = "python"
        ArgumentList = "$DEV_CORE/Scripts/anthropic_adapter.py"
        WorkingDirectory = $REPO_ROOT
        RedirectStandardOutput = $adapterLog
        RedirectStandardError = $adapterErr
        PassThru = $true
        ErrorAction = "SilentlyContinue"
    }
    if ($IsWindows) { $spParams["WindowStyle"] = "Hidden" }
    $proc = Start-Process @spParams
    
    $adapterOpen = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Milliseconds 500
        if (Check-Port 8788) {
            $adapterOpen = $true
            break
        }
    }
    if ($adapterOpen) {
        Log "  Anthropic Adapter lance avec succes sur port 8788" "Green"
    } else {
        Log "  [WARN] Anthropic Adapter n'a pas repondu sur le port 8788 apres 15s." "Yellow"
    }
} else {
    Log "  Anthropic Adapter OK (Port 8788 actif)" "Green"
}

# 2.4 Repowise Server (Port 7337) - Skipped (using lightweight MCP mode)
Log "  Repowise Server: Skipped serve daemon startup (using lightweight stdio MCP mode)" "Green"

# 2.5 Agent environment variables configuration
Log "  Configuration des variables d'environnement des agents (Scope User)..." "Gray"
& "$DEV_CORE\Scripts\init_agent_env.ps1" -Scope User


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
