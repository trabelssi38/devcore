"""Launch evidence, retry budget and lifetime exclusion on temporary roots."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace
import uuid

import pytest

SCHEDULER = Path(__file__).resolve().parents[1] / 'Scheduler'
sys.path.insert(0, str(SCHEDULER))
from scheduler_presence import instance_guard, instance_available, publish_ready, child_ready, clear_ready, adopt_ready
from windows_process_identity import process_identity
from devcore_engine.infra import system_watcher

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='Windows identity/daemon recipe')


def watcher(tmp_path):
    instance = system_watcher.SystemWatcher.__new__(system_watcher.SystemWatcher)
    instance.local_root = tmp_path / 'local'
    instance.data_root = tmp_path / 'data'
    instance.log = lambda *a: None
    return instance


def test_launch_failure_spends_budget_not_success(tmp_path, monkeypatch):
    instance = watcher(tmp_path)
    calls = []
    def fail(*a, **kw):
        calls.append(1)
        raise OSError('fixture failure')
    monkeypatch.setattr(system_watcher.subprocess, 'Popen', fail)
    assert not instance.ensure_scheduler_daemon()
    assert not instance.ensure_scheduler_daemon()
    assert calls == [1]


def test_busy_instance_never_spawns_or_claims_health(tmp_path, monkeypatch):
    instance = watcher(tmp_path)
    with instance_guard(instance.local_root):
        monkeypatch.setattr(system_watcher.subprocess, 'Popen', lambda *a, **k: pytest.fail('No duplicate'))
        assert not instance.ensure_scheduler_daemon()
    assert not (instance.local_root / 'Runtime/service_restarts.sqlite3').exists()


def test_child_death_and_pending_child_never_claim_ready(tmp_path, monkeypatch):
    instance = watcher(tmp_path)
    process = SimpleNamespace(pid=os.getpid(), poll=lambda: 1)
    monkeypatch.setattr(system_watcher.subprocess, 'Popen', lambda *a, **k: process)
    assert not instance.ensure_scheduler_daemon(.02)
    process.poll = lambda: None
    monkeypatch.setattr(system_watcher.subprocess, 'Popen', lambda *a, **k: pytest.fail('No blind relaunch'))
    assert not instance.ensure_scheduler_daemon()


def test_launch_token_ready_and_child_roots_are_scoped(tmp_path, monkeypatch):
    instance = watcher(tmp_path)
    process = SimpleNamespace(pid=os.getpid(), poll=lambda: None)
    captured = []
    def launch(*a, **kw):
        captured.append(kw['env'])
        publish_ready(instance.local_root, kw['env']['DEVCORE_SCHEDULER_START_TOKEN'])
        return process
    monkeypatch.setattr(system_watcher.subprocess, 'Popen', launch)
    assert instance.ensure_scheduler_daemon()
    assert instance.ensure_scheduler_daemon()
    assert len(captured) == 1
    assert captured[0]['DEVCORE_LOCAL_ROOT'] == str(instance.local_root)
    assert captured[0]['DEVCORE_DATA_ROOT'] == str(instance.data_root)
    process.poll = lambda: 1
    assert not instance.ensure_scheduler_daemon()


@pytest.mark.parametrize('field,value', [('token', 'foreign'), ('pid', True), ('pid', 0),
    ('protocol', True), ('python', 'wrong'), ('local_root', 'wrong'),
    ('ready_at', 0), ('ready_at', float('nan')), ('ready_at', True)])
def test_wrong_stale_or_invalid_evidence_refused(tmp_path, field, value):
    token = uuid.uuid4().hex
    publish_ready(tmp_path, token)
    path = tmp_path / 'Scheduler/scheduler.ready.json'
    data = json.loads(path.read_text())
    data[field] = value
    path.write_text(json.dumps(data))
    assert not child_ready(tmp_path, token, SimpleNamespace(pid=os.getpid(), poll=lambda: None))


@pytest.mark.parametrize('timeout', [0, -1, 31, True, float('nan'), float('inf')])
def test_invalid_deadline_before_any_launch(tmp_path, timeout):
    with pytest.raises(ValueError):
        watcher(tmp_path).ensure_scheduler_daemon(timeout)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('provided_token', [True, False])
def test_real_empty_fixture_daemon_ready_and_guard_released_on_death(tmp_path, provided_token):
    platform = tmp_path / 'platform'
    local = tmp_path / 'local'
    (platform / 'Scheduler').mkdir(parents=True)
    (platform / 'Scheduler/jobs.devcore.json').write_text('[]')
    token = uuid.uuid4().hex
    env = dict(os.environ, DEVCORE_PLATFORM_ROOT=str(platform), DEVCORE_LOCAL_ROOT=str(local),
        DEVCORE_DATA_ROOT=str(tmp_path / 'data'), DEVCORE_SCHEDULER_START_TOKEN=token)
    if not provided_token:
        env.pop('DEVCORE_SCHEDULER_START_TOKEN')
    process = subprocess.Popen([sys.executable, str(SCHEDULER / 'scheduler_tick.py')], env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline and process.poll() is None:
            if adopt_ready(local, tmp_path / 'data', platform):
                break
            time.sleep(.05)
        if not provided_token:
            token = json.loads((local / 'Scheduler/scheduler.ready.json').read_text())['token']
        assert child_ready(local, token, process), 'Fixture daemon did not initialize'
        assert adopt_ready(local, tmp_path / 'data', platform)
        assert not adopt_ready(local, tmp_path / 'foreign-data', platform)
        assert not instance_available(local)
        assert json.loads((local / 'Scheduler/jobs.json').read_text()) == []
    finally:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True, timeout=5)
        else:
            process.kill()
        process.wait(timeout=5)
        process.stderr.close()
    # Windows venv launcher can exit before its interpreter releases handles.
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and not instance_available(local):
        time.sleep(.05)
    assert instance_available(local)
    assert not child_ready(local, token, process)
    assert not adopt_ready(local, tmp_path / 'data', platform)


def test_clear_readiness_only_for_own_launch(tmp_path):
    token = uuid.uuid4().hex
    publish_ready(tmp_path, token)
    clear_ready(tmp_path, uuid.uuid4().hex)
    assert child_ready(tmp_path, token, SimpleNamespace(pid=os.getpid(), poll=lambda: None))
    clear_ready(tmp_path, token)
    assert not (tmp_path / 'Scheduler/scheduler.ready.json').exists()


def test_new_watcher_adopts_matching_os_identity_without_launch(tmp_path, monkeypatch):
    instance = watcher(tmp_path)
    monkeypatch.setenv('DEVCORE_DATA_ROOT', str(instance.data_root))
    monkeypatch.setenv('DEVCORE_PLATFORM_ROOT', str(system_watcher.DEV_CORE_ROOT))
    publish_ready(instance.local_root, uuid.uuid4().hex)
    monkeypatch.setattr(system_watcher.subprocess, 'Popen', lambda *a, **k: pytest.fail('No duplicate launch'))
    with instance_guard(instance.local_root):
        assert instance.ensure_scheduler_daemon()
    assert not (instance.local_root / 'Runtime/service_restarts.sqlite3').exists()
    assert (instance.local_root / 'Runtime/services.launch.guard').exists()


@pytest.mark.parametrize('field,value', [('creation_100ns', 1), ('creation_100ns', True),
    ('image', 'foreign-image')])
def test_pid_reuse_or_foreign_image_refused(tmp_path, field, value):
    token = uuid.uuid4().hex
    publish_ready(tmp_path, token)
    path = tmp_path / 'Scheduler/scheduler.ready.json'
    data = json.loads(path.read_text())
    data['identity'][field] = value
    path.write_text(json.dumps(data))
    with instance_guard(tmp_path):
        assert not adopt_ready(tmp_path, os.environ['DEVCORE_DATA_ROOT'], os.environ['DEVCORE_PLATFORM_ROOT'])
    assert not child_ready(tmp_path, token, SimpleNamespace(pid=os.getpid(), poll=lambda: None))


@pytest.mark.parametrize('field', ['script', 'python', 'data_root', 'platform_root'])
def test_foreign_adoption_profile_refused(tmp_path, field):
    publish_ready(tmp_path, uuid.uuid4().hex)
    path = tmp_path / 'Scheduler/scheduler.ready.json'
    data = json.loads(path.read_text())
    data[field] = 'foreign'
    path.write_text(json.dumps(data))
    with instance_guard(tmp_path):
        assert not adopt_ready(tmp_path, os.environ['DEVCORE_DATA_ROOT'], os.environ['DEVCORE_PLATFORM_ROOT'])


def test_os_identity_access_denied_and_old_protocol_refused(tmp_path, monkeypatch):
    import scheduler_presence
    publish_ready(tmp_path, uuid.uuid4().hex)
    def denied(*a):
        raise OSError('fixture denied')
    monkeypatch.setattr(scheduler_presence, 'process_identity', denied)
    with instance_guard(tmp_path):
        assert not adopt_ready(tmp_path, os.environ['DEVCORE_DATA_ROOT'], os.environ['DEVCORE_PLATFORM_ROOT'])
    path = tmp_path / 'Scheduler/scheduler.ready.json'
    data = json.loads(path.read_text())
    data['protocol'] = 1
    path.write_text(json.dumps(data))
    with instance_guard(tmp_path):
        assert not adopt_ready(tmp_path, os.environ['DEVCORE_DATA_ROOT'], os.environ['DEVCORE_PLATFORM_ROOT'])


@pytest.mark.parametrize('pid', [True, 0, -1, 2**32])
def test_os_pid_input_bounds(pid):
    with pytest.raises(ValueError):
        process_identity(pid)


def test_guard_access_error_not_treated_as_proven_busy(tmp_path, monkeypatch):
    import scheduler_presence
    publish_ready(tmp_path, uuid.uuid4().hex)
    def denied(*a):
        raise PermissionError('fixture inaccessible guard')
    monkeypatch.setattr(scheduler_presence, 'instance_guard', denied)
    assert not adopt_ready(tmp_path, os.environ['DEVCORE_DATA_ROOT'], os.environ['DEVCORE_PLATFORM_ROOT'])


def test_explicit_profile_without_environment_roots(tmp_path, monkeypatch):
    monkeypatch.delenv('DEVCORE_DATA_ROOT', raising=False)
    monkeypatch.delenv('DEVCORE_PLATFORM_ROOT', raising=False)
    data, platform = tmp_path / 'data', tmp_path / 'platform'
    publish_ready(tmp_path, uuid.uuid4().hex, data_root=data, platform_root=platform)
    with instance_guard(tmp_path):
        assert adopt_ready(tmp_path, data, platform)


@pytest.mark.parametrize('token', ['', 'x' * 32, '1' * 31])
def test_invalid_explicit_token_refused_before_sync(tmp_path, monkeypatch, token):
    import scheduler_tick, scheduler_sync
    monkeypatch.setenv('DEVCORE_SCHEDULER_START_TOKEN', token)
    monkeypatch.setattr(scheduler_sync, 'sync_registry', lambda *a: pytest.fail('No sync on invalid token'))
    with pytest.raises(ValueError, match='Invalid launch token'):
        scheduler_tick.start_daemon(SimpleNamespace(local_root=tmp_path),
            tmp_path / 'scheduler.db', tmp_path / 'jobs.json', tmp_path / 'scheduler.lock')
    assert list(tmp_path.iterdir()) == []
