# endday.ps1 -- DEV_CORE session close
param(
    [switch]$SkipBackup,
    [switch]$SkipQdrant,
    [switch]$AgentMode,
    [switch]$Full,
    [int]$StepTimeoutSeconds = 60
)

$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { "C:\devcore\DEV_CORE_DATA" }
$AUTO          = "$DEV_CORE\Scripts\Auto"
$TODAY         = Get-Date -Format "yyyy-MM-dd"
$LOG           = "$DEV_CORE_DATA\Logs\scripts\endday_$TODAY.log"
$LOCK_FILE     = "$DEV_CORE_DATA\Runtime\endday.lock"
$ENDDAY_STARTED = Get-Date
$METRICS_SERVICE = "$DEV_CORE\Scripts\metrics_service.ps1"
. "$PSScriptRoot\platform_version.ps1"
$PLATFORM = Get-DevCorePlatformInfo

if ($SkipBackup.IsPresent -and -not $Full.IsPresent) { $AgentMode = $true }

function Log { param($msg,$color="Gray"); $l="[$(Get-Date -f HH:mm:ss)] $msg"; Add-Content $LOG $l -ErrorAction SilentlyContinue; Write-Host "  $l" -ForegroundColor $color }
function Record-Metric { param([string]$MetricType,[double]$Value,[string]$Unit="count",[hashtable]$Payload=@{})
    if (-not (Test-Path $METRICS_SERVICE)) { return }
    try {
        $payloadJson = $Payload | ConvertTo-Json -Depth 8 -Compress
        & $METRICS_SERVICE -Action Record -Source "endday" -Project "devcore" -MetricType $MetricType -Value $Value -Unit $Unit -PayloadJson $payloadJson 6>$null | Out-Null
    } catch {}
}
function Acquire-EnddayLock {
    $runtimeDir = Split-Path -Parent $LOCK_FILE
    New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null
    if (Test-Path -LiteralPath $LOCK_FILE) {
        try {
            $existing = Get-Content -LiteralPath $LOCK_FILE -Raw -Encoding UTF8 | ConvertFrom-Json
            $existingPid = [int]$existing.pid
            $createdAt = [datetime]$existing.created_at
            $processAlive = $false
            if ($existingPid -gt 0) {
                $processAlive = $null -ne (Get-Process -Id $existingPid -ErrorAction SilentlyContinue)
            }
            if ($processAlive -and ((Get-Date) - $createdAt).TotalHours -lt 2) {
                Log "endday already running pid=$existingPid -- skip" "Yellow"
                return $false
            }
        } catch {}
        Remove-Item -LiteralPath $LOCK_FILE -Force -ErrorAction SilentlyContinue
    }
    $lock = @{
        pid = $PID
        created_at = (Get-Date).ToString("o")
        agent_mode = [bool]$AgentMode
    }
    [System.IO.File]::WriteAllText($LOCK_FILE, ($lock | ConvertTo-Json -Compress), [System.Text.Encoding]::UTF8)
    return $true
}
function Release-EnddayLock {
    try {
        if (Test-Path -LiteralPath $LOCK_FILE) {
            $existing = Get-Content -LiteralPath $LOCK_FILE -Raw -Encoding UTF8 | ConvertFrom-Json
            if ([int]$existing.pid -eq $PID) {
                Remove-Item -LiteralPath $LOCK_FILE -Force -ErrorAction SilentlyContinue
            }
        }
    } catch {
        Remove-Item -LiteralPath $LOCK_FILE -Force -ErrorAction SilentlyContinue
    }
}
function Invoke-EnddayStep {
    param(
        [string]$Label,
        [scriptblock]$ScriptBlock,
        [object[]]$ArgumentList = @(),
        [int]$TimeoutSeconds = $StepTimeoutSeconds
    )
    $stepStarted = Get-Date
    try {
        if ($TimeoutSeconds -le 0) {
            & $ScriptBlock @ArgumentList
            return $true
        }
        $job = Start-Job -ScriptBlock $ScriptBlock -ArgumentList $ArgumentList
        if (Wait-Job -Timeout $TimeoutSeconds -Job $job) {
            Receive-Job -Job $job 2>&1 | Out-Null
            return $true
        }
        Stop-Job -Job $job -ErrorAction SilentlyContinue
        Log "  [WARN] $Label timeout after ${TimeoutSeconds}s" "Yellow"
        Record-Metric -MetricType "timeout" -Value 1 -Unit "count" -Payload @{ component = "endday"; step = $Label; timeout_seconds = $TimeoutSeconds }
        return $false
    } catch {
        Log "  [WARN] $Label failed: $_" "Yellow"
        return $false
    } finally {
        if ($job) { Remove-Job -Job $job -Force -ErrorAction SilentlyContinue }
        $stepElapsed = ((Get-Date) - $stepStarted).TotalSeconds
        Record-Metric -MetricType "duration" -Value $stepElapsed -Unit "seconds" -Payload @{ component = "endday"; step = $Label }
    }
}
function Run { param($script,$label)
    $p = "$AUTO\$script"
    if (Test-Path $p) {
        Log "-> $label" "Cyan"
        Invoke-EnddayStep -Label $label -ScriptBlock { param($ScriptPath) & $ScriptPath } -ArgumentList @($p) | Out-Null
    } else { Log "SKIP $script" "Yellow" }
}

