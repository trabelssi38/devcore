import sys
from pathlib import Path


PERFORMANCE_ROOT = Path(__file__).resolve().parent
DEV_CORE_ROOT = PERFORMANCE_ROOT.parent
for path in [
    DEV_CORE_ROOT / "Performance",
    DEV_CORE_ROOT / "API",
    DEV_CORE_ROOT / "_archive" / "Database",
]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def test_process_kill_drill_marks_interrupted_runs_resumable() -> None:
    from devcore_chaos import simulate_process_kill_recovery

    report = simulate_process_kill_recovery(run_id="run-killed", task_id="T-210")

    assert report["scenario"] == "process_kill"
    assert report["ok"] is True
    assert report["resumed_runs"] == 1
    assert report["transitions"] == [("run-killed", "start"), ("run-killed", "resume")]


def test_db_restart_drill_rolls_back_and_reconnects_cleanly() -> None:
    from devcore_chaos import simulate_db_restart_recovery

    report = simulate_db_restart_recovery()

    assert report["scenario"] == "db_restart"
    assert report["ok"] is True
    assert report["first_session"]["rolled_back"] is True
    assert report["first_session"]["closed"] is True
    assert report["second_session"]["committed"] is True
    assert report["reconnected"] is True


def test_qdrant_unavailable_drill_is_degraded_not_fatal() -> None:
    from devcore_chaos import simulate_qdrant_unavailable

    report = simulate_qdrant_unavailable(collections=["decisions", "lessons"])

    assert report["scenario"] == "qdrant_unavailable"
    assert report["ok"] is True
    assert report["status"] == "degraded"
    assert report["fatal"] is False
    assert report["retry"]["recommended"] is True
    assert report["collections"] == ["decisions", "lessons"]
