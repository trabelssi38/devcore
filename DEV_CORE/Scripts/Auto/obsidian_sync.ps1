# obsidian_sync.ps1 — DEV_CORE v6 Auto layer
$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { "C:\DEV_CORE_DATA" }
$TODAY         = Get-Date -Format "yyyy-MM-dd"
$LOG           = "$DEV_CORE_DATA\Logs\scripts\obsidian_sync_$TODAY.log"
function Log { param($msg,$color="Gray"); $l="[$(Get-Date -f HH:mm:ss)] $msg"; Add-Content $LOG $l -ErrorAction SilentlyContinue; Write-Host "    $l" -ForegroundColor $color }
Log "obsidian_sync — mise à jour Daily Note" "Cyan"
$notePath = "$DEV_CORE_DATA\Vault\Daily Notes\$TODAY.md"
if (-not (Test-Path $notePath)) { Log "Daily Note absente — créée par launch.ps1" "Yellow"; exit 0 }
# Lire le contenu existant
$content = Get-Content $notePath -Raw
# Ajouter les métriques du jour si section vide
if ($content -match "<!-- Auto-complété par endday -->") {
    $metricsBlock = "Total : — tokens | Cache : —% | Client : $((Get-Content "$DEV_CORE\Config\active_client.txt" -ErrorAction SilentlyContinue))"
    $content = $content -replace "<!-- Auto-complété par endday -->", $metricsBlock
    $content | Set-Content $notePath -Encoding UTF8
    Log "Daily Note mise à jour : $notePath" "Green"
} else { Log "Daily Note déjà à jour" "Gray" }
