# obsidian_sync.ps1 -- DEV_CORE v9.0 Auto layer
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
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { (Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) "DEV_CORE_DATA") }
$DEV_CORE_LOCAL = if ($env:DEVCORE_LOCAL_ROOT) { $env:DEVCORE_LOCAL_ROOT } elseif ($env:LOCALAPPDATA) { "$env:LOCALAPPDATA\DEV_CORE_LOCAL" } else { $DEV_CORE_DATA }
$TODAY         = Get-Date -Format "yyyy-MM-dd"
$LOG           = "$DEV_CORE_DATA\Logs\scripts\obsidian_sync_$TODAY.log"
function Log { param($msg,$color="Gray"); $l="[$(Get-Date -f HH:mm:ss)] $msg"; Add-Content $LOG $l -ErrorAction SilentlyContinue; Write-Host "    $l" -ForegroundColor $color }
Log "obsidian_sync -- mise a jour Daily Note" "Cyan"
$notePath = "$DEV_CORE_DATA\Vault\Daily Notes\$TODAY.md"
if (-not (Test-Path $notePath)) { Log "Daily Note absente -- creee par launch.ps1" "Yellow"; exit 0 }
# Lire le contenu existant
$content = Get-Content $notePath -Raw
# Ajouter les metriques du jour si section vide
if ($content -match "<!-- Auto-complete par endday -->") {
    $activeClient = Get-Content "$DEV_CORE_DATA\Runtime\active_client.txt" -ErrorAction SilentlyContinue
    if (-not $activeClient) {
        $activeClient = Get-Content "$DEV_CORE\Config\active_client.txt" -ErrorAction SilentlyContinue
    }
    $metricsBlock = "Total : -- tokens | Cache : --% | Client : $activeClient"
    $content = $content -replace "<!-- Auto-complete par endday -->", $metricsBlock
    $content | Set-Content $notePath -Encoding UTF8
    Log "Daily Note mise a jour : $notePath" "Green"
} else { Log "Daily Note deja a jour" "Gray" }
