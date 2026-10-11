"""Archived v6 mission entry points must not mutate a shared JSON board."""

import os
import subprocess
from pathlib import Path

import pytest


PLATFORM = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("script,args", [
    ("Scripts/archived/mission_add.ps1", ["-Title", "Ignored"]),
    ("Scripts/archived/mission_done.ps1", []),
    ("Scripts/archived/mission_next.ps1", []),
    ("Scripts/archived/mission_pause.ps1", []),
    ("Scripts/archived/mission_skip.ps1", []),
    ("Scripts/archived/mission_status.ps1", []),
    ("download/mission_next.ps1", []),
])
def test_archived_mission_command_refuses_shared_json(tmp_path, script, args):
    data = tmp_path / "data"
    memory = data / "Memory"
    memory.mkdir(parents=True)
    board = memory / "missions.json"
    original = b'{"project":"legacy","missions":[{"id":"M-01","status":"active"}]}'
    board.write_bytes(original)
    local = tmp_path / "local"
    env = os.environ.copy()
    env.update({"DEVCORE_DATA_ROOT": str(data), "DEVCORE_LOCAL_ROOT": str(local),
                "DEVCORE_PLATFORM_ROOT": str(PLATFORM)})
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy",
         "Bypass", "-File", str(PLATFORM / script), *args],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=20,
    )
    assert result.returncode != 0
    assert "JSON global desactive" in result.stderr
    assert board.read_bytes() == original
    assert sorted(path.name for path in memory.iterdir()) == ["missions.json"]
    assert not local.exists()


@pytest.mark.parametrize("entry_point", ["session_start.ps1", "session_start_v2.ps1"])
@pytest.mark.parametrize("exit_code", [0, 7])
def test_download_session_start_delegates_without_global_flag(tmp_path, entry_point, exit_code):
    platform = tmp_path / "platform"
    scripts = platform / "Scripts"
    download = platform / "download"
    scripts.mkdir(parents=True)
    download.mkdir()
    source = PLATFORM / "download" / entry_point
    (download / source.name).write_bytes(source.read_bytes())
    (scripts / "session_start.ps1").write_text(
        f'Set-Content -LiteralPath $env:DCC_CALLS -Value "current-session"\nexit {exit_code}\n',
        encoding="utf-8",
    )
    data = tmp_path / "data"
    memory = data / "Memory"
    memory.mkdir(parents=True)
    mission_board = memory / "missions.json"
    original = b'{"project":"legacy","missions":[{"id":"M-01","status":"active"}]}'
    mission_board.write_bytes(original)
    local = tmp_path / "local"
    calls = tmp_path / "calls.txt"
    env = os.environ.copy()
    env.update({"DEVCORE_PLATFORM_ROOT": str(platform),
                "DEVCORE_DATA_ROOT": str(data), "DEVCORE_LOCAL_ROOT": str(local),
                "DCC_CALLS": str(calls)})
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy",
         "Bypass", "-File", str(download / source.name)],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == exit_code
    assert calls.read_text(encoding="utf-8").strip() == "current-session"
    assert mission_board.read_bytes() == original
    assert sorted(path.name for path in memory.iterdir()) == ["missions.json"]
    assert not local.exists()


def test_legacy_path_rewriter_is_disabled_without_modifying_scripts(tmp_path):
    scripts = tmp_path / "Scripts"
    auto = scripts / "Auto"
    auto.mkdir(parents=True)
    source = PLATFORM / "Scripts" / "Auto" / "update_paths.ps1"
    entry_point = auto / source.name
    entry_point.write_bytes(source.read_bytes())
    victim = scripts / "legacy.ps1"
    original = b'$tasks = "$DEV_CORE_DATA\\Memory\\tasks.json"\r\n'
    victim.write_bytes(original)
    env = os.environ.copy()
    env.update({
        "DEVCORE_PLATFORM_ROOT": str(tmp_path),
        "DEVCORE_DATA_ROOT": str(tmp_path / "data"),
        "DEVCORE_LOCAL_ROOT": str(tmp_path / "local"),
    })

    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy",
         "Bypass", "-File", str(entry_point)],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=20,
    )

    assert result.returncode == 2
    assert "Legacy source rewriter disabled" in result.stderr
    assert victim.read_bytes() == original
    assert not (tmp_path / "data").exists()
    assert not (tmp_path / "local").exists()


def test_legacy_in_place_migration_is_disabled_without_moving_board(tmp_path):
    data = tmp_path / "data"
    memory = data / "Memory"
    memory.mkdir(parents=True)
    board = memory / "tasks.json"
    original = b'{"project":"alpha","tasks":[{"id":"T-01"}]}'
    board.write_bytes(original)
    source = PLATFORM / "Scripts" / "Auto" / "migrate_multiproject.ps1"
    env = os.environ.copy()
    env.update({
        "DEVCORE_PLATFORM_ROOT": str(PLATFORM),
        "DEVCORE_DATA_ROOT": str(data),
        "DEVCORE_LOCAL_ROOT": str(tmp_path / "local"),
    })

    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy",
         "Bypass", "-File", str(source)],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=20,
    )

    assert result.returncode == 2
    assert "Legacy in-place migration disabled" in result.stderr
    assert board.read_bytes() == original
    assert sorted(path.name for path in memory.iterdir()) == ["tasks.json"]
    assert not (memory / "alpha").exists()
    assert not (tmp_path / "local").exists()


