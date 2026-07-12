# benchmark_reference.ps1 -- DEV_CORE reference benchmark artifact
param(
    [string]$OutputDir = "",
    [int]$Iterations = 3,
    [switch]$Json
)

$ErrorActionPreference = "Stop"

if ($Iterations -lt 1) { $Iterations = 1 }

$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { Split-Path -Parent $PSScriptRoot }
$DATA_ROOT = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { Join-Path (Split-Path -Parent $DEV_CORE) "DEV_CORE_DATA" }
$SCRIPTS = Join-Path $DEV_CORE "Scripts"
$DASHBOARD = Join-Path $DEV_CORE "Dashboard\index.html"

. "$SCRIPTS\platform_version.ps1"
$platform = Get-DevCorePlatformInfo

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path $DATA_ROOT "Logs\benchmarks"
}
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

function Measure-DevCoreAction {
    param(
        [Parameter(Mandatory=$true)][scriptblock]$Action
    )

    $timer = [System.Diagnostics.Stopwatch]::StartNew()
    & $Action
    $timer.Stop()
    return [math]::Round($timer.Elapsed.TotalMilliseconds, 3)
}

function Get-Percentile {
    param(
        [double[]]$Values,
        [double]$Percentile
    )

    if ($Values.Count -eq 0) { return 0 }
    $sorted = @($Values | Sort-Object)
    $index = [math]::Ceiling(($Percentile / 100.0) * $sorted.Count) - 1
    if ($index -lt 0) { $index = 0 }
    if ($index -ge $sorted.Count) { $index = $sorted.Count - 1 }
    return [math]::Round([double]$sorted[$index], 3)
}

function New-LatencyBenchmark {
    param(
        [Parameter(Mandatory=$true)][string]$Name,
        [Parameter(Mandatory=$true)][scriptblock]$Action,
        [string]$Unit = "ms"
    )

    $samples = @()
    for ($i = 0; $i -lt $Iterations; $i++) {
        $samples += Measure-DevCoreAction -Action $Action
    }

    return [pscustomobject]@{
        name = $Name
        kind = "latency"
        unit = $Unit
        iterations = $Iterations
        p50 = Get-Percentile -Values $samples -Percentile 50
        p95 = Get-Percentile -Values $samples -Percentile 95
        min = [math]::Round([double](@($samples | Measure-Object -Minimum).Minimum), 3)
        max = [math]::Round([double](@($samples | Measure-Object -Maximum).Maximum), 3)
        samples = @($samples)
    }
}

function New-SizeBenchmark {
    param(
        [Parameter(Mandatory=$true)][string]$Name,
        [Parameter(Mandatory=$true)][string]$Path
    )

    $bytes = if (Test-Path -LiteralPath $Path) { (Get-Item -LiteralPath $Path).Length } else { 0 }
    return [pscustomobject]@{
        name = $Name
        kind = "size"
        unit = "bytes"
        path = $Path
        bytes = [int64]$bytes
        exists = [bool](Test-Path -LiteralPath $Path)
    }
}

$benchmarks = @(
    (New-SizeBenchmark -Name "dashboard_payload_size" -Path $DASHBOARD),
    (New-LatencyBenchmark -Name "verify_config_load" -Action {
        $source = Get-Content -LiteralPath (Join-Path $SCRIPTS "verify.ps1") -Raw -Encoding UTF8
        if ($source -notmatch "Get-CiChecks") { throw "verify.ps1 missing Get-CiChecks" }
    })
)

$report = [pscustomobject]@{
    schema_version = "1.0"
    platform_version = $platform.version
    generated_at = (Get-Date).ToString("o")
    machine = $env:COMPUTERNAME
    iterations = $Iterations
    benchmarks = @($benchmarks)
    artifact_path = $null
}

$fileName = "benchmark-reference-{0}.json" -f (Get-Date -Format "yyyyMMdd-HHmmss")
$artifactPath = Join-Path $OutputDir $fileName
$report.artifact_path = $artifactPath
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $artifactPath -Encoding UTF8

if ($Json) {
    $report | ConvertTo-Json -Depth 8
} else {
    Write-Host "[OK] Benchmark reference artifact: $artifactPath" -ForegroundColor Green
    foreach ($benchmark in $benchmarks) {
        if ($benchmark.kind -eq "latency") {
            Write-Host ("[BENCH] {0} p50={1}{2} p95={3}{2}" -f $benchmark.name, $benchmark.p50, $benchmark.unit, $benchmark.p95)
        } else {
            Write-Host ("[BENCH] {0} {1}={2}" -f $benchmark.name, $benchmark.unit, $benchmark.bytes)
        }
    }
}

exit 0
