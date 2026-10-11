"""Cooperative server shutdown with disposable profiles and ephemeral ports."""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys

PS_EXE = shutil.which("pwsh") or shutil.which("powershell") or "powershell"
import threading
import time
import uuid

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Scripts'))
import service_runtime as runtime
from scheduler_lock import SchedulerLeaseLock
from scheduler_storage import write_json
from windows_process_identity import process_identity

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='Windows identity profile')


def receipt(root):
    path, _, guard = runtime.paths(root, 'router')
    data = {'protocol': 1, 'token': uuid.uuid4().hex, 'pid': os.getpid(),
        'identity': process_identity(os.getpid()),
        'profile': runtime.profile(root, root / 'data', root / 'platform', 'router')}
    write_json(path, data)
    return path, guard, data


@pytest.mark.parametrize('field,value', [('pid', True), ('pid', 0), ('token', 'bad'), ('protocol', True),
    ('identity', {'creation_100ns': 1, 'image': 'wrong'}), ('profile', {})])
def test_wrong_receipt_never_writes_stop(tmp_path, field, value):
    path, guard, data = receipt(tmp_path)
    data[field] = value
    write_json(path, data)
    with SchedulerLeaseLock(guard, 'fixture')._guard():
        with pytest.raises((ValueError, OSError)):
            runtime.request_stop(tmp_path, tmp_path / 'data', tmp_path / 'platform', 'router')
    assert not runtime.paths(tmp_path, 'router')[1].exists()


def test_foreign_profile_and_unheld_guard_refused(tmp_path):
    _, guard, _ = receipt(tmp_path)
    with pytest.raises(ValueError):
        runtime.request_stop(tmp_path, tmp_path / 'data', tmp_path / 'platform', 'router')
    with SchedulerLeaseLock(guard, 'fixture')._guard():
        with pytest.raises(ValueError):
            runtime.request_stop(tmp_path, tmp_path / 'foreign', tmp_path / 'platform', 'router')
    assert not runtime.paths(tmp_path, 'router')[1].exists()


@pytest.mark.parametrize('raw', ['{', '[]', 'x' * 4097, '[' * 1500 + ']' * 1500])
def test_invalid_receipt_preserved(tmp_path, raw):
    path, _, _ = runtime.paths(tmp_path, 'router')
    path.parent.mkdir()
    path.write_text(raw)
    with pytest.raises(ValueError):
        runtime.request_stop(tmp_path, tmp_path / 'data', tmp_path / 'platform', 'router')
    assert path.read_text() == raw


def test_unregistered_service_does_not_create_store(tmp_path):
    with pytest.raises(OSError):
        runtime.request_stop(tmp_path, tmp_path / 'data', tmp_path / 'platform', 'router')
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('field,value', [('token', '0' * 32), ('profile', {}), ('outcome', 'unknown'), ('protocol', True)])
def test_foreign_or_invalid_terminal_result_refused(tmp_path, monkeypatch, field, value):
    path, guard, data = receipt(tmp_path)
    terminal = dict(data, outcome='ok')
    terminal[field] = value
    original = runtime.write_json
    def emulate_finish(request_path, request):
        original(request_path, request)
        path.unlink()
        request_path.unlink()
        original(guard.with_suffix('.result.json'), terminal)
    monkeypatch.setattr(runtime, 'require_busy', lambda *a: None)  # Isolated completed-cycle fixture.
    monkeypatch.setattr(runtime, 'write_json', emulate_finish)
    with pytest.raises(ValueError, match='Shutdown result'):
        runtime.request_stop(tmp_path, tmp_path / 'data', tmp_path / 'platform', 'router', 1)
    assert runtime.read_record(guard.with_suffix('.result.json')) == terminal


@pytest.mark.parametrize('status,completed,wait,expected', [
    ('shutdown_failed', False, 1, 3), ('stop_requested', False, 1, 2),
    ('shutdown_completed', True, 1, 0), ('stop_requested', False, 0, 0)])
def test_cli_distinguishes_failed_pending_and_completed(tmp_path, monkeypatch, capsys, status, completed, wait, expected):
    import stop_service
    monkeypatch.setattr(stop_service, 'request_stop', lambda *a: {'status': status, 'shutdown_completed': completed})
    assert stop_service.main(['--local-root', str(tmp_path), '--data-root', str(tmp_path / 'data'),
        '--platform-root', str(tmp_path / 'platform'), '--service', 'router', '--wait-seconds', str(wait)]) == expected
    assert json.loads(capsys.readouterr().out)['status'] == status