Write-Host ""; Write-Host "  $($PLATFORM.title) -- END OF DAY" -ForegroundColor Cyan
Write-Host "  -------------------------------------" -ForegroundColor DarkGray; Write-Host ""

if (-not (Acquire-EnddayLock)) {
    Record-Metric -MetricType "skipped" -Value 1 -Unit "count" -Payload @{ component = "endday"; reason = "lock_active" }
    exit 0
}

try {
    Log "1/8 Extraction lecons"   ; Run "lesson_extractor.ps1"  "lesson_extractor"
    if ($AgentMode) {
        Log "AgentMode Qdrant SKIP" "Gray"
        Log "AgentMode Obsidian SKIP" "Gray"
        Log "AgentMode memory rotate SKIP" "Gray"
        Log "AgentMode memory hierarchy SKIP" "Gray"
        Log "AgentMode auto skills SKIP" "Gray"
    } else {
        if (-not $SkipQdrant) { Log "2/8 Sync Qdrant"; Run "qdrant_sync.ps1" "qdrant_sync" } else { Log "2/8 Qdrant SKIP" "Gray" }
        Log "3/8 Sync Obsidian"       ; Run "obsidian_sync.ps1"     "obsidian_sync"
        Log "4/8 Rotation memoire"    ; Run "memory_rotate.ps1"     "memory_rotate"
        Log "4.5/8 Consolidation memoire hierarchique L1 -> L2/L3"
        Invoke-EnddayStep -Label "memory_hierarchy" -ScriptBlock { param($ScriptPath) & $ScriptPath -Action Aggregate } -ArgumentList @("$DEV_CORE\Scripts\memory_hierarchy.ps1") | Out-Null

        Log "5/8 Detection skills et Auto-Apprentissage" ; Run "auto_skills_detector.ps1" "auto_skills"
    }
    if ($AgentMode) {
        Log "AgentMode intent learner SKIP" "Gray"
    } else {
        Invoke-EnddayStep -Label "intent_learner" -ScriptBlock { param($ScriptPath) python $ScriptPath } -ArgumentList @("$DEV_CORE\Scripts\Auto\intent_learner.py") | Out-Null
    }

    Log "6/8 Backup"
    if (-not $SkipBackup) {
        $bdir = "$DEV_CORE_DATA\Backups\auto"
        New-Item -ItemType Directory -Path $bdir -Force | Out-Null
        try {
            foreach ($col in @("decisions","lessons","patterns","codebase")) {
                Invoke-RestMethod "http://localhost:6333/collections/$col/snapshots" -Method POST -TimeoutSec 10 -ErrorAction SilentlyContinue | Out-Null
            }
            Log "  Snapshots Qdrant OK" "Green"
        } catch { Log "  Qdrant snapshot skip" "Yellow" }
        $memMd = "$DEV_CORE_DATA\Memory\MEMORY.md"
        if (Test-Path $memMd) { Copy-Item $memMd "$bdir\MEMORY_$TODAY.md" -Force }
        Log "  Backup OK" "Green"
    }

    Log "6.5/8 Sync tarifs modeles"
    if ($AgentMode) {
        Log "AgentMode pricing sync SKIP" "Gray"
    } else {
        Invoke-EnddayStep -Label "model_pricing_sync" -TimeoutSeconds 30 -ScriptBlock { param($ScriptPath) & $ScriptPath } -ArgumentList @("$DEV_CORE\Scripts\Auto\model_pricing_sync.ps1") | Out-Null
        Log "  Pricing sync OK : $DEV_CORE_DATA\Logs\pricing\model_pricing_sync_report.json" "Green"
    }

    Log "7/8 Rapport token"
    if ($AgentMode) {
        Log "AgentMode Rapport token SKIP" "Gray"
    } else {
        $tokenOk = Invoke-EnddayStep -Label "token_report" -TimeoutSeconds 180 -ScriptBlock { param($ScriptPath,$Date) python $ScriptPath --date $Date } -ArgumentList @("$DEV_CORE\Scripts\Auto\token_report.py", $TODAY)
        if ($tokenOk) {
            Log "  Rapport dynamique : $DEV_CORE_DATA\Logs\token_reports\$TODAY-report.html" "Green"
        } else {
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
<h1>$($PLATFORM.title) -- Token Report $TODAY</h1>
<div class="m"><div class="v">-</div><div class="l">Total tokens</div></div>
<div class="m"><div class="v">-</div><div class="l">Cache hits</div></div>
<div class="m"><div class="v">-</div><div class="l">Sessions</div></div>
<p style="color:#94a3b8;font-size:12px;margin-top:20px">Auto-genere par endday.ps1 - $($PLATFORM.title)</p>
</body></html>
"@
            [System.IO.File]::WriteAllText($rpt, $html, [System.Text.Encoding]::UTF8)
            Log "  Rapport : $rpt" "Green"
        }
    }

    Log "7.5/8 Task scan + sync final"
    if ($AgentMode) {
        Log "AgentMode Task scan + sync final SKIP" "Gray"
    } else {
        Invoke-EnddayStep -Label "task_scan" -TimeoutSeconds 120 -ScriptBlock { param($ScriptPath) & $ScriptPath } -ArgumentList @("$DEV_CORE\Scripts\task_scan.ps1") | Out-Null
        Invoke-EnddayStep -Label "task_sync" -TimeoutSeconds 120 -ScriptBlock { param($ScriptPath) & $ScriptPath } -ArgumentList @("$DEV_CORE\Scripts\task_sync.ps1") | Out-Null
        Log "  Scan + Sync final OK" "Green"
    }

    Log "8/8 Next actions"
    $na = "$DEV_CORE_DATA\Memory\next_actions.md"
    $enddayElapsed = ((Get-Date) - $ENDDAY_STARTED).TotalSeconds
    Record-Metric -MetricType "duration" -Value $enddayElapsed -Unit "seconds" -Payload @{ status = "success"; component = "endday"; agent_mode = [bool]$AgentMode }
    Record-Metric -MetricType "success" -Value 1 -Unit "count" -Payload @{ component = "endday"; agent_mode = [bool]$AgentMode }
    if (Test-Path $na) { Write-Host ""; Get-Content $na | Select-Object -First 15 | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray } }

    Write-Host ""; Write-Host "  OK End of day -- $TODAY" -ForegroundColor Green; Write-Host ""
} finally {
    Release-EnddayLock
}
