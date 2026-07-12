# ci_python_tests.ps1 -- portable Python test runner
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$tests = @(
    "DEV_CORE/API/test_api_v1.py",
    "DEV_CORE/API/test_api_versioning_policy.py",
    "DEV_CORE/API/test_domain_contracts.py",
    "DEV_CORE/API/test_openapi_client_generation.py",
    "DEV_CORE/API/test_ports.py",
    "DEV_CORE/Database/test_importer_reconciliation.py",
    "DEV_CORE/Database/test_postgres_schema_contract.py",
    "DEV_CORE/Database/test_repositories_transactions.py",
    "DEV_CORE/Database/test_sqlalchemy_alembic_setup.py",
    "DEV_CORE/Scripts/test_dashboard_api.py",
    "DEV_CORE/MCP/obsidian-vault/test_obsidian_vault_paths.py",
    "DEV_CORE/Scripts/Auto/test_model_pricing_sync.py",
    "DEV_CORE/Scripts/Auto/test_token_report_clients.py"
)

$existingTests = @()
foreach ($test in $tests) {
    if (Test-Path -LiteralPath (Join-Path $repoRoot $test)) {
        $existingTests += $test
    }
}

if ($existingTests.Count -eq 0) {
    Write-Host "[FAIL] No Python tests configured" -ForegroundColor Red
    exit 1
}

$pytestCheck = & python -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('pytest') else 1)"
if ($LASTEXITCODE -eq 0) {
    & python -m pytest @existingTests
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "[WARN] pytest unavailable; using stdlib fallback runner" -ForegroundColor Yellow
    $runner = Join-Path $env:TEMP "devcore_pytest_fallback.py"
    @'
import importlib.util
import inspect
import sys
import tempfile
from pathlib import Path

failures = []
tests = sys.argv[1:]

for test_path in tests:
    path = Path(test_path).resolve()
    spec = importlib.util.spec_from_file_location(path.stem + "_fallback", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    for name, func in sorted(vars(module).items()):
        if not name.startswith("test_") or not callable(func):
            continue

        kwargs = {}
        tmp_ctx = None
        try:
            sig = inspect.signature(func)
            for param in sig.parameters.values():
                if param.name == "tmp_path":
                    tmp_ctx = tempfile.TemporaryDirectory()
                    kwargs[param.name] = Path(tmp_ctx.name)
                else:
                    raise RuntimeError(f"unsupported fixture: {param.name}")
            func(**kwargs)
            print(f"[PYTEST-FALLBACK OK] {path.name}::{name}")
        except Exception as exc:
            failures.append(f"{path.name}::{name} -- {exc}")
        finally:
            if tmp_ctx:
                tmp_ctx.cleanup()

if failures:
    print("[FAIL] Python fallback test failures:")
    for failure in failures:
        print("  " + failure)
    sys.exit(1)

print("[OK] Python fallback tests passed")
'@ | Set-Content -LiteralPath $runner -Encoding UTF8
    & python $runner @existingTests
    $fallbackExit = $LASTEXITCODE
    Remove-Item -LiteralPath $runner -Force -ErrorAction SilentlyContinue
    if ($fallbackExit -ne 0) { exit $fallbackExit }
}

Write-Host "[OK] Python tests passed" -ForegroundColor Green
exit 0
