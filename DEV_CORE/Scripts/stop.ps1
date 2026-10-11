# stop.ps1 -- DEV_CORE v10.0 Platform Shutdown Script
# Cooperative scheduler shutdown precedes session/network shutdown.
param(
    [switch]$SchedulerOnly,
    [ValidateRange(1,30)][int]$WaitSeconds = 30
)

$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT -and (Test-Path (Join-Path $env:DEVCORE_PLATFORM_ROOT "Scripts\platform_version.ps1"))) {
    $env:DEVCORE_PLATFORM_ROOT
} elseif (Test-Path (Join-Path $PSScriptRoot "platform_version.ps1")) {
    Split-Path -Parent $PSScriptRoot
} elseif (Test-Path (Join-Path $PSScriptRoot "Scripts\platform_version.ps1")) {
    $PSScriptRoot
} elseif (Test-Path (Join-Path (Split-Path -Parent $PSScriptRoot) "DEV_CORE\Scripts\platform_version.ps1")) {
    Join-Path (Split-Path -Parent $PSScriptRoot) "DEV_CORE"
} else {
    Split-Path -Parent $PSScriptRoot
}
if ($DEV_CORE -match '[/\\]Scripts[/\\]?$') {
    $DEV_CORE = Split-Path -Parent $DEV_CORE
}
if (-not $env:PYTHONPATH -or $env:PYTHONPATH -notlike "*$DEV_CORE*") {
    $env:PYTHONPATH = if ($env:PYTHONPATH) { "$DEV_CORE;$env:PYTHONPATH" } else { $DEV_CORE }
}
. "$DEV_CORE\Scripts\platform_version.ps1"

$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { (Join-Path $DEV_CORE "DEV_CORE_DATA") }
$PLATFORM = Get-DevCorePlatformInfo

Write-Host ""
Write-Host "  $($PLATFORM.title) -- SHUTDOWN ALL SYSTEMS" -ForegroundColor Yellow
Write-Host "  ========================================" -ForegroundColor DarkGray
Write-Host ""

# Explicit local profile is required for scheduler control; no name-based kill.
$pythonExe = Get-DevCorePython
if (-not $env:DEVCORE_LOCAL_ROOT -or -not $env:DEVCORE_DATA_ROOT) {
    Write-Error "DEVCORE_LOCAL_ROOT et DEVCORE_DATA_ROOT explicites requis pour un arret verifie."
    exit 1
}
Write-Host "Arret cooperatif du scheduler et suspension des relances..." -ForegroundColor White
if (-not $SchedulerOnly) {
    $serviceControl = Join-Path $DEV_CORE 'Scheduler/service_control.py'
    $pauseText = & $pythonExe -I $serviceControl --local-root $env:DEVCORE_LOCAL_ROOT --data-root $env:DEVCORE_DATA_ROOT --platform-root $DEV_CORE --action pause
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Pause globale refusee : un lancement peut etre en cours. Services conserves."
        exit 1
    }
    try { $pauseResult = $pauseText | ConvertFrom-Json -ErrorAction Stop } catch { exit 1 }
    if ($pauseResult.status -ne 'services_paused') { exit 1 }
}
$control = Join-Path $DEV_CORE 'Scheduler/stop_scheduler.py'
$resultText = & $pythonExe -I $control --local-root $env:DEVCORE_LOCAL_ROOT --data-root $env:DEVCORE_DATA_ROOT --platform-root $DEV_CORE --pause --wait-seconds $WaitSeconds
$controlExit = $LASTEXITCODE
if ($controlExit -ne 0) {
    Write-Warning "Arret non confirme : autres services conserves. Une demande acceptee peut rester en attente."
    exit $controlExit
}
try { $result = $resultText | ConvertFrom-Json -ErrorAction Stop } catch { exit 1 }
if (-not $result.shutdown_completed) { exit 2 }
Write-Host "Cycle scheduler termine, guard libere ; relances suspendues." -ForegroundColor Green
if ($SchedulerOnly) { exit 0 }

# End session only after the scheduler completed its shutdown protocol.
& $pythonExe -m devcore_engine.cli session end --project "devcore"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# Registered local services only: cooperative request, never a port-based kill.
Write-Host "Fermeture cooperative des services enregistres..." -ForegroundColor White
$serviceStop = Join-Path $DEV_CORE 'Scripts/stop_service.py'
$incomplete = $false
foreach ($service in @('dashboard', 'router', 'headroom-native', 'headroom-auxiliary')) {
    $serviceText = & $pythonExe -I $serviceStop --local-root $env:DEVCORE_LOCAL_ROOT --data-root $env:DEVCORE_DATA_ROOT --platform-root $DEV_CORE --service $service --wait-seconds $WaitSeconds
    $serviceExit = $LASTEXITCODE
    if ($serviceExit -ne 0) {
        Write-Warning "Service '$service' : fermeture non confirmee ou en echec ; aucun arret force."
        $incomplete = $true
        continue
    }
    try { $serviceResult = $serviceText | ConvertFrom-Json -ErrorAction Stop } catch { $incomplete = $true; continue }
    if (-not $serviceResult.shutdown_completed) { $incomplete = $true; continue }
    Write-Host "Service '$service' : protocole de fermeture termine." -ForegroundColor Green
}
Write-Warning "RepoWise et ancien adaptateur 8788 : arret non qualifie, processus conserves."
Write-Host "Relances suspendues ; reprises globale et scheduler explicites requises."
if ($incomplete) { exit 1 }
