import os
import subprocess
import sys
from pathlib import Path
import pytest

from devcore_engine.services.tasks import TaskService


PLATFORM_ROOT = Path(__file__).resolve().parents[1]


def _run(script, env, *args):
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
         "-File", str(PLATFORM_ROOT / "Scripts" / script), *args],
        cwd=PLATFORM_ROOT, env=env, capture_output=True, text=True,
    )


def test_edit_pause_skip_adapters_are_project_scoped_and_json_free(tmp_path, monkeypatch):
    local_root = tmp_path / "local"
    shared_root = tmp_path / "shared"
    local_root.mkdir()
    shared_root.mkdir()
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(local_root))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(shared_root))
    service = TaskService()
    try:
        service.add_task("Alpha one", project_id="alpha", steps=3)
        service.add_task("Alpha two", project_id="alpha")
        service.add_task("Beta one", project_id="beta", steps=3)
        service.next_task("alpha")
        service.next_task("beta")
    finally:
        service.conn.close()

    env = os.environ.copy()
    env["DEVCORE_PLATFORM_ROOT"] = str(PLATFORM_ROOT)
    env["DEVCORE_PYTHON"] = sys.executable

    edit = _run("task_edit.ps1", env, "-Project", "alpha", "-Id", "T-01",
                "-Title", "Edited alpha", "-Steps", "4")
    assert edit.returncode == 0, edit.stderr
    stale_pause = _run("task_pause.ps1", env, "-Project", "beta", "-Id", "T-01",
                       "-ExpectedVersion", "1")
    assert stale_pause.returncode != 0
    assert "stale task version" in stale_pause.stderr
    pause = _run("task_pause.ps1", env, "-Project", "beta", "-Id", "T-01")
    assert pause.returncode == 0, pause.stderr
    skip = _run("task_skip.ps1", env, "-Project", "alpha", "-Id", "T-01",
                "-Reason", "Dependency blocked")
    assert skip.returncode == 0, skip.stderr

    resume = _run("task_resume.ps1", env, "-Project", "beta", "-Id", "T-01")
    assert resume.returncode == 0, resume.stderr

    service = TaskService()
    try:
        assert service.get_task("T-01", "alpha")["title"] == "Edited alpha"
        assert service.get_task("T-01", "alpha")["steps_total"] == 4
        assert service.get_task("T-01", "alpha")["status"] == "skipped"
        assert service.get_task("T-02", "alpha")["status"] == "in_progress"
        assert service.get_task("T-01", "beta")["status"] == "in_progress"
        assert service.get_task("T-01", "beta")["title"] == "beta one"
    finally:
        service.conn.close()
    assert not list(shared_root.rglob("tasks.json"))


def test_resume_rejects_second_active_task(tmp_path):
    service = TaskService(tmp_path / "local")
    try:
        service.add_task("One", project_id="alpha")
        service.add_task("Two", project_id="alpha")
        service.next_task("alpha")
        service.pause_task("T-01", project_id="alpha")
        service.next_task("alpha")
        try:
            service.resume_task("T-01", project_id="alpha")
        except ValueError as exc:
            assert "already active" in str(exc)
        else:
            raise AssertionError("resume must reject a second active task")
        assert service.get_task("T-01", "alpha")["status"] == "paused"
        assert service.get_task("T-02", "alpha")["status"] == "in_progress"
    finally:
        service.conn.close()


def test_task_step_adapter_requires_project_and_uses_transactional_service(tmp_path, monkeypatch):
    local_root = tmp_path / "local"
    shared_root = tmp_path / "shared"
    local_root.mkdir()
    shared_root.mkdir()
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(local_root))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(shared_root))

    env = os.environ.copy()
    env["DEVCORE_PLATFORM_ROOT"] = str(PLATFORM_ROOT)
    env["DEVCORE_PYTHON"] = sys.executable
    missing = _run("task_step_done.ps1", env, "-TaskId", "T-01")
    assert missing.returncode != 0
    assert not (local_root / "devcore.db").exists()

    service = TaskService()
    try:
        service.add_task("Alpha", project_id="alpha", steps=2)
        service.add_task("Beta", project_id="beta", steps=2)
        service.next_task("alpha")
        service.next_task("beta")
        alpha_version = service.get_task("T-01", "alpha")["version"]
    finally:
        service.conn.close()

    step = _run("task_step_done.ps1", env, "-Project", "alpha", "-TaskId", "T-01",
                "-ExpectedVersion", str(alpha_version))
    assert step.returncode == 0, step.stderr
    stale = _run("task_step_done.ps1", env, "-Project", "alpha", "-TaskId", "T-01",
                  "-ExpectedVersion", str(alpha_version))
    assert stale.returncode != 0
    assert "stale task version" in stale.stderr

    service = TaskService()
    try:
        assert service.get_task("T-01", "alpha")["steps_done"] == 1
        assert service.get_task("T-01", "beta")["steps_done"] == 0
    finally:
        service.conn.close()
    assert not list(shared_root.rglob("tasks.json"))