@pytest.mark.parametrize("exit_code", [0, 9])
def test_download_diagnose_delegates_without_reading_mission_board(tmp_path, exit_code):
    platform = tmp_path / "platform"
    scripts = platform / "Scripts"
    download = platform / "download"
    scripts.mkdir(parents=True)
    download.mkdir()
    source = PLATFORM / "download" / "diagnose.ps1"
    (download / source.name).write_bytes(source.read_bytes())
    calls = tmp_path / "diagnose-calls.txt"
    (scripts / "diagnose.ps1").write_text(
        f'Set-Content -LiteralPath $env:DCC_CALLS -Value ($args -join "|")\nexit {exit_code}\n',
        encoding="utf-8",
    )
    data = tmp_path / "data"
    memory = data / "Memory"
    memory.mkdir(parents=True)
    board = memory / "missions.json"
    original = b'{"project":"foreign","missions":[{"id":"M-01","status":"active"}]}'
    board.write_bytes(original)
    env = os.environ.copy()
    env.update({
        "DEVCORE_PLATFORM_ROOT": str(platform),
        "DEVCORE_DATA_ROOT": str(data),
        "DEVCORE_LOCAL_ROOT": str(tmp_path / "local"),
        "DCC_CALLS": str(calls),
    })

    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy",
         "Bypass", "-File", str(download / source.name), "-Gate", "-Json"],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=20,
    )

    assert result.returncode == exit_code
    assert calls.read_text(encoding="utf-8").strip() == "-Gate|-Json"
    assert board.read_bytes() == original
    assert sorted(path.name for path in memory.iterdir()) == ["missions.json"]
    assert not (tmp_path / "local").exists()


@pytest.mark.parametrize("exit_code", [0, 9])
def test_dc_v2_check_propagates_diagnostic_status(tmp_path, exit_code):
    platform = tmp_path / "platform"
    scripts = platform / "Scripts"
    download = platform / "download"
    scripts.mkdir(parents=True)
    download.mkdir()
    source = PLATFORM / "download" / "dc_v2.ps1"
    (download / source.name).write_bytes(source.read_bytes())
    calls = tmp_path / "dc-check-calls.txt"
    (scripts / "diagnose.ps1").write_text(
        f'Set-Content -LiteralPath $env:DCC_CALLS -Value "diagnose"\nexit {exit_code}\n',
        encoding="utf-8",
    )
    env = os.environ.copy()
    env.update({
        "DEVCORE_PLATFORM_ROOT": str(platform),
        "DEVCORE_DATA_ROOT": str(tmp_path / "data"),
        "DEVCORE_LOCAL_ROOT": str(tmp_path / "local"),
        "DCC_CALLS": str(calls),
    })

    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy",
         "Bypass", "-File", str(download / source.name), "check"],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=20,
    )

    assert result.returncode == exit_code
    assert calls.read_text(encoding="utf-8").strip() == "diagnose"
    assert not (tmp_path / "data").exists()
    assert not (tmp_path / "local").exists()


@pytest.mark.parametrize("command,stub,expected", [
    (("launch",), "launch.ps1", "--project|alpha"),
    (("endday",), "endday.ps1", "--project|alpha"),
    (("ask", "explain"), "ask.ps1", "alpha|explain"),
])
def test_dc_v2_lifecycle_requires_and_forwards_project(tmp_path, command, stub, expected):
    platform = tmp_path / "platform"
    scripts = platform / "Scripts"
    download = platform / "download"
    scripts.mkdir(parents=True)
    download.mkdir()
    (download / "dc_v2.ps1").write_bytes((PLATFORM / "download" / "dc_v2.ps1").read_bytes())
    calls = tmp_path / "calls.txt"
    if stub == "ask.ps1":
        body = 'param([string]$PromptFr,[string]$Project)\nSet-Content -LiteralPath $env:DCC_CALLS -Value "$Project|$PromptFr"\nexit 7\n'
    else:
        body = 'Set-Content -LiteralPath $env:DCC_CALLS -Value ($args -join "|")\nexit 7\n'
    (scripts / stub).write_text(body, encoding="utf-8")
    env = os.environ.copy()
    env.update({
        "DEVCORE_PLATFORM_ROOT": str(platform),
        "DEVCORE_LOCAL_ROOT": str(tmp_path / "local"),
        "DEVCORE_DATA_ROOT": str(tmp_path / "data"),
        "DCC_CALLS": str(calls),
    })
    base = ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy",
            "Bypass", "-File", str(download / "dc_v2.ps1")]

    missing = subprocess.run([*base, *command], cwd=tmp_path, env=env,
                             capture_output=True, text=True, timeout=20)
    assert missing.returncode == 2
    assert not calls.exists()
    supplied = subprocess.run([*base, "-Project", "alpha", *command],
                              cwd=tmp_path, env=env, capture_output=True,
                              text=True, timeout=20)
    assert supplied.returncode == 7
    assert calls.read_text(encoding="utf-8").strip() == expected
    assert not (tmp_path / "local").exists()
    assert not (tmp_path / "data").exists()


def test_dc_v2_weekly_propagates_shared_maintenance_refusal(tmp_path):
    platform = tmp_path / "platform"
    scripts = platform / "Scripts"
    auto = scripts / "Auto"
    download = platform / "download"
    auto.mkdir(parents=True)
    download.mkdir()
    (download / "dc_v2.ps1").write_bytes((PLATFORM / "download" / "dc_v2.ps1").read_bytes())
    (auto / "weekly_maintenance.ps1").write_text('exit 4\n', encoding="utf-8")
    env = os.environ.copy()
    env.update({
        "DEVCORE_PLATFORM_ROOT": str(platform),
        "DEVCORE_LOCAL_ROOT": str(tmp_path / "local"),
        "DEVCORE_DATA_ROOT": str(tmp_path / "data"),
    })

    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy",
         "Bypass", "-File", str(download / "dc_v2.ps1"), "weekly"],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=20,
    )

    assert result.returncode == 4
    assert not (tmp_path / "local").exists()
    assert not (tmp_path / "data").exists()
