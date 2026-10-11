import json
import os
import subprocess
import sys
from pathlib import Path

from devcore_engine.services.tasks import TaskService


PLATFORM_ROOT = Path(__file__).resolve().parents[1]


def test_ask_uses_selected_project_and_active_sql_task(tmp_path, monkeypatch):
    local_root = tmp_path / "local"
    shared_root = tmp_path / "shared"
    beta_cwd = tmp_path / "beta"
    for path in (local_root, shared_root, beta_cwd):
        path.mkdir()
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(local_root))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(shared_root))
    service = TaskService()
    try:
        service.add_task("Alpha current", project_id="alpha")
        service.add_task("Beta old", project_id="beta")
        service.complete_task("T-01", project_id="beta")
        service.add_task("Beta current", project_id="beta")
        service.next_task("alpha")
        service.next_task("beta")
    finally:
        service.conn.close()
    stale = shared_root / "Memory" / "alpha" / "tasks.json"
    stale.parent.mkdir(parents=True)
    stale.write_text(json.dumps({"project": "alpha", "current_task": "T-99", "tasks": [{"id": "T-99", "status": "active"}]}))

    env = os.environ.copy()
    env["DEVCORE_PLATFORM_ROOT"] = str(PLATFORM_ROOT)
    env["DEVCORE_PYTHON"] = sys.executable
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
         str(PLATFORM_ROOT / "Scripts" / "ask.ps1"), "-PromptFr", "corrige le bug", "-Project", "alpha"],
        cwd=beta_cwd, env=env, input="n\n", capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert "mission_id: T-01" in result.stdout
    assert "Launch cancelled" in result.stdout
    assert not (local_root / "Sessions" / "hf_alpha_T-01").exists()
    assert not (local_root / "Logs" / "router" / "prepare-events.jsonl").exists()

    confirmed = subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
         str(PLATFORM_ROOT / "Scripts" / "ask.ps1"), "-PromptFr", "corrige le bug", "-Project", "alpha"],
        cwd=beta_cwd, env=env, input="y\n", capture_output=True, text=True, timeout=30,
    )
    assert confirmed.returncode == 0, (confirmed.stdout, confirmed.stderr)
    handoff = json.loads((local_root / "Sessions" / "hf_alpha_T-01" / "request.json").read_text())
    assert handoff["project_id"] == "alpha"
    assert handoff["mission_id"] == "T-01"
    assert not (local_root / "Sessions" / "hf_beta_T-02").exists()
    assert json.loads(stale.read_text())["current_task"] == "T-99"


def test_ask_rejects_invalid_project_before_opening_state(tmp_path):
    local = tmp_path / "local"
    data = tmp_path / "data"
    env = os.environ.copy()
    env.update({"DEVCORE_PLATFORM_ROOT": str(PLATFORM_ROOT),
                "DEVCORE_LOCAL_ROOT": str(local), "DEVCORE_DATA_ROOT": str(data)})
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy",
         "Bypass", "-File", str(PLATFORM_ROOT / "Scripts" / "ask.ps1"),
         "-PromptFr", "résume", "-Project", "../beta"],
        cwd=tmp_path, env=env, input="n\n", capture_output=True, text=True, timeout=20,
    )
    assert result.returncode != 0
    assert "Identifiant de projet invalide" in result.stderr
    assert not local.exists()
    assert not data.exists()


