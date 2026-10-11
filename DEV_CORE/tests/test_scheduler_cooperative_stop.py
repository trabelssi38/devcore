"""Cooperative shutdown uses isolated roots and preserves committed work."""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import time
import uuid

import pytest

SCHEDULER = Path(__file__).resolve().parents[1] / 'Scheduler'
sys.path.insert(0, str(SCHEDULER))
import scheduler_tick
from scheduler_contract import SchedulerJob, SchedulerJobCommand, SchedulerJobSchedule, SchedulerJobState
from scheduler_presence import adopt_ready, instance_available, instance_guard, publish_ready
from stop_scheduler import request_stop, stop_path, stop_requested
from scheduler_control import is_paused, pause, resume, pause_path

PS_EXE = shutil.which("pwsh") or shutil.which("powershell") or "powershell"


def test_finish_current_job_and_save_before_stopping(tmp_path, monkeypatch):
    scheduled = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    jobs = [SchedulerJob(id=name, name=name, timezone='UTC', policy='catch_up',
        schedule=SchedulerJobSchedule(kind='once', expr=scheduled),
        command=SchedulerJobCommand(type='python', path=name),
        state=SchedulerJobState(next_run_at=scheduled)) for name in ['first', 'second']]
    scheduler_tick.save_jobs(jobs, tmp_path / 'jobs.json')
    stopping, calls = [], []
    def execute(command):
        calls.append(command.path)
        stopping.append(True)
        return 0, '', ''
    monkeypatch.setattr(scheduler_tick, 'execute_job_command', execute)
    scheduler_tick.main_loop(tmp_path / 'scheduler.db', tmp_path / 'jobs.json',
        tmp_path / 'scheduler.lock', stop_callback=lambda: bool(stopping))
    states = scheduler_tick.load_jobs(tmp_path / 'jobs.json')
    assert calls == ['first']
    assert states[0].state.last_status == 'ok' and states[0].state.completed_count == 1
    assert states[1].state.last_run_at is None
    assert not (tmp_path / 'scheduler.lock').exists()


@pytest.mark.skipif(os.name != 'nt', reason='Windows OS identity protocol')
def test_stale_receipt_can_stop_only_verified_profile(tmp_path):
    data, platform, token = tmp_path / 'data', tmp_path / 'platform', uuid.uuid4().hex
    publish_ready(tmp_path, token, data_root=data, platform_root=platform)
    path = tmp_path / 'Scheduler/scheduler.ready.json'
    receipt = json.loads(path.read_text())
    receipt['ready_at'] = time.time() - 120
    path.write_text(json.dumps(receipt))
    with instance_guard(tmp_path):
        assert not adopt_ready(tmp_path, data, platform)
        with pytest.raises(RuntimeError):
            request_stop(tmp_path, tmp_path / 'foreign', platform)
        assert not stop_path(tmp_path, token).exists()
        result = request_stop(tmp_path, data, platform)
        assert result['stopped_confirmed'] is False and result['force'] is False
        assert stop_requested(tmp_path, token)


@pytest.mark.skipif(os.name != 'nt', reason='Windows OS identity protocol')
@pytest.mark.parametrize('field,value', [('protocol', True), ('pid', 0), ('creation_100ns', 1), ('token', '0' * 32)])
def test_foreign_or_invalid_stop_is_ignored(tmp_path, field, value):
    token = uuid.uuid4().hex
    publish_ready(tmp_path, token, data_root=tmp_path / 'data', platform_root=tmp_path / 'platform')
    with instance_guard(tmp_path):
        request_stop(tmp_path, tmp_path / 'data', tmp_path / 'platform')
    path = stop_path(tmp_path, token)
    payload = json.loads(path.read_text())
    payload[field] = value
    path.write_text(json.dumps(payload))
    assert not stop_requested(tmp_path, token)
    assert path.exists()