@pytest.mark.parametrize("script", ["task_done.ps1", "../download/task_done.ps1"])
def test_task_done_adapter_requires_project_and_preserves_other_project(tmp_path, monkeypatch, script):
    local_root = tmp_path / "local"
    shared_root = tmp_path / "shared"
    local_root.mkdir()
    shared_root.mkdir()
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(local_root))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(shared_root))
    env = os.environ.copy()
    env["DEVCORE_PLATFORM_ROOT"] = str(PLATFORM_ROOT)
    env["DEVCORE_PYTHON"] = sys.executable
    env["DEVCORE_ACTIVE_PROJECT_NAME"] = "beta"

    missing = _run(script, env, "-TaskId", "T-01", "-Force")
    assert missing.returncode != 0
    assert not (local_root / "devcore.db").exists()

    service = TaskService()
    try:
        service.add_task("Alpha", project_id="alpha")
        service.add_task("Beta", project_id="beta")
        service.next_task("alpha")
        service.next_task("beta")
        alpha_version = service.get_task("T-01", "alpha")["version"]
    finally:
        service.conn.close()

    stale = _run(script, env, "-Project", "alpha", "-TaskId", "T-01",
                 "-ExpectedVersion", str(alpha_version - 1), "-Force")
    assert stale.returncode != 0
    assert "stale task version" in stale.stderr
    completed = _run(script, env, "-Project", "alpha", "-TaskId", "T-01",
                     "-ExpectedVersion", str(alpha_version), "-Force")
    assert completed.returncode == 0, completed.stderr

    service = TaskService()
    try:
        assert service.get_task("T-01", "alpha")["status"] == "done"
        assert service.get_task("T-01", "beta")["status"] == "in_progress"
    finally:
        service.conn.close()
    assert not list(shared_root.rglob("tasks.json"))


@pytest.mark.parametrize("command_words", [("task", "done"), ("mission", "validee")])
def test_dc_v2_completion_forwards_explicit_project_and_version(tmp_path, monkeypatch, command_words):
    local_root = tmp_path / "local"
    shared_root = tmp_path / "shared"
    local_root.mkdir()
    shared_root.mkdir()
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(local_root))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(shared_root))
    env = os.environ.copy()
    env["DEVCORE_PLATFORM_ROOT"] = str(PLATFORM_ROOT)
    env["DEVCORE_PYTHON"] = sys.executable
    env["DEVCORE_ACTIVE_PROJECT_NAME"] = "beta"

    missing = _run("../download/dc_v2.ps1", env, *command_words)
    assert missing.returncode != 0
    assert not (local_root / "devcore.db").exists()

    service = TaskService()
    try:
        service.add_task("Alpha", project_id="alpha")
        service.add_task("Beta", project_id="beta")
        service.next_task("alpha")
        service.next_task("beta")
        version = service.get_task("T-01", "alpha")["version"]
    finally:
        service.conn.close()

    stale = _run("../download/dc_v2.ps1", env, "-Project", "alpha", "-TaskId", "T-01",
                 "-ExpectedVersion", str(version - 1), *command_words)
    assert stale.returncode != 0
    assert "stale task version" in stale.stderr
    completed = _run("../download/dc_v2.ps1", env, "-Project", "alpha", "-TaskId", "T-01",
                     "-ExpectedVersion", str(version), *command_words)
    assert completed.returncode == 0, completed.stderr
    service = TaskService()
    try:
        assert service.get_task("T-01", "alpha")["status"] == "done"
        assert service.get_task("T-01", "beta")["status"] == "in_progress"
    finally:
        service.conn.close()
    assert not list(shared_root.rglob("tasks.json"))


