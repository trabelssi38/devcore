import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from devcore_engine.services.tasks import TaskService


PLATFORM_ROOT = Path(__file__).resolve().parents[1]


def test_cli_and_powershell_step_use_project_scoped_sqlite(tmp_path, monkeypatch):
    local_root = tmp_path / "local"
    shared_root = tmp_path / "shared"
    local_root.mkdir()
    shared_root.mkdir()
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(local_root))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(shared_root))
    service = TaskService()
    try:
        service.add_task("Alpha", project_id="alpha", steps=3)
        service.add_task("Beta", project_id="beta", steps=3)
        service.next_task("alpha")
        service.next_task("beta")
    finally:
        service.conn.close()

    env = os.environ.copy()
    env["DEVCORE_PLATFORM_ROOT"] = str(PLATFORM_ROOT)
    env["DEVCORE_PYTHON"] = sys.executable
    command = [sys.executable, "-m", "devcore_engine.cli", "task", "step", "T-01", "--project", "alpha", "--json"]
    result = subprocess.run(command, cwd=PLATFORM_ROOT, env=env, capture_output=True, text=True, check=True)
    assert json.loads(result.stdout)["task"]["steps_done"] == 1

    script = PLATFORM_ROOT / "Scripts" / "task_step_done.ps1"
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(script),
         "-Project", "alpha", "-TaskId", "T-01", "-StepNumber", "3"],
        cwd=PLATFORM_ROOT, env=env, capture_output=True, text=True, check=True,
    )
    assert "3/3" in result.stdout

    service = TaskService()
    try:
        assert service.get_task("T-01", "alpha")["status"] == "done"
        assert service.get_task("T-01", "beta")["steps_done"] == 0
    finally:
        service.conn.close()
    assert not (shared_root / "Memory" / "alpha" / "tasks.json").exists()


def test_concurrent_step_increments_are_not_lost(tmp_path):
    db_root = tmp_path / "local"
    service = TaskService(db_root)
    try:
        service.add_task("Concurrent", project_id="alpha", steps=8)
        service.next_task("alpha")
    finally:
        service.conn.close()

    def advance(_):
        worker = TaskService(db_root)
        try:
            worker.step_task("T-01", project_id="alpha")
        finally:
            worker.conn.close()

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(advance, range(8)))

    service = TaskService(db_root)
    try:
        task = service.get_task("T-01", "alpha")
        assert (task["steps_done"], task["status"]) == (8, "done")
    finally:
        service.conn.close()
