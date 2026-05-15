# memory_rotate.ps1 -- DEV_CORE v6 Auto layer
$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { "C:\devcore\DEV_CORE_DATA" }
$TODAY         = Get-Date -Format "yyyy-MM-dd"
$LOG           = "$DEV_CORE_DATA\Logs\scripts\memory_rotate_$TODAY.log"
function Log { param($msg,$color="Gray"); $l="[$(Get-Date -f HH:mm:ss)] $msg"; Add-Content $LOG $l -ErrorAction SilentlyContinue; Write-Host "    $l" -ForegroundColor $color }
Log "memory_rotate -- rotation MEMORY.md" "Cyan"
$memPath = "$DEV_CORE_DATA\Memory\MEMORY.md"
$archDir = "$DEV_CORE_DATA\Memory\archive"
New-Item -ItemType Directory -Path $archDir -Force | Out-Null
if (-not (Test-Path $memPath)) {
    # Creer MEMORY.md initial
    @"
# MEMORY.md -- DEV_CORE v6
<!-- Auto-genere par memory_rotate.ps1 -->
<!-- Score min inclusion : 0.5 | Max entrees : 50 -->

## Patterns confirmes

## Decisions actives

## Prompts efficaces
"@ | Set-Content $memPath -Encoding UTF8
    Log "MEMORY.md cree" "Green"; exit 0
}
$lines = (Get-Content $memPath).Count
Log "MEMORY.md -- $lines lignes" "Green"
# Si > 300 lignes, archiver et tronquer
if ($lines -gt 300) {
    Copy-Item $memPath "$archDir\MEMORY_$TODAY.md" -Force
    Log "Archive : $archDir\MEMORY_$TODAY.md" "Green"
    # Garder les 200 premieres lignes (top entries)
    Get-Content $memPath | Select-Object -First 200 | Set-Content $memPath -Encoding UTF8
    Log "MEMORY.md tronque a 200 lignes" "Cyan"
}