def test_download_task_adapters_and_dc_v2_share_scoped_service(tmp_path, monkeypatch):
    local_root = tmp_path / "local"
    shared_root = tmp_path / "shared"
    local_root.mkdir()
    shared_root.mkdir()
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(local_root))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(shared_root))
    env = os.environ.copy()
    env["DEVCORE_PLATFORM_ROOT"] = str(PLATFORM_ROOT)
    env["DEVCORE_PYTHON"] = sys.executable
    env["DEVCORE_ACTIVE_PROJECT_NAME"] = "beta"

    for script, args in (
        ("../download/task_add.ps1", ("-Title", "missing")),
        ("../download/task_next.ps1", ()),
        ("../download/task_status.ps1", ()),
        ("../download/dc_v2.ps1", ("new", "task", "missing")),
    ):
        assert _run(script, env, *args).returncode != 0
    assert not (local_root / "devcore.db").exists()

    for project in ("alpha", "beta"):
        added = _run("../download/task_add.ps1", env, "-Project", project,
                     "-Title", f"{project} first")
        assert added.returncode == 0, added.stderr
    dependent = _run("../download/task_add.ps1", env, "-Project", "alpha",
                     "-Title", "alpha dependent", "-DependsOn", "T-01")
    assert dependent.returncode == 0, dependent.stderr
    via_alias = _run("../download/dc_v2.ps1", env, "-Project", "alpha",
                     "new", "task", "alpha extra", "-coding")
    assert via_alias.returncode == 0, via_alias.stderr
    selected = _run("../download/dc_v2.ps1", env, "-Project", "alpha", "next", "task")
    assert selected.returncode == 0, selected.stderr
    beta_selected = _run("../download/task_next.ps1", env, "-Project", "beta")
    assert beta_selected.returncode == 0, beta_selected.stderr
    status = _run("../download/task_status.ps1", env, "-Project", "alpha")
    assert status.returncode == 0, status.stderr
    assert "TASK BOARD (alpha)" in status.stdout
    assert "beta first" not in status.stdout

    service = TaskService()
    try:
        assert service.get_task("T-01", "alpha")["status"] == "in_progress"
        assert service.get_task("T-02", "alpha")["depends_on"] == "T-01"
        assert service.get_task("T-03", "alpha")["title"] == "alpha extra"
        assert service.get_task("T-01", "beta")["status"] == "in_progress"
    finally:
        service.conn.close()
    alias_status = _run("../download/dc_v2.ps1", env, "-Project", "alpha", "task", "status")
    assert alias_status.returncode == 0, alias_status.stderr
    assert "TASK BOARD (alpha)" in alias_status.stdout
    paused = _run("../download/dc_v2.ps1", env, "-Project", "beta", "-TaskId", "T-01",
                  "task", "pause")
    assert paused.returncode == 0, paused.stderr
    skipped = _run("../download/dc_v2.ps1", env, "-Project", "alpha", "-TaskId", "T-01",
                   "task", "skip")
    assert skipped.returncode == 0, skipped.stderr
    service = TaskService()
    try:
        assert service.get_task("T-01", "beta")["status"] == "paused"
        assert service.get_task("T-01", "alpha")["status"] == "skipped"
    finally:
        service.conn.close()
    assert not list(shared_root.rglob("tasks.json"))


def test_edit_rejects_invalid_steps_and_missing_project(tmp_path, monkeypatch):
    local_root = tmp_path / "local"
    shared_root = tmp_path / "shared"
    local_root.mkdir()
    shared_root.mkdir()
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(local_root))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(shared_root))
    service = TaskService()
    try:
        service.add_task("Alpha", project_id="alpha", steps=3)
        service.next_task("alpha")
        service.step_task("T-01", step_number=2, project_id="alpha")
    finally:
        service.conn.close()
    env = os.environ.copy()
    env["DEVCORE_PLATFORM_ROOT"] = str(PLATFORM_ROOT)
    env["DEVCORE_PYTHON"] = sys.executable

    bad_steps = _run("task_edit.ps1", env, "-Project", "alpha", "-Id", "T-01", "-Steps", "1")
    assert bad_steps.returncode != 0
    missing_project = _run("task_pause.ps1", env, "-Id", "T-01")
    assert missing_project.returncode != 0

    service = TaskService()
    try:
        assert service.get_task("T-01", "alpha")["steps_total"] == 3
        assert service.get_task("T-01", "alpha")["status"] == "in_progress"
    finally:
        service.conn.close()
