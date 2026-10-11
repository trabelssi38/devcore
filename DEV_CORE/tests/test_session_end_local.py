"""Session end keeps routine output local and passes an explicit project."""

import hashlib
import os
import subprocess
from pathlib import Path

import pytest


SOURCE = Path(__file__).resolve().parents[1] / "Scripts" / "session_end.ps1"


def test_session_end_is_project_scoped_without_legacy_maintenance(tmp_path):
    platform = tmp_path / "platform"
    scripts = platform / "Scripts"
    scripts.mkdir(parents=True)
    (scripts / "session_end.ps1").write_bytes(SOURCE.read_bytes())
    (scripts / "platform_version.ps1").write_text(
        "function Get-DevCorePlatformInfo { [pscustomobject]@{ title = 'TEST' } }",
        encoding="utf-8",
    )
    (scripts / "gen_metrics.ps1").write_text(
        'param([string]$Project)\nAdd-Content $env:DCC_CALLS "metrics:$Project"', encoding="utf-8",
    )
    (scripts / "task_scan.ps1").write_text(
        'param([string]$Project,[string]$RepoPath)\nAdd-Content $env:DCC_CALLS "scan:$Project|$RepoPath"',
        encoding="utf-8",
    )
    (scripts / "task_sync.ps1").write_text(
        'Add-Content $env:DCC_CALLS "sync"', encoding="utf-8",
    )
    for name in ("qdrant_sync", "obsidian_sync", "endday_check"):
        (scripts / f"{name}.ps1").write_text(
            f'Add-Content $env:DCC_CALLS "legacy:{name}"', encoding="utf-8",
        )

    local = tmp_path / "local"
    shared = tmp_path / "shared"
    local.mkdir()
    shared.mkdir()
    legacy = shared / "unchanged.txt"
    legacy.write_text("shared state", encoding="utf-8")
    calls = tmp_path / "calls.txt"
    env = os.environ.copy()
    env.update({
        "DEVCORE_PLATFORM_ROOT": str(platform),
        "DEVCORE_LOCAL_ROOT": str(local),
        "DEVCORE_DATA_ROOT": str(shared),
        "DCC_CALLS": str(calls),
        "DEVCORE_ACTIVE_PROJECT_NAME": "wrong-project",
    })
    for project in ("alpha", "beta"):
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-File", str(scripts / "session_end.ps1"), "-Project", project,
             "-RepoPath", str(tmp_path / "repo")],
            cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30,
            encoding="utf-8", errors="replace",
        )
        assert result.returncode == 0, result.stdout + result.stderr
        key = hashlib.sha256(project.encode()).hexdigest()[:16].upper()
        assert list((local / "Logs" / "scripts" / key).glob("session_end_*.log"))

    records = calls.read_text(encoding="utf-8").splitlines()
    assert records == [
        "metrics:alpha", f"scan:alpha|{tmp_path / 'repo'}", "sync",
        "metrics:beta", f"scan:beta|{tmp_path / 'repo'}", "sync",
    ]
    assert legacy.read_text(encoding="utf-8") == "shared state"
    assert sorted(path.name for path in shared.iterdir()) == ["unchanged.txt"]


