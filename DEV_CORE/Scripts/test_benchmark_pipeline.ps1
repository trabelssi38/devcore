# test_benchmark_pipeline.ps1 -- reference benchmark pipeline contract
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$benchmarkScript = Join-Path $PSScriptRoot "benchmark_reference.ps1"
$verifyScript = Join-Path $PSScriptRoot "verify.ps1"
$workflowPath = Join-Path $repoRoot ".github\workflows\ci.yml"
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("devcore-benchmark-test-" + [guid]::NewGuid().ToString("N"))

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

try {
    Assert-True (Test-Path -LiteralPath $benchmarkScript) "benchmark_reference.ps1 should exist"

    New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null
    $output = & powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $benchmarkScript -OutputDir $tempRoot -Iterations 1 -Json | Out-String
    if ($LASTEXITCODE -ne 0) {
        throw "benchmark_reference.ps1 should exit 0. Output: $output"
    }

    $report = $output | ConvertFrom-Json
    Assert-True ($report.schema_version -eq "1.0") "benchmark report should expose schema_version 1.0"
    Assert-True (-not [string]::IsNullOrWhiteSpace([string]$report.generated_at)) "benchmark report should include generated_at"
    Assert-True (-not [string]::IsNullOrWhiteSpace([string]$report.artifact_path)) "benchmark report should include artifact_path"
    Assert-True (Test-Path -LiteralPath $report.artifact_path) "benchmark artifact should be written"
    Assert-True (@($report.benchmarks).Count -ge 2) "benchmark report should include at least two measurements"
    Assert-True (@($report.benchmarks | Where-Object name -eq "dashboard_payload_size").Count -eq 1) "benchmark should include dashboard_payload_size"
    Assert-True (@($report.benchmarks | Where-Object name -eq "verify_config_load").Count -eq 1) "benchmark should include verify_config_load"

    $artifactReport = Get-Content -LiteralPath $report.artifact_path -Raw -Encoding UTF8 | ConvertFrom-Json
    Assert-True ($artifactReport.schema_version -eq "1.0") "artifact report should be valid JSON"

    $verifySource = Get-Content -LiteralPath $verifyScript -Raw -Encoding UTF8
    Assert-True ($verifySource -match 'name\s*=\s*"benchmarks"') "verify.ps1 should include benchmarks in CI checks"

    $workflow = Get-Content -LiteralPath $workflowPath -Raw -Encoding UTF8
    Assert-True ($workflow -match "benchmark_reference.ps1") "CI workflow should run benchmark_reference.ps1"
    Assert-True ($workflow -match "actions/upload-artifact") "CI workflow should upload benchmark artifacts"

    Write-Host "[OK] benchmark pipeline tests passed" -ForegroundColor Green
} finally {
    Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}