@pytest.mark.parametrize('raw', ['{', '[]', 'x' * 2049])
def test_malformed_or_oversize_request_ignored(tmp_path, raw):
    token = uuid.uuid4().hex
    path = stop_path(tmp_path, token)
    path.parent.mkdir()
    path.write_text(raw)
    assert not stop_requested(tmp_path, token)


@pytest.mark.skipif(os.name != 'nt', reason='Windows daemon protocol')
def test_real_empty_daemon_stops_and_cleans_own_receipts(tmp_path):
    local, data, platform = [tmp_path / name for name in ['local', 'data', 'platform']]
    (platform / 'Scheduler').mkdir(parents=True)
    (platform / 'Scheduler/jobs.devcore.json').write_text('[]')
    token = uuid.uuid4().hex
    env = dict(os.environ, DEVCORE_LOCAL_ROOT=str(local), DEVCORE_DATA_ROOT=str(data),
        DEVCORE_PLATFORM_ROOT=str(platform), DEVCORE_SCHEDULER_START_TOKEN=token)
    process = subprocess.Popen([sys.executable, str(SCHEDULER / 'scheduler_tick.py')],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline and not adopt_ready(local, data, platform):
            time.sleep(.05)
        assert adopt_ready(local, data, platform)
        cli = subprocess.run([sys.executable, '-I', str(SCHEDULER / 'stop_scheduler.py'),
            '--local-root', str(local), '--data-root', str(data), '--platform-root', str(platform),
            '--pause', '--wait-seconds', '5'],
            env=env, capture_output=True, text=True, timeout=8)
        assert cli.returncode == 0, cli.stderr
        assert json.loads(cli.stdout)['stopped_confirmed'] is False
        assert json.loads(cli.stdout)['shutdown_completed'] is True
        assert process.wait(timeout=8) == 0
        assert instance_available(local)
        assert not (local / 'Scheduler/scheduler.ready.json').exists()
        assert not stop_path(local, token).exists()
        assert is_paused(local)
        assert resume(local, data, platform)['started'] is False
        assert not is_paused(local)
    finally:
        if process.poll() is None:
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True, timeout=5)
        process.wait(timeout=5)
        process.stderr.close()


