"""Two local project sessions must not share a daily admission flag."""

import hashlib
import json
import os
import subprocess
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1] / "Scripts"


def _platform(tmp_path):
    platform = tmp_path / "platform"
    scripts = platform / "Scripts"
    scripts.mkdir(parents=True)
    for name in ("session_start.ps1", "Get-ActiveProject.ps1"):
        (scripts / name).write_bytes((SOURCE / name).read_bytes())
    python_stub = scripts / "fake_python.ps1"
    python_stub.write_text(
        "Write-Output ('{\"project\":\"' + $env:DCC_PROJECT + '\",\"tasks\":[{\"id\":\"T-01\",\"status\":\"todo\"}]}')\nexit 0\n",
        encoding="utf-8",
    )
    (scripts / "platform_version.ps1").write_text(
        f"function Get-DevCorePython {{ return '{python_stub}' }}\n",
        encoding="utf-8",
    )
    (scripts / "launch.ps1").write_text(
        'Set-Content (Join-Path $env:DCC_CALLS ("launch-" + $PID + ".txt")) $env:DCC_PROJECT\n'
        'Start-Sleep -Milliseconds 500\nexit 0\n', encoding="utf-8",
    )
    for name in ("task_next.ps1", "gen_session_context.ps1"):
        (scripts / name).write_text("exit 0\n", encoding="utf-8")
    return scripts


def _project(tmp_path, name):
    project = tmp_path / name
    marker = project / ".devcore"
    marker.mkdir(parents=True)
    (marker / "project.json").write_text(json.dumps({"name": name}), encoding="utf-8")
    return project


def _start(scripts, project, local, data, calls, name):
    env = os.environ.copy()
    env.update({"DEVCORE_PLATFORM_ROOT": str(scripts.parent),
                "DEVCORE_LOCAL_ROOT": str(local), "DEVCORE_DATA_ROOT": str(data),
                "DCC_CALLS": str(calls), "DCC_PROJECT": name})
    return subprocess.Popen(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy",
         "Bypass", "-File", str(scripts / "session_start.ps1")],
        cwd=project, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True,
    )


def _finish(process):
    stdout, stderr = process.communicate(timeout=30)
    assert process.returncode == 0, stdout + stderr


def test_two_projects_start_concurrently_with_separate_flags(tmp_path):
    scripts = _platform(tmp_path)
    calls = tmp_path / "calls"
    calls.mkdir()
    local, data = tmp_path / "local", tmp_path / "data"
    alpha, beta = _project(tmp_path, "alpha"), _project(tmp_path, "beta")
    processes = [_start(scripts, alpha, local, data, calls, "alpha"),
                 _start(scripts, beta, local, data, calls, "beta")]
    for process in processes:
        _finish(process)
    assert sorted(path.read_text(encoding="utf-8-sig").strip()
                  for path in calls.glob("launch-*.txt")) == ["alpha", "beta"]
    flags = list(local.rglob("*.flag"))
    assert len(flags) == 2
    for name in ("alpha", "beta"):
        key = hashlib.sha256(name.encode()).hexdigest()[:16].upper()
        assert any(key in str(flag) for flag in flags)
    assert not data.exists()


def test_duplicate_project_start_runs_once(tmp_path):
    scripts = _platform(tmp_path)
    calls = tmp_path / "calls"
    calls.mkdir()
    local, data = tmp_path / "local", tmp_path / "data"
    alpha = _project(tmp_path, "alpha")
    processes = [_start(scripts, alpha, local, data, calls, "alpha") for _ in range(2)]
    for process in processes:
        _finish(process)
    assert len(list(calls.glob("launch-*.txt"))) == 1
    assert len(list(local.rglob("*.flag"))) == 1
    assert not data.exists()
