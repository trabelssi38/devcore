# test_hermes_hardening.ps1 -- Hermes cron health, lock and rotation contracts
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$dashboard = Join-Path $PSScriptRoot "gen_dashboard.ps1"
$tick = Join-Path $PSScriptRoot "hermes_cron_tick.py"
$sync = Join-Path $PSScriptRoot "Auto\sync_cron_jobs.py"

function Assert-SourceContains {
    param([string]$Source, [string]$Pattern, [string]$Message)
    if ($Source -notmatch $Pattern) { throw $Message }
}

$dashboardSource = Get-Content -LiteralPath $dashboard -Raw -Encoding UTF8
Assert-SourceContains $dashboardSource 'HERMES_TICK_WARN_SECONDS\s*=\s*600' "dashboard should use a 600s Hermes tick warning threshold"
Assert-SourceContains $dashboardSource 'Get-HermesCronProcesses' "dashboard should check hermes_cron_tick.py process state"
Assert-SourceContains $dashboardSource 'status-degraded' "dashboard should render degraded Hermes status without red failure"
if ($dashboardSource -match 'lastTickSec\s+-lt\s+150') {
    throw "dashboard must not depend on a 150s tick-only health threshold"
}

$tickSource = Get-Content -LiteralPath $tick -Raw -Encoding UTF8
Assert-SourceContains $tickSource 'RotatingFileHandler' "cron tick should rotate cron_tick.log"
Assert-SourceContains $tickSource 'LOCK_FILE' "cron tick should define a lock file"
Assert-SourceContains $tickSource 'msvcrt\.locking' "cron tick should use Windows single-instance file locking"
Assert-SourceContains $tickSource 'sys\.exit\(0\)' "cron tick should exit cleanly when another daemon owns the lock"

$syncSource = Get-Content -LiteralPath $sync -Raw -Encoding UTF8
Assert-SourceContains $syncSource 'repair_next_run_at' "sync_cron_jobs should repair stale next_run_at"
Assert-SourceContains $syncSource 'LEGACY_HERMES_RUNTIME_HOME' "sync_cron_jobs should also repair legacy ~/.hermes jobs.json"
Assert-SourceContains $syncSource 'mirror_jobs_to_legacy_home' "sync_cron_jobs should mirror jobs to ~/.hermes"

Write-Host "[OK] Hermes hardening contracts passed" -ForegroundColor Green