def test_ask_rejects_foreign_board_before_confirmation(tmp_path):
    local = tmp_path / "local"
    data = tmp_path / "data"
    fake_python = tmp_path / "fake_python.ps1"
    fake_python.write_text(
        "Write-Output '{\"project\":\"beta\",\"current_task\":\"T-01\",\"tasks\":[]}'\nexit 0\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env.update({"DEVCORE_PLATFORM_ROOT": str(PLATFORM_ROOT),
                "DEVCORE_LOCAL_ROOT": str(local), "DEVCORE_DATA_ROOT": str(data),
                "DEVCORE_PYTHON": str(fake_python)})
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy",
         "Bypass", "-File", str(PLATFORM_ROOT / "Scripts" / "ask.ps1"),
         "-PromptFr", "résume", "-Project", "alpha"],
        cwd=tmp_path, env=env, input="n\n", capture_output=True, text=True, timeout=20,
    )
    assert result.returncode != 0
    assert "Board du mauvais projet" in result.stderr
    assert "mission_id" not in result.stdout
    assert not local.exists()
    assert not data.exists()


def test_ask_rejects_foreign_board_after_confirmation(tmp_path):
    local = tmp_path / "local"
    data = tmp_path / "data"
    counter = tmp_path / "board_calls.txt"
    fake_python = tmp_path / "fake_python.ps1"
    fake_python.write_text(
        """if ($args[0] -eq '-c') {
    Write-Output '{"confirmation_text":"Confirmer ?","interpretation":{}}'
    exit 0
}
$count = if (Test-Path $env:DCC_COUNTER) { [int](Get-Content $env:DCC_COUNTER -Raw) } else { 0 }
$count++
Set-Content $env:DCC_COUNTER $count
$name = if ($count -eq 1) { 'alpha' } else { 'beta' }
Write-Output ('{"project":"' + $name + '","current_task":"T-01","tasks":[{"id":"T-01","status":"in_progress","version":1}]}')
exit 0
""",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env.update({"DEVCORE_PLATFORM_ROOT": str(PLATFORM_ROOT),
                "DEVCORE_LOCAL_ROOT": str(local), "DEVCORE_DATA_ROOT": str(data),
                "DEVCORE_PYTHON": str(fake_python), "DCC_COUNTER": str(counter)})
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
         "-File", str(PLATFORM_ROOT / "Scripts" / "ask.ps1"),
         "-PromptFr", "résume", "-Project", "alpha"],
        cwd=tmp_path, env=env, input="y\n", capture_output=True, text=True, timeout=20,
    )
    assert result.returncode != 0, result.stdout + result.stderr
    assert "Board du mauvais projet" in result.stderr
    assert "attendu alpha" in result.stderr
    assert counter.read_text(encoding="utf-8-sig").strip() == "2"
    assert not local.exists()
    assert not data.exists()


def test_ask_rejects_changed_task_version_after_confirmation(tmp_path):
    local = tmp_path / "local"
    data = tmp_path / "data"
    counter = tmp_path / "board_calls.txt"
    fake_python = tmp_path / "fake_python.ps1"
    fake_python.write_text(
        """if ($args[0] -eq '-c') {
    Write-Output '{"confirmation_text":"Confirmer ?","interpretation":{}}'
    exit 0
}
$count = if (Test-Path $env:DCC_COUNTER) { [int](Get-Content $env:DCC_COUNTER -Raw) } else { 0 }
$count++
Set-Content $env:DCC_COUNTER $count
Write-Output ('{"project":"alpha","current_task":"T-01","tasks":[{"id":"T-01","status":"in_progress","version":' + $count + '}]}')
exit 0
""",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env.update({"DEVCORE_PLATFORM_ROOT": str(PLATFORM_ROOT),
                "DEVCORE_LOCAL_ROOT": str(local), "DEVCORE_DATA_ROOT": str(data),
                "DEVCORE_PYTHON": str(fake_python), "DCC_COUNTER": str(counter)})
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
         "-File", str(PLATFORM_ROOT / "Scripts" / "ask.ps1"),
         "-PromptFr", "résume", "-Project", "alpha"],
        cwd=tmp_path, env=env, input="y\n", capture_output=True, text=True, timeout=20,
    )
    assert result.returncode != 0, result.stdout + result.stderr
    assert "version de la" in result.stderr
    assert counter.read_text(encoding="utf-8-sig").strip() == "2"
    assert not local.exists()
    assert not data.exists()
