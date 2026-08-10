# stop.ps1 -- DEV_CORE v10.0 Platform Shutdown Script
# Stops the active work session and terminates all background services cleanly.

$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { Split-Path -Parent $PSScriptRoot }
if ($DEV_CORE -match '\\Scripts\\?$') {
    $DEV_CORE = Split-Path -Parent $DEV_CORE
}
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { (Join-Path $DEV_CORE "DEV_CORE_DATA") }

. "$DEV_CORE\Scripts\platform_version.ps1"
$PLATFORM = Get-DevCorePlatformInfo

Write-Host ""
Write-Host "  $($PLATFORM.title) -- SHUTDOWN ALL SYSTEMS" -ForegroundColor Yellow
Write-Host "  ========================================" -ForegroundColor DarkGray
Write-Host ""

# 1. End the active session in DB
Write-Host "[1/3] Cloture de la session en base..." -ForegroundColor White
$pythonExe = if (Get-Command "python" -ErrorAction SilentlyContinue) { "python" } else { "C:\Program Files\Python313\python.exe" }
$env:PYTHONPATH = $DEV_CORE
& $pythonExe -m devcore_engine.cli session end --project "devcore"

# 2. Stop Hermes/Scheduler Daemon
Write-Host "[2/3] Arret du daemon Scheduler..." -ForegroundColor White
$schedProcs = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*scheduler_tick*" -or $_.CommandLine -like "*hermes_cron*"
}
if ($schedProcs) {
    foreach ($p in $schedProcs) {
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
        Write-Host "  Daemon Scheduler (PID: $($p.ProcessId)) arrete." -ForegroundColor Green
    }
} else {
    Write-Host "  Daemon Scheduler non actif." -ForegroundColor Gray
}

# 3. Terminate port-bound background services
Write-Host "[3/3] Fermeture des services reseaux..." -ForegroundColor White
$ports = @{
    20129 = "Dashboard API"
    20130 = "Gemini Router"
    8787  = "Headroom Proxy"
    8788  = "Anthropic Adapter"
    7337  = "Repowise Server"
}

foreach ($port in $ports.Keys) {
    $name = $ports[$port]
    $connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($connections) {
        $pids = $connections | Select-Object -ExpandProperty OwningProcess -Unique
        foreach ($owningPid in $pids) {
            Stop-Process -Id $owningPid -Force -ErrorAction SilentlyContinue
            Write-Host "  Service '$name' sur le port $port (PID: $owningPid) arrete." -ForegroundColor Green
        }
    } else {
        Write-Host "  Service '$name' sur le port $port non actif." -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "  Tous les systemes DEV_CORE ont ete arretes avec succes !" -ForegroundColor Green
Write-Host ""