@pytest.mark.parametrize("failed_step,expected_calls", [
    ("gen_metrics", ["metrics"]),
    ("task_scan", ["metrics", "scan"]),
    ("task_sync", ["metrics", "scan", "sync"]),
])
def test_session_end_stops_and_reports_failed_step(tmp_path, failed_step, expected_calls):
    platform = tmp_path / "platform"
    scripts = platform / "Scripts"
    scripts.mkdir(parents=True)
    (scripts / "session_end.ps1").write_bytes(SOURCE.read_bytes())
    (scripts / "platform_version.ps1").write_text(
        "function Get-DevCorePlatformInfo { [pscustomobject]@{ title = 'TEST' } }",
        encoding="utf-8",
    )
    for name, label in (("gen_metrics", "metrics"), ("task_scan", "scan"),
                        ("task_sync", "sync")):
        script = f'Add-Content $env:DCC_CALLS "{label}"\n'
        script += "exit 7\n" if name == failed_step else "exit 0\n"
        (scripts / f"{name}.ps1").write_text(script, encoding="utf-8")
    local = tmp_path / "local"
    data = tmp_path / "data"
    local.mkdir()
    data.mkdir()
    calls = tmp_path / "calls.txt"
    env = os.environ.copy()
    env.update({"DEVCORE_PLATFORM_ROOT": str(platform),
                "DEVCORE_LOCAL_ROOT": str(local), "DEVCORE_DATA_ROOT": str(data),
                "DCC_CALLS": str(calls)})
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy",
         "Bypass", "-File", str(scripts / "session_end.ps1"), "-Project", "alpha",
         "-RepoPath", str(tmp_path / "repo")],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30,
        encoding="utf-8", errors="replace",
    )
    assert result.returncode != 0
    assert "Session end complete" not in result.stdout
    assert calls.read_text(encoding="utf-8").splitlines() == expected_calls
    assert not list(data.iterdir())


def test_session_end_rejects_invalid_project_before_writing(tmp_path):
    platform = tmp_path / "platform"
    scripts = platform / "Scripts"
    scripts.mkdir(parents=True)
    (scripts / "session_end.ps1").write_bytes(SOURCE.read_bytes())
    (scripts / "platform_version.ps1").write_text("", encoding="utf-8")
    local = tmp_path / "local"
    data = tmp_path / "data"
    env = os.environ.copy()
    env.update({"DEVCORE_PLATFORM_ROOT": str(platform),
                "DEVCORE_LOCAL_ROOT": str(local), "DEVCORE_DATA_ROOT": str(data)})
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy",
         "Bypass", "-File", str(scripts / "session_end.ps1"), "-Project", "../beta"],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30,
        encoding="utf-8", errors="replace",
    )
    assert result.returncode != 0
    assert not local.exists()
    assert not data.exists()


@pytest.mark.parametrize("failed_step", ["qdrant_sync", "obsidian_sync", "endday_check"])
def test_session_end_optional_maintenance_failure_is_reported(tmp_path, failed_step):
    platform = tmp_path / "platform"
    scripts = platform / "Scripts"
    scripts.mkdir(parents=True)
    (scripts / "session_end.ps1").write_bytes(SOURCE.read_bytes())
    (scripts / "platform_version.ps1").write_text(
        "function Get-DevCorePlatformInfo { [pscustomobject]@{ title = 'TEST' } }",
        encoding="utf-8",
    )
    for name in ("gen_metrics", "task_scan", "task_sync", "qdrant_sync",
                 "obsidian_sync", "endday_check"):
        script = f'Add-Content $env:DCC_CALLS "{name}"\n'
        script += "exit 7\n" if name == failed_step else "exit 0\n"
        (scripts / f"{name}.ps1").write_text(script, encoding="utf-8")
    local = tmp_path / "local"
    data = tmp_path / "data"
    local.mkdir()
    data.mkdir()
    calls = tmp_path / "calls.txt"
    env = os.environ.copy()
    env.update({"DEVCORE_PLATFORM_ROOT": str(platform),
                "DEVCORE_LOCAL_ROOT": str(local), "DEVCORE_DATA_ROOT": str(data),
                "DCC_CALLS": str(calls)})
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy",
         "Bypass", "-File", str(scripts / "session_end.ps1"), "-Project", "alpha",
         "-RepoPath", str(tmp_path / "repo"), "-RunLegacyGlobalMaintenance"],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30,
        encoding="utf-8", errors="replace",
    )
    assert result.returncode != 0
    assert "Session end complete" not in result.stdout
    order = ("gen_metrics", "task_scan", "task_sync", "qdrant_sync",
             "obsidian_sync", "endday_check")
    assert calls.read_text(encoding="utf-8").splitlines() == list(order[:order.index(failed_step) + 1])
    assert not list(data.iterdir())