def test_pause_blocks_watcher_and_direct_sync(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from devcore_engine.infra import system_watcher
    import scheduler_sync
    pause(tmp_path, tmp_path / 'data', tmp_path / 'platform')
    watcher = system_watcher.SystemWatcher.__new__(system_watcher.SystemWatcher)
    watcher.local_root = tmp_path
    watcher.log = lambda *a: None
    monkeypatch.setattr(system_watcher.subprocess, 'Popen', lambda *a, **k: pytest.fail('No launch'))
    monkeypatch.setattr(scheduler_sync, 'sync_registry', lambda *a: pytest.fail('No sync'))
    assert not watcher.ensure_scheduler_daemon()
    with pytest.raises(RuntimeError, match='inhibited'):
        scheduler_tick.start_daemon(SimpleNamespace(local_root=tmp_path), None, None, None)


def test_resume_requires_idle_guard_matching_profile(tmp_path):
    data, platform = tmp_path / 'data', tmp_path / 'platform'
    pause(tmp_path, data, platform)
    with instance_guard(tmp_path):
        with pytest.raises(OSError):
            resume(tmp_path, data, platform)
    with pytest.raises(ValueError):
        resume(tmp_path, tmp_path / 'foreign', platform)
    assert is_paused(tmp_path)
    resume(tmp_path, data, platform)
    assert not is_paused(tmp_path)


@pytest.mark.parametrize('raw', ['{', '[]', 'x' * 4097])
def test_corrupt_pause_preserved_and_blocks_restart(tmp_path, raw):
    path = pause_path(tmp_path)
    path.parent.mkdir()
    path.write_text(raw)
    assert is_paused(tmp_path)
    with pytest.raises((ValueError, AttributeError)):
        resume(tmp_path, tmp_path / 'data', tmp_path / 'platform')
    assert path.read_text() == raw


@pytest.mark.parametrize('seconds', [-1, 31, True, float('nan'), float('inf')])
def test_invalid_wait_does_not_write(tmp_path, seconds):
    with pytest.raises(ValueError):
        request_stop(tmp_path, tmp_path / 'data', tmp_path / 'platform', wait_seconds=seconds)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('exit_code,completed,expected', [(0, True, 0), (2, False, 2), (1, False, 1), (0, False, 2)])
def test_powershell_scheduler_only_gates_other_shutdown(tmp_path, exit_code, completed, expected):
    platform = tmp_path / 'platform'
    scripts = platform / 'Scripts'
    scripts.mkdir(parents=True)
    (scripts / 'platform_version.ps1').write_text('''
function Get-DevCorePython { return $env:DEVCORE_PYTHON }
function Get-DevCorePlatformInfo { return @{title='fixture'} }
''')
    stub = tmp_path / 'fixture_python.ps1'
    payload = json.dumps({'shutdown_completed': completed})
    stub.write_text(f"Write-Output '{payload}'\nexit {exit_code}\n")
    env = dict(os.environ, DEVCORE_PLATFORM_ROOT=str(platform), DEVCORE_LOCAL_ROOT=str(tmp_path / 'local'),
        DEVCORE_DATA_ROOT=str(tmp_path / 'data'), DEVCORE_PYTHON=str(stub))
    result = subprocess.run([PS_EXE, '-NoProfile', '-File', str(SCHEDULER.parent / 'Scripts/stop.ps1'),
        '-SchedulerOnly', '-WaitSeconds', '1'], env=env, capture_output=True, text=True, timeout=8)
    assert result.returncode == expected, result.stdout + result.stderr
    assert not (tmp_path / 'local').exists() and not (tmp_path / 'data').exists()


@pytest.mark.skipif(os.name != 'nt', reason='Windows daemon and PowerShell protocol')
def test_real_powershell_stops_fixture_daemon_and_leaves_pause(tmp_path):
    local, data, platform = [tmp_path / name for name in ['local', 'data', 'platform']]
    shutil.copytree(SCHEDULER, platform / 'Scheduler',
        ignore=shutil.ignore_patterns('__pycache__', 'jobs.devcore.json'))
    (platform / 'Scheduler/jobs.devcore.json').write_text('[]')
    (platform / 'Scripts').mkdir()
    (platform / 'Scripts/platform_version.ps1').write_text('''
function Get-DevCorePython { return $env:DEVCORE_PYTHON }
function Get-DevCorePlatformInfo { return @{title='fixture'} }
''')
    env = dict(os.environ, DEVCORE_LOCAL_ROOT=str(local), DEVCORE_DATA_ROOT=str(data),
        DEVCORE_PLATFORM_ROOT=str(platform), DEVCORE_PYTHON=sys.executable,
        DEVCORE_SCHEDULER_START_TOKEN=uuid.uuid4().hex)
    env['PYTHONPATH'] = os.environ.get('PYTHONPATH', '') + os.pathsep + str(SCHEDULER.parent / 'Tools')
    process = subprocess.Popen([sys.executable, str(platform / 'Scheduler/scheduler_tick.py')],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline and not (local / 'Scheduler/scheduler.ready.json').exists():
            time.sleep(.05)
        result = subprocess.run([PS_EXE, '-NoProfile', '-File', str(SCHEDULER.parent / 'Scripts/stop.ps1'),
            '-SchedulerOnly', '-WaitSeconds', '5'], env=env, capture_output=True, text=True, timeout=10)
        assert result.returncode == 0, result.stdout + result.stderr
        assert process.wait(timeout=5) == 0
        assert is_paused(local) and instance_available(local)
        assert not (local / 'Scheduler/scheduler.ready.json').exists()
    finally:
        if process.poll() is None:
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True, timeout=5)
        process.wait(timeout=5)
        process.stderr.close()
