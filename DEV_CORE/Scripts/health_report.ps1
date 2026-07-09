# health_report.ps1 -- DEV_CORE v10 short local health report
param(
    [switch]$Json
)

$ErrorActionPreference = "Stop"
$started = Get-Date
$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { "C:\devcore\DEV_CORE_DATA" }
$checks = New-Object System.Collections.Generic.List[object]

function Add-HealthCheck {
    param(
        [string]$Component,
        [string]$Name,
        [ValidateSet("OK", "WARN", "FAIL")][string]$Status,
        [string]$Detail = "",
        [string]$Fix = ""
    )

    $checks.Add([PSCustomObject]@{
        component = $Component
        name      = $Name
        status    = $Status
        detail    = $Detail
        fix       = $Fix
    }) | Out-Null
}

function Test-PortFast {
    param(
        [int]$Port,
        [int]$TimeoutMs = 250
    )

    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $result = $tcp.BeginConnect([System.Net.IPAddress]::Loopback, $Port, $null, $null)
        $success = $result.AsyncWaitHandle.WaitOne($TimeoutMs, $true)
        if ($success) { $tcp.EndConnect($result) }
        $tcp.Close()
        return $success
    } catch {
        return $false
    }
}

function Get-TaskBoardPath {
    $project = "devcore"
    $activeProjectScript = Join-Path $PSScriptRoot "Get-ActiveProject.ps1"
    if (Test-Path $activeProjectScript) {
        try { $project = (& $activeProjectScript).Trim() } catch {}
    }
    return Join-Path $DEV_CORE_DATA "Memory\$project\tasks.json"
}

# Paths
if (Test-Path $DEV_CORE) {
    Add-HealthCheck "paths" "DEVCORE_PLATFORM_ROOT" "OK" $DEV_CORE
} else {
    Add-HealthCheck "paths" "DEVCORE_PLATFORM_ROOT" "FAIL" $DEV_CORE "Set DEVCORE_PLATFORM_ROOT"
}

if (Test-Path $DEV_CORE_DATA) {
    Add-HealthCheck "paths" "DEVCORE_DATA_ROOT" "OK" $DEV_CORE_DATA
} else {
    Add-HealthCheck "paths" "DEVCORE_DATA_ROOT" "FAIL" $DEV_CORE_DATA "Set DEVCORE_DATA_ROOT"
}

# Services
$servicePorts = @(
    @{ name = "Qdrant"; port = 6333; fix = "Start Qdrant" },
    @{ name = "Gemini Router"; port = 20130; fix = "dc launch" },
    @{ name = "Dashboard API"; port = 20129; fix = "dc launch" },
    @{ name = "Headroom Proxy"; port = 8787; fix = "headroom_start.ps1" },
    @{ name = "Repowise Server"; port = 7337; fix = "repowise serve" }
)
foreach ($service in $servicePorts) {
    if (Test-PortFast -Port $service.port) {
        Add-HealthCheck "services" $service.name "OK" "Port $($service.port)"
    } else {
        Add-HealthCheck "services" $service.name "WARN" "Port $($service.port) unavailable" $service.fix
    }
}

# Secrets: quick health uses git grep; diagnose.ps1 keeps the deeper scanner.
try {
    $secretPattern = "sk-[A-Za-z0-9_-]{20,}|AQ\.[A-Za-z0-9_-]{30,}|AIza[0-9A-Za-z_-]{20,}"
    $secretHits = & git -C (Get-Location).Path grep -I -n -E $secretPattern -- `
        ":!DEV_CORE/Config/gemini_api_key.txt" `
        ":!DEV_CORE/Dashboard/index.html" `
        ":!DEV_CORE_DATA/**" 2>$null
    if ($LASTEXITCODE -eq 0 -and $secretHits) {
        Add-HealthCheck "secrets" "tracked files quick scan" "FAIL" "Potential secret pattern found" "Run secret_scan.ps1"
    } else {
        Add-HealthCheck "secrets" "tracked files quick scan" "OK" "No hardcoded secret pattern detected"
    }
} catch {
    Add-HealthCheck "secrets" "tracked files quick scan" "WARN" "git grep unavailable" "Run secret_scan.ps1"
}

# Task board
$taskBoardPath = Get-TaskBoardPath
if (Test-Path $taskBoardPath) {
    try {
        $board = Get-Content $taskBoardPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $active = @($board.tasks | Where-Object { $_.status -eq "active" }).Count
        $todo = @($board.tasks | Where-Object { $_.status -eq "todo" }).Count
        Add-HealthCheck "task_board" "tasks.json" "OK" "active=$active todo=$todo path=$taskBoardPath"
    } catch {
        Add-HealthCheck "task_board" "tasks.json" "FAIL" "Unreadable: $_" "Validate JSON"
    }
} else {
    Add-HealthCheck "task_board" "tasks.json" "WARN" "Missing: $taskBoardPath" "dc new task [title]"
}

# Memory
$memoryPath = Join-Path $DEV_CORE_DATA "Memory"
$memoryFile = Join-Path $memoryPath "MEMORY.md"
if (Test-Path $memoryPath) {
    Add-HealthCheck "memory" "Memory directory" "OK" $memoryPath
} else {
    Add-HealthCheck "memory" "Memory directory" "FAIL" $memoryPath "Create memory directory"
}
if (Test-Path $memoryFile) {
    $lineCount = @(Get-Content $memoryFile -ErrorAction SilentlyContinue).Count
    Add-HealthCheck "memory" "MEMORY.md" "OK" "$lineCount lines"
} else {
    Add-HealthCheck "memory" "MEMORY.md" "WARN" "Missing: $memoryFile" "launch.ps1"
}

$durationMs = [int]((Get-Date) - $started).TotalMilliseconds
$okCount = 0
$warnCount = 0
$failCount = 0
foreach ($check in $checks) {
    switch ($check.status) {
        "OK" { $okCount++ }
        "WARN" { $warnCount++ }
        "FAIL" { $failCount++ }
    }
}
$overall = if ($failCount -gt 0) { "FAIL" } elseif ($warnCount -gt 0) { "WARN" } else { "OK" }
$projectName = "devcore"
try { $projectName = (& "$PSScriptRoot\Get-ActiveProject.ps1" 2>$null).Trim() } catch {}
$checkArray = @()
foreach ($check in $checks) { $checkArray += $check }

$report = [PSCustomObject]@{
    schema_version = "1.0"
    generated_at   = (Get-Date).ToString("o")
    project        = $projectName
    overall        = $overall
    ok             = $okCount
    warn           = $warnCount
    fail           = $failCount
    duration_ms    = $durationMs
    checks         = $checkArray
}

if ($Json) {
    $report | ConvertTo-Json -Depth 8
} else {
    Write-Host ""
    Write-Host "  DEV_CORE v10 -- Health" -ForegroundColor Cyan
    Write-Host "  ======================" -ForegroundColor DarkGray
    foreach ($check in $checks) {
        $color = switch ($check.status) { "OK" { "Green" } "WARN" { "Yellow" } default { "Red" } }
        Write-Host ("  [{0}] {1}/{2} -- {3}" -f $check.status, $check.component, $check.name, $check.detail) -ForegroundColor $color
        if ($check.fix) { Write-Host "       Fix: $($check.fix)" -ForegroundColor DarkGray }
    }
    Write-Host ""
    Write-Host "  Overall: $overall | OK: $($report.ok) WARN: $warnCount FAIL: $failCount | ${durationMs}ms" -ForegroundColor White
    Write-Host ""
}

if ($failCount -gt 0) { exit 1 }
exit 0
