# weekly_maintenance.ps1 - DEV_CORE v9.0 Auto layer
$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { "C:\devcore\DEV_CORE_DATA" }
$TODAY         = Get-Date -Format "yyyy-MM-dd"
$LOG           = "$DEV_CORE_DATA\Logs\scripts\weekly_maintenance_$TODAY.log"
function Log { param($msg,$color="Gray"); $l="[$(Get-Date -f HH:mm:ss)] $msg"; Add-Content $LOG $l -ErrorAction SilentlyContinue; Write-Host "    $l" -ForegroundColor $color }
Log "weekly_maintenance - audit complet" "Cyan"
$rptDir = "$DEV_CORE_DATA\Logs\token_reports"
New-Item -ItemType Directory -Path $rptDir -Force | Out-Null

# 1. Memory audit
Log "1/6 Memory audit" "Cyan"
$memPath = "$DEV_CORE_DATA\Memory\MEMORY.md"
if (Test-Path $memPath) { Log "  MEMORY.md : $((Get-Content $memPath).Count) lignes" "Green" }

# 2. Qdrant dedup check
Log "2/6 Qdrant check" "Cyan"
try { $q = Invoke-RestMethod "http://localhost:6333/collections" -TimeoutSec 3; Log "  Qdrant OK" "Green" }
catch { Log "  Qdrant non disponible" "Yellow" }

# 3. Skills prune
Log "3/6 Skills check" "Cyan"
$regPath = "$DEV_CORE\Skills\skills_registry.json"
$runtimePath = "$DEV_CORE_DATA\Skills\skills_runtime.json"
if (Test-Path $regPath) {
    $reg = Get-Content $regPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $cutoff = (Get-Date).AddDays(-30).ToString("yyyy-MM-dd")
    $runtime = $null
    if (Test-Path $runtimePath) {
        try { $runtime = Get-Content $runtimePath -Raw -Encoding UTF8 | ConvertFrom-Json } catch { $runtime = $null }
    }
    $stale = if ($runtime) {
        @($runtime.skills | Where-Object { $_.last_used -and $_.last_used -lt $cutoff })
    } else {
        @()
    }
    if ($stale.Count -gt 0) { Log "  $($stale.Count) skills non utilises depuis 30j : $($stale.id -join ', ')" "Yellow" }
    else { Log "  Tous les skills actifs" "Green" }
    if (-not $runtime) { Log "  Runtime skills absent : $runtimePath" "Gray" }
}

# 4. Cache flush
Log "4/6 Cache flush" "Cyan"
$cache = "$DEV_CORE\Cache"
if (Test-Path $cache) {
    $items = Get-ChildItem $cache -File | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) }
    $items | Remove-Item -Force -ErrorAction SilentlyContinue
    Log "  $($items.Count) fichiers supprimes du cache" "Green"
}

# 5. Rapport HTML
Log "5/6 Rapport hebdo" "Cyan"
$culture = [System.Globalization.CultureInfo]::InvariantCulture
$weekNum = $culture.Calendar.GetWeekOfYear((Get-Date), $culture.DateTimeFormat.CalendarWeekRule, $culture.DateTimeFormat.FirstDayOfWeek)
$week = "$(Get-Date -Format 'yyyy')-W$($weekNum.ToString('00'))"

$html = "<!DOCTYPE html><html><head><meta charset=`"utf-8`">"
$html += "<title>DEV_CORE Weekly $week</title>"
$html += "<style>body{font-family:system-ui;max-width:700px;margin:40px auto;color:#1e293b}h1{color:#6366f1;font-size:16px}</style>"
$html += "</head><body>"
$html += "<h1>DEV_CORE v9.0 - Weekly Report $week</h1>"
$html += "<p>Genere : $((Get-Date).ToString('yyyy-MM-dd HH:mm'))</p>"
$html += "<ul>"
$html += "<li>MEMORY.md : $((Get-Content $memPath -ErrorAction SilentlyContinue).Count) lignes</li>"
$html += "<li>Skills : $((Get-Content $regPath | ConvertFrom-Json -ErrorAction SilentlyContinue).skills.Count) actifs</li>"
$html += "</ul>"
$html += "<p style=`"color:#94a3b8;font-size:12px`">Auto-genere par weekly_maintenance.ps1</p>"
$html += "</body></html>"
$html | Set-Content "$rptDir\$week-weekly.html" -Encoding UTF8
Log "  Rapport : $rptDir\$week-weekly.html" "Green"

# 6. Backup vault
Log "6/6 Backup" "Cyan"
$bkp = "$DEV_CORE_DATA\Backups\auto\MEMORY_weekly_$TODAY.md"
if (Test-Path $memPath) { Copy-Item $memPath $bkp -Force; Log "  Backup MEMORY.md OK" "Green" }

Log "weekly_maintenance termine" "Green"
