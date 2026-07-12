# ci_powershell_tests.ps1 -- portable PowerShell test runner
$ErrorActionPreference = "Stop"

$tests = @(
    "test_verify_ci.ps1",
    "test_ci_workflow.ps1",
    "test_benchmark_pipeline.ps1",
    "test_network_bind_contract.ps1",
    "test_dashboard_auth_contract.ps1",
    "test_test_exit_contract.ps1",
    "test_platform_version.ps1",
    "test_embedding_contract.ps1",
    "test_health_report.ps1",
    "test_diagnose_gate.ps1",
    "test_secret_scan.ps1",
    "test_dc_dispatch.ps1",
    "test_task_service.ps1",
    "test_gateway.ps1",
    "test_context_service.ps1",
    "test_memory_service.ps1",
    "test_metrics_service.ps1",
    "test_event_bus.ps1",
    "test_knowledge_graph.ps1",
    "test_plugin_service.ps1",
    "test_skills_runtime.ps1",
    "test_auto_skills_pipeline.ps1",
    "test_internal_plugins.ps1",
    "test_repowise_watch_worker.ps1"
)

foreach ($test in $tests) {
    $path = Join-Path $PSScriptRoot $test
    if (-not (Test-Path -LiteralPath $path)) {
        Write-Host "[FAIL] Missing PowerShell test: $test" -ForegroundColor Red
        exit 1
    }

    Write-Host "[TEST] $test" -ForegroundColor Cyan
    & powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $path
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "[OK] PowerShell tests passed" -ForegroundColor Green
exit 0