def test_real_uvicorn_finishes_on_matching_request(tmp_path, monkeypatch):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    monkeypatch.setitem(runtime.SERVICES, 'fixture', port)
    for key, name in [('DEVCORE_LOCAL_ROOT', ''), ('DEVCORE_DATA_ROOT', 'data'), ('DEVCORE_PLATFORM_ROOT', 'platform')]:
        monkeypatch.setenv(key, str(tmp_path / name))
    async def app(scope, receive, send):
        await send({'type': 'http.response.start', 'status': 200, 'headers': []})
        await send({'type': 'http.response.body', 'body': b'fixture'})
    errors = []
    def run():
        try:
            runtime.run_managed(app, host='127.0.0.1', port=port, service='fixture', lifespan='off', log_level='error')
        except BaseException as exc:
            errors.append(exc)
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    path, stop, _ = runtime.paths(tmp_path, 'fixture')
    try:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not path.exists() and not errors:
            time.sleep(.05)
        data = runtime.read_record(path)
        # Wrong nonce cannot close the server.
        write_json(stop, dict(protocol=1, token='0' * 32, pid=data['pid'], identity=data['identity']))
        time.sleep(.3)
        assert thread.is_alive() and not errors
        # Invalid records must not terminate the monitor; a valid request
        # afterwards still closes the real server.
        for raw in (b'{', b'\xff', b'[' * 1500 + b']' * 1500, b'x' * 4097):
            stop.write_bytes(raw)
            time.sleep(.3)
            assert thread.is_alive() and not errors
            assert stop.read_bytes() == raw
        result = runtime.request_stop(tmp_path, tmp_path / 'data', tmp_path / 'platform', 'fixture', 5)
        thread.join(timeout=2)
        assert result['shutdown_completed'] and not result['force']
        assert not thread.is_alive() and not errors
        assert not path.exists() and not stop.exists()
    finally:
        if thread.is_alive() and path.exists():
            data = runtime.read_record(path)
            write_json(stop, dict(protocol=1, token=data['token'], pid=data['pid'], identity=data['identity']))
            thread.join(timeout=5)


def test_malformed_signal_at_cleanup_preserves_terminal_outcome(tmp_path, monkeypatch):
    import uvicorn
    for key, name in [('DEVCORE_LOCAL_ROOT', ''), ('DEVCORE_DATA_ROOT', 'data'),
            ('DEVCORE_PLATFORM_ROOT', 'platform')]:
        monkeypatch.setenv(key, str(tmp_path / name))
    path, stop, guard = runtime.paths(tmp_path, 'router')
    raw = b'[' * 1500 + b']' * 1500
    class Server:
        started = True
        force_exit = False
        def __init__(self, config):
            pass
        def run(self):
            stop.write_bytes(raw)
    monkeypatch.setattr(uvicorn, 'Server', Server)
    runtime.run_managed(None, host='127.0.0.1', port=20130, service='router')
    assert not path.exists()
    assert stop.read_bytes() == raw
    assert runtime.read_record(guard.with_suffix('.result.json'))['outcome'] == 'ok'
    with SchedulerLeaseLock(guard, 'fixture-observer')._guard():
        pass


@pytest.mark.parametrize('missing', [False, True])
def test_full_powershell_only_requests_registered_services(tmp_path, missing):
    scripts = tmp_path / 'platform/Scripts'
    scripts.mkdir(parents=True)
    (scripts / 'platform_version.ps1').write_text('''
function Get-DevCorePython { return $env:DEVCORE_PYTHON }
function Get-DevCorePlatformInfo { return @{title='fixture'} }
''')
    stub = tmp_path / 'fixture_python.ps1'
    stub.write_text('''
[System.IO.File]::AppendAllText($env:FIXTURE_TRACE, ($args -join ' ') + "`n")
if ($args -contains '-m') { exit 0 }
if ($args -contains '--action') { Write-Output '{"status":"services_paused"}'; exit 0 }
if ($args -contains '--service' -and $env:FIXTURE_MISSING -eq 'yes') { exit 1 }
Write-Output '{"shutdown_completed":true}'; exit 0
''')
    trace = tmp_path / 'calls.txt'
    env = dict(os.environ, DEVCORE_LOCAL_ROOT=str(tmp_path / 'local'), DEVCORE_DATA_ROOT=str(tmp_path / 'data'),
        DEVCORE_PLATFORM_ROOT=str(scripts.parent), DEVCORE_PYTHON=str(stub), FIXTURE_TRACE=str(trace),
        FIXTURE_MISSING='yes' if missing else 'no')
    wrapper = tmp_path / 'stop_fixture.ps1'
    source = Path(__file__).resolve().parents[1] / 'Scripts/stop.ps1'
    wrapper.write_text(f"function Stop-Process {{ throw 'No process kill allowed' }}\n"
        f"function Get-NetTCPConnection {{ throw 'No port discovery allowed' }}\n& '{source.as_posix()}'\nexit $LASTEXITCODE\n")
    result = subprocess.run([PS_EXE, '-NoProfile', '-File', str(wrapper)], env=env,
        capture_output=True, text=True, timeout=8)
    assert result.returncode == (1 if missing else 0), result.stdout + result.stderr
    calls = trace.read_text()
    assert calls.count('--service ') == 4
    assert 'No process kill allowed' not in result.stderr and 'No port discovery allowed' not in result.stderr
