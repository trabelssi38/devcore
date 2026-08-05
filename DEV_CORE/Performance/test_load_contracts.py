import sys
from pathlib import Path


PERFORMANCE_ROOT = Path(__file__).resolve().parent
DEV_CORE_ROOT = PERFORMANCE_ROOT.parent
for path in [
    DEV_CORE_ROOT / "Performance",
    DEV_CORE_ROOT / "API",
    DEV_CORE_ROOT / "_archive" / "Database",
    DEV_CORE_ROOT / "Scripts",
]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def test_api_sse_worker_and_db_load_contracts_stay_inside_local_budgets() -> None:
    from devcore_load import run_local_load_contract

    report = run_local_load_contract(
        api_iterations=40,
        sse_iterations=120,
        worker_iterations=300,
        db_iterations=160,
    )

    assert report["schema_version"] == 1
    assert report["api"]["operations"] == 120
    assert report["api"]["p95_ms"] < 150
    assert report["sse"]["events"] == 120
    assert report["sse"]["p95_ms"] < 10
    assert report["workers"]["runs"] == 300
    assert report["workers"]["p95_ms"] < 10
    assert report["db"]["operations"] == 320
    assert report["db"]["p95_ms"] < 10
