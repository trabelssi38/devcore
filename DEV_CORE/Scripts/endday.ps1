# endday.ps1 — DEV_CORE v6
param([switch]$SkipBackup, [switch]$SkipQdrant)

$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { "C:\devcore\DEV_CORE_DATA" }
$AUTO          = "$DEV_CORE\Scripts\Auto"
$TODAY         = Get-Date -Format "yyyy-MM-dd"
$LOG           = "$DEV_CORE_DATA\Logs\scripts\endday_$TODAY.log"

function Log { param($msg,$color="Gray"); $l="[$(Get-Date -f HH:mm:ss)] $msg"; Add-Content $LOG $l -ErrorAction SilentlyContinue; Write-Host "  $l" -ForegroundColor $color }
function Run { param($script,$label)
    $p = "$AUTO\$script"
    if (Test-Path $p) { Log "→ $label" "Cyan"; & $p } else { Log "SKIP $script" "Yellow" }
}

Write-Host ""; Write-Host "  DEV_CORE v6 — END OF DAY" -ForegroundColor Cyan
Write-Host "  ─────────────────────────────────────" -ForegroundColor DarkGray; Write-Host ""

Log "1/8 Extraction leçons"   ; Run "lesson_extractor.ps1"  "lesson_extractor"
if (-not $SkipQdrant) { Log "2/8 Sync Qdrant"; Run "qdrant_sync.ps1" "qdrant_sync" } else { Log "2/8 Qdrant SKIP" "Gray" }
Log "3/8 Sync Obsidian"       ; Run "obsidian_sync.ps1"     "obsidian_sync"
Log "4/8 Rotation mémoire"    ; Run "memory_rotate.ps1"     "memory_rotate"
Log "5/8 Détection skills & Auto-Apprentissage" ; Run "auto_skills_detector.ps1" "auto_skills"
try {
    python "$DEV_CORE\Scripts\Auto\intent_learner.py"
} catch {
    Log "  Erreur auto-apprentissage: $_" "Yellow"
}

Log "6/8 Backup"
if (-not $SkipBackup) {
    $bdir = "$DEV_CORE_DATA\Backups\auto"
    New-Item -ItemType Directory -Path $bdir -Force | Out-Null
    try {
        foreach ($col in @("decisions","lessons","patterns","codebase")) {
            Invoke-RestMethod "http://localhost:6333/collections/$col/snapshots" -Method POST -ErrorAction SilentlyContinue | Out-Null
        }
        Log "  Snapshots Qdrant OK" "Green"
    } catch { Log "  Qdrant snapshot skip" "Yellow" }
    $memMd = "$DEV_CORE_DATA\Memory\MEMORY.md"
    if (Test-Path $memMd) { Copy-Item $memMd "$bdir\MEMORY_$TODAY.md" -Force }
    Log "  Backup OK" "Green"
}

Log "7/8 Rapport token"
try {
    python "$DEV_CORE\Scripts\Auto\token_report.py" --date $TODAY
    Log "  Rapport dynamique : $DEV_CORE_DATA\Logs\token_reports\$TODAY-report.html" "Green"
} catch {
    Log "  Repli sur le template statique..." "Yellow"
    $rptDir = "$DEV_CORE_DATA\Logs\token_reports"
    New-Item -ItemType Directory -Path $rptDir -Force | Out-Null
    $rpt = "$rptDir\$TODAY-report.html"
    $html = @"
<!DOCTYPE html><html><head><meta charset="utf-8">
<title>DEV_CORE Token Report $TODAY</title>
<style>body{{font-family:system-ui;max-width:700px;margin:40px auto;color:#1e293b}}
h1{{font-size:16px;color:#6366f1}}.m{{display:inline-block;padding:10px 18px;
background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;margin:6px;text-align:center}}
.v{{font-size:24px;font-weight:600}}.l{{font-size:11px;color:#64748b;margin-top:3px}}</style>
</head><body>
<h1>DEV_CORE v6 — Token Report $TODAY</h1>
<div class="m"><div class="v">—</div><div class="l">Total tokens</div></div>
<div class="m"><div class="v">—</div><div class="l">Cache hits</div></div>
<div class="m"><div class="v">—</div><div class="l">Sessions</div></div>
<p style="color:#94a3b8;font-size:12px;margin-top:20px">Auto-généré par endday.ps1 · DEV_CORE v6</p>
</body></html>
"@
    [System.IO.File]::WriteAllText($rpt, $html, [System.Text.Encoding]::UTF8)
    Log "  Rapport : $rpt" "Green"
}

Log "8/8 Next actions"
$na = "$DEV_CORE_DATA\Memory\next_actions.md"
if (Test-Path $na) { Write-Host ""; Get-Content $na | Select-Object -First 15 | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray } }

Write-Host ""; Write-Host "  ✓ End of day — $TODAY" -ForegroundColor Green; Write-Host ""
