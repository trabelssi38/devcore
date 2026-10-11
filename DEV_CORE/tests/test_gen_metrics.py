import csv
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from devcore_engine.services.tasks import TaskService


PLATFORM_ROOT = Path(__file__).resolve().parents[1]


def test_gen_metrics_uses_project_sql_and_local_output(tmp_path, monkeypatch):
    local_root = tmp_path / "local"
    shared_root = tmp_path / "shared"
    local_root.mkdir()
    shared_root.mkdir()
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(local_root))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(shared_root))
    service = TaskService()
    try:
        service.add_task("Alpha", project_id="alpha", steps=3)
        service.add_task("Beta", project_id="beta", steps=9)
        service.next_task("alpha")
        service.step_task("T-01", project_id="alpha")
    finally:
        service.conn.close()

    stale = shared_root / "Memory" / "alpha" / "tasks.json"
    stale.parent.mkdir(parents=True)
    stale.write_text(json.dumps({"project": "alpha", "tasks": [{"id": "T-01", "steps_done": 99, "steps_total": 99}]}))
    env = os.environ.copy()
    env["DEVCORE_PLATFORM_ROOT"] = str(PLATFORM_ROOT)
    env["DEVCORE_PYTHON"] = sys.executable
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File",
         str(PLATFORM_ROOT / "Scripts" / "gen_metrics.ps1"), "-Project", "alpha"],
        cwd=PLATFORM_ROOT, env=env, capture_output=True, text=True, check=True,
    )
    assert "1/3" in result.stdout
    files = list((local_root / "Metrics" / "alpha").glob("session_metrics_*.csv"))
    assert len(files) == 1
    with files[0].open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert rows == [{
        "date": files[0].stem.removeprefix("session_metrics_"),
        "project": "alpha",
        "active_task": "T-01",
        "tasks_count": "1",
        "steps_done": "1",
        "steps_total": "3",
        "progress_pct": "33",
    }]
    assert not (shared_root / "Metrics").exists()
    assert json.loads(stale.read_text())["tasks"][0]["steps_done"] == 99


def test_session_context_uses_sql_and_separate_local_project_paths(tmp_path, monkeypatch):
    local_root = tmp_path / "local"
    shared_root = tmp_path / "shared"
    local_root.mkdir()
    shared_root.mkdir()
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(local_root))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(shared_root))
    service = TaskService()
    try:
        service.add_task("Alpha SQL", project_id="alpha", steps=2)
        service.add_task("Beta SQL", project_id="beta", steps=4)
        service.next_task("alpha")
        service.next_task("beta")
        alpha_version = service.get_task("T-01", "alpha")["version"]
        beta_version = service.get_task("T-01", "beta")["version"]
    finally:
        service.conn.close()
    stale = shared_root / "Memory" / "alpha" / "tasks.json"
    stale.parent.mkdir(parents=True)
    stale.write_text(json.dumps({"project": "alpha", "tasks": [{"id": "T-99", "title": "Stale JSON", "status": "active"}]}))

    env = os.environ.copy()
    env["DEVCORE_PLATFORM_ROOT"] = str(PLATFORM_ROOT)
    env["DEVCORE_PYTHON"] = sys.executable
    script = PLATFORM_ROOT / "Scripts" / "gen_session_context.ps1"
    for project in ("alpha", "beta"):
        subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File",
             str(script), "-Project", project],
            cwd=PLATFORM_ROOT, env=env, capture_output=True, text=True, check=True,
        )
    alpha_key = hashlib.sha256(b"alpha").hexdigest()[:16].upper()
    beta_key = hashlib.sha256(b"beta").hexdigest()[:16].upper()
    alpha_context = (local_root / "Runtime" / "projects" / alpha_key / "session_context.txt").read_text(encoding="utf-8-sig")
    beta_context = (local_root / "Runtime" / "projects" / beta_key / "session_context.txt").read_text(encoding="utf-8-sig")
    assert "Alpha SQL".lower() in alpha_context
    assert "Stale JSON" not in alpha_context
    assert "Beta SQL".lower() in beta_context
    assert alpha_context != beta_context
    assert not (shared_root / "Logs" / "scripts" / "session_context.txt").exists()
    assert json.loads(stale.read_text())["tasks"][0]["id"] == "T-99"
    service = TaskService()
    try:
        assert service.get_task("T-01", "alpha")["version"] == alpha_version
        assert service.get_task("T-01", "beta")["version"] == beta_version
    finally:
        service.conn.close()


def test_metric_and_context_generators_reject_implicit_or_invalid_project(tmp_path):
    env = os.environ.copy()
    env.update({
        "DEVCORE_LOCAL_ROOT": str(tmp_path / "local"),
        "DEVCORE_DATA_ROOT": str(tmp_path / "data"),
        "DEVCORE_PLATFORM_ROOT": str(PLATFORM_ROOT),
        "DEVCORE_PYTHON": sys.executable,
        "DEVCORE_ACTIVE_PROJECT_NAME": "beta",
    })
    for script in ("gen_metrics.ps1", "gen_session_context.ps1"):
        for arguments in ((), ("-Project", "../beta")):
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                 "-File", str(PLATFORM_ROOT / "Scripts" / script), *arguments],
                cwd=PLATFORM_ROOT, env=env, capture_output=True, text=True, timeout=30,
            )
            assert result.returncode != 0
    assert not (tmp_path / "local").exists()
    assert not (tmp_path / "data").exists()
