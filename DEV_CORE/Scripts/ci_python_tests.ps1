param(
    [string[]]$Include,
    [string[]]$Exclude
)

# ci_python_tests.ps1 -- portable Python test runner
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$tests = @(
    "DEV_CORE/Scripts/test_ai_capability_registry.py",
    "DEV_CORE/Scripts/test_gemini_router_routing_profile.py",
    "DEV_CORE/API/test_api_v1.py",
    "DEV_CORE/API/test_api_versioning_policy.py",
    "DEV_CORE/API/test_correlation_context.py",
    "DEV_CORE/API/test_domain_contracts.py",
    "DEV_CORE/API/test_dual_read_cutover.py",
    "DEV_CORE/API/test_eval_datasets.py",
    "DEV_CORE/API/test_github_webhooks.py",
    "DEV_CORE/API/test_llmops_langfuse.py",
    "DEV_CORE/API/test_openapi_client_generation.py",
    "DEV_CORE/API/test_observability_instrumentation.py",
    "DEV_CORE/API/test_ports.py",
    "DEV_CORE/API/test_prometheus_metrics.py",
    "DEV_CORE/API/test_run_pause_resume_cancel.py",
    "DEV_CORE/API/test_run_state_machine.py",
    "DEV_CORE/API/test_slo_budget_policy.py",
    "DEV_CORE/API/test_worker_execution.py",
    "DEV_CORE/_archive/Database/test_audit_log_service.py",
    "DEV_CORE/_archive/Database/test_backup_restore_downgrade.py",
    "DEV_CORE/_archive/Database/test_importer_reconciliation.py",
    "DEV_CORE/_archive/Database/test_outbox_idempotency.py",
    "DEV_CORE/_archive/Database/test_outbox_retry_dlq.py",
    "DEV_CORE/_archive/Database/test_postgres_schema_contract.py",
    "DEV_CORE/_archive/Database/test_repositories_transactions.py",
    "DEV_CORE/_archive/Database/test_schedules_persistence.py",
    "DEV_CORE/_archive/Database/test_sqlalchemy_alembic_setup.py",
    "DEV_CORE/_archive/Database/test_tenant_isolation_matrix.py",
    "DEV_CORE/_archive/Database/test_workspace_isolation.py",
    "DEV_CORE/docs/test_operator_docs.py",
    "DEV_CORE/Performance/test_load_contracts.py",
    "DEV_CORE/Performance/test_failure_drills.py",
    "DEV_CORE/Security/test_security_review.py",
    "DEV_CORE/Release/test_release_packaging.py",
    "DEV_CORE/Support/test_incident_runbook.py",
    "DEV_CORE/Plugins/test_manifest_v2_contract.py",
    "DEV_CORE/Templates/test_workflow_templates.py",
    "DEV_CORE/Scripts/test_dashboard_api.py",
    "DEV_CORE/Skills/test_ui_ux_skill_devcore.py",
    "DEV_CORE/MCP/obsidian-vault/test_obsidian_vault_paths.py",
    "DEV_CORE/Scripts/Auto/test_model_pricing_sync.py",
    "DEV_CORE/Scripts/Auto/test_token_report_clients.py",
    "DEV_CORE/Web/test_frontend_scaffold.py",
    "DEV_CORE/Web/test_dashboard_components.py",
    "DEV_CORE/Web/test_api_client_sse.py",
    "DEV_CORE/Web/test_ui_states_network_recovery.py",
    "DEV_CORE/Web/test_responsive_accessibility.py",
    "DEV_CORE/Web/test_playwright_setup.py"
)

$existingTests = @()
foreach ($test in $tests) {
    if (Test-Path -LiteralPath (Join-Path $repoRoot $test)) {
        $existingTests += $test
    }
}

if ($Include -and $Include.Count -gt 0) {
    $existingTests = @($existingTests | Where-Object { $Include -contains $_ })
}
if ($Exclude -and $Exclude.Count -gt 0) {
    $existingTests = @($existingTests | Where-Object { $Exclude -notcontains $_ })
}

if ($existingTests.Count -eq 0) {
    Write-Host "[FAIL] No Python tests configured" -ForegroundColor Red
    exit 1
}

$pytestCheck = & python -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('pytest') else 1)"
if ($LASTEXITCODE -eq 0) {
    if ($IsWindows -or $env:OS -eq 'Windows_NT') {
        & python (Join-Path $PSScriptRoot 'run_windows_pytest.py') @existingTests
    } else {
        & python -m pytest -p no:cacheprovider @existingTests
    }
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "[WARN] pytest unavailable; using stdlib fallback runner" -ForegroundColor Yellow
    $fallbackRoot = Join-Path $repoRoot ("pytest-fallback-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $fallbackRoot | Out-Null
    $runner = Join-Path $fallbackRoot "runner.py"
    @'
import importlib.util
import inspect
import os
import shutil
import sys
from uuid import uuid4
from pathlib import Path

failures = []
tests = sys.argv[1:]
root = Path(__file__).resolve().parent

for test_path in tests:
    path = Path(test_path).resolve()
    spec = importlib.util.spec_from_file_location(path.stem + "_fallback", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    for name, func in sorted(vars(module).items()):
        if not name.startswith("test_") or not callable(func):
            continue

        kwargs = {}
        tmp_path = None
        try:
            sig = inspect.signature(func)
            for param in sig.parameters.values():
                if param.name == "tmp_path":
                    tmp_path = root / ("fixture-" + uuid4().hex)
                    tmp_path.mkdir(mode=0o750)
                    kwargs[param.name] = tmp_path
                else:
                    raise RuntimeError(f"unsupported fixture: {param.name}")
            func(**kwargs)
            print(f"[PYTEST-FALLBACK OK] {path.name}::{name}")
        except Exception as exc:
            failures.append(f"{path.name}::{name} -- {exc}")
        finally:
            if tmp_path:
                shutil.rmtree(tmp_path)

if failures:
    print("[FAIL] Python fallback test failures:")
    for failure in failures:
        print("  " + failure)
    sys.exit(1)

print("[OK] Python fallback tests passed")
'@ | Set-Content -LiteralPath $runner -Encoding UTF8
    try {
        & python $runner @existingTests
        $fallbackExit = $LASTEXITCODE
    } finally {
        Remove-Item -LiteralPath $fallbackRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
    if ($fallbackExit -ne 0) { exit $fallbackExit }
}

Write-Host "[OK] Python tests passed" -ForegroundColor Green
exit 0
