"""Maintenance excludes participating launches; fixtures only."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

PS_EXE = shutil.which("pwsh") or shutil.which("powershell") or "powershell"

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Scheduler'))
from service_control import control, launch_guard, services_paused, paused_path
from devcore_engine.infra import system_watcher


def watcher(root):
    obj = system_watcher.SystemWatcher.__new__(system_watcher.SystemWatcher)
    obj.local_root = root
    obj.log = lambda *a: None
    return obj


def test_pause_blocks_new_watcher_and_full_audit(tmp_path, monkeypatch):
    assert control(tmp_path, tmp_path / 'data', tmp_path / 'platform', 'pause')['processes_stopped'] is False
    monkeypatch.setattr(system_watcher.subprocess, 'Popen', lambda *a, **k: pytest.fail('No launch'))
    monkeypatch.setattr(system_watcher, 'check_port', lambda *a, **k: pytest.fail('No probe'))
    obj = watcher(tmp_path)
    assert not obj.check_and_heal_service('fixture', '127.0.0.1', 1234, ['fixture'])
    assert not obj.ensure_scheduler_daemon()
    assert obj.audit_and_heal()['status'] == 'PAUSED'
    assert not (tmp_path / 'Runtime/service_restarts.sqlite3').exists()


def test_busy_launch_refuses_pause_without_marker(tmp_path):
    with launch_guard(tmp_path):
        with pytest.raises(OSError):
            control(tmp_path, tmp_path / 'data', tmp_path / 'platform', 'pause')
    assert not services_paused(tmp_path)


def test_pause_and_resume_profile_checked(tmp_path):
    data, platform = tmp_path / 'data', tmp_path / 'platform'
    control(tmp_path, data, platform, 'pause')
    with pytest.raises(ValueError):
        control(tmp_path, tmp_path / 'foreign', platform, 'resume')
    with launch_guard(tmp_path):
        with pytest.raises(OSError):
            control(tmp_path, data, platform, 'resume')
    assert services_paused(tmp_path)
    assert control(tmp_path, data, platform, 'resume')['processes_started'] is False
    assert not services_paused(tmp_path)


@pytest.mark.parametrize('raw', ['{', '[]', 'x' * 4097])
@pytest.mark.parametrize('action', ['pause', 'resume'])
def test_invalid_marker_preserved(tmp_path, raw, action):
    path = paused_path(tmp_path)
    path.parent.mkdir()
    path.write_text(raw)
    with pytest.raises(ValueError):
        control(tmp_path, tmp_path / 'data', tmp_path / 'platform', action)
    assert path.read_text() == raw and services_paused(tmp_path)


def test_pause_appearing_before_guard_recheck_blocks_launch(tmp_path, monkeypatch):
    from contextlib import contextmanager
    @contextmanager
    def racing_guard(root):
        control(root, root / 'data', root / 'platform', 'pause')
        yield
    monkeypatch.setattr(system_watcher, 'launch_guard', racing_guard)
    monkeypatch.setattr(system_watcher.subprocess, 'Popen', lambda *a, **k: pytest.fail('No launch'))
    assert not watcher(tmp_path).check_and_heal_service('fixture', '127.0.0.1', 1234, ['fixture'])
    assert not watcher(tmp_path).ensure_scheduler_daemon()


@pytest.mark.skipif(os.name != 'nt', reason='Windows cross-process exclusion')
def test_other_process_cannot_pause_during_launch(tmp_path):
    script = Path(__file__).resolve().parents[1] / 'Scheduler/service_control.py'
    with launch_guard(tmp_path):
        result = subprocess.run([sys.executable, '-I', str(script), '--action', 'pause',
            '--local-root', str(tmp_path), '--data-root', str(tmp_path / 'data'),
            '--platform-root', str(tmp_path / 'platform')], capture_output=True, text=True, timeout=5)
    assert result.returncode == 1 and 'error' in json.loads(result.stderr)
    assert not services_paused(tmp_path)


def test_full_stop_refuses_before_scheduler_session_or_network(tmp_path):
    platform = tmp_path / 'platform'
    scripts = platform / 'Scripts'
    scripts.mkdir(parents=True)
    (scripts / 'platform_version.ps1').write_text('''
function Get-DevCorePython { return $env:DEVCORE_PYTHON }
function Get-DevCorePlatformInfo { return @{title='fixture'} }
''')
    stub = tmp_path / 'fixture_python.ps1'
    stub.write_text('''
if ($args -contains '--action') { Write-Output '{"error":"fixture busy"}'; exit 1 }
throw 'Scheduler/session must not be called'
''')
    env = dict(os.environ, DEVCORE_PLATFORM_ROOT=str(platform), DEVCORE_PYTHON=str(stub),
        DEVCORE_LOCAL_ROOT=str(tmp_path / 'local'), DEVCORE_DATA_ROOT=str(tmp_path / 'data'))
    script = Path(__file__).resolve().parents[1] / 'Scripts/stop.ps1'
    result = subprocess.run([PS_EXE, '-NoProfile', '-File', str(script)], env=env,
        capture_output=True, text=True, timeout=8)
    assert result.returncode == 1
    assert 'Pause globale refusee' in result.stdout
    assert 'Scheduler/session must not be called' not in result.stderr
