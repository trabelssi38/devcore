"""Cooperative lifecycle for local Uvicorn services; no PID/port-based kill."""
import json
import os
from pathlib import Path
import sys
import threading
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Scheduler'))
from scheduler_lock import SchedulerLeaseLock, SchedulerGuardBusy
from scheduler_storage import write_json
from windows_process_identity import process_identity

SERVICES = {'dashboard': 20129, 'router': 20130, 'headroom-native': 8787, 'headroom-auxiliary': 8789}


def paths(root, service):
    if service not in SERVICES:
        raise ValueError('Unsupported managed service')
    base = Path(root) / 'Runtime' / ('service-' + service)
    return base.with_suffix('.identity.json'), base.with_suffix('.stop.json'), base.with_suffix('.instance')


def profile(local_root, data_root, platform_root, service):
    return {'local_root': str(Path(local_root).resolve()), 'data_root': str(Path(data_root).resolve()),
        'platform_root': str(Path(platform_root).resolve()), 'service': service, 'port': SERVICES[service]}


def read_record(path):
    with path.open('rb') as stream:
        raw = stream.read(4097)
    if len(raw) > 4096:
        raise ValueError('Oversized service record')
    try:
        data = json.loads(raw)
    except RecursionError as exc:
        raise ValueError('Excessive service record nesting') from exc
    if not isinstance(data, dict):
        raise ValueError('Invalid service record')
    return data


def valid_token(token):
    return isinstance(token, str) and len(token) == 32 and all(c in '0123456789abcdef' for c in token)


def require_busy(guard_path):
    if not guard_path.with_suffix(guard_path.suffix + '.guard').is_file():
        raise ValueError('Service lifetime guard absent')
    try:
        with SchedulerLeaseLock(guard_path, 'identity-observer')._guard():
            pass
    except SchedulerGuardBusy:
        return
    raise ValueError('Service lifetime guard is not held')


def request_stop(local_root, data_root, platform_root, service, wait_seconds=0):
    if type(wait_seconds) not in (int, float) or not 0 <= wait_seconds <= 30:
        raise ValueError('Wait must be between zero and 30 seconds')
    root = Path(local_root).resolve(strict=True)
    receipt_path, request_path, guard_path = paths(root, service)
    receipt = read_record(receipt_path)
    require_busy(guard_path)
    pid = receipt.get('pid')
    expected = profile(root, data_root, platform_root, service)
    if (type(receipt.get('protocol')) is not int or receipt['protocol'] != 1
        or receipt.get('profile') != expected or not valid_token(receipt.get('token'))
        or type(pid) is not int or pid <= 0 or receipt.get('identity') != process_identity(pid)):
        raise ValueError('Service identity/profile not verified')
    require_busy(guard_path)
    # Known live process is verified; local receipt storage must be trusted.
    write_json(request_path, {'protocol': 1, 'token': receipt['token'], 'pid': pid,
        'identity': receipt['identity']})
    result = {'service': service, 'status': 'stop_requested', 'force': False,
        'shutdown_completed': False, 'shutdown_finished': False}
    deadline = time.monotonic() + wait_seconds
    while wait_seconds and time.monotonic() < deadline:
        if not receipt_path.exists() and not request_path.exists():
            try:
                with SchedulerLeaseLock(guard_path, 'stop-observer')._guard():
                    terminal = read_record(guard_path.with_suffix('.result.json'))
                    if (type(terminal.get('protocol')) is not int or terminal['protocol'] != 1
                        or terminal.get('token') != receipt['token'] or terminal.get('pid') != pid
                        or type(terminal.get('pid')) is not int or terminal.get('identity') != receipt['identity']
                        or terminal.get('profile') != expected
                        or terminal.get('outcome') not in ('ok', 'server_error', 'lifespan_error', 'not_started', 'forced_exit')):
                        raise ValueError('Shutdown result identity/profile not verified')
                    result['shutdown_finished'] = True
                    result['shutdown_completed'] = terminal['outcome'] == 'ok'
                    result['status'] = 'shutdown_completed' if result['shutdown_completed'] else 'shutdown_failed'
                    result['outcome'] = terminal['outcome']
                break
            except OSError:
                pass
        time.sleep(min(.1, max(0, deadline - time.monotonic())))
    return result


def run_managed(app, *, host, port, service, **kwargs):
    import uvicorn
    names = ('DEVCORE_LOCAL_ROOT', 'DEVCORE_DATA_ROOT', 'DEVCORE_PLATFORM_ROOT')
    values = [os.environ.get(name) for name in names]
    if all(value is None for value in values):
        return uvicorn.run(app, host=host, port=port, **kwargs)
    if not all(values) or host != '127.0.0.1' or type(port) is not int or SERVICES.get(service) != port:
        raise ValueError('Managed service requires explicit roots and matching localhost profile')
    if kwargs.get('timeout_graceful_shutdown') is not None:
        raise ValueError('Managed drain must not cancel active requests on a graceful timeout')
    kwargs['timeout_graceful_shutdown'] = None
    root, data_root, platform_root = values
    receipt_path, request_path, guard_path = paths(root, service)
    server = uvicorn.Server(uvicorn.Config(app, host=host, port=port, **kwargs))
    token, pid = uuid.uuid4().hex, os.getpid()
    identity = process_identity(pid)
    receipt = {'protocol': 1, 'token': token, 'pid': pid, 'identity': identity,
        'profile': profile(root, data_root, platform_root, service)}
    finished = threading.Event()
    def monitor():
        while not finished.wait(.2):
            try:
                request = read_record(request_path)
                if (type(request.get('protocol')) is int and request['protocol'] == 1
                    and request.get('token') == token and type(request.get('pid')) is int
                    and request['pid'] == pid and request.get('identity') == identity):
                    server.should_exit = True
                    return
            except (OSError, ValueError):
                pass
    with SchedulerLeaseLock(guard_path, 'service-' + token)._guard():
        write_json(receipt_path, receipt)  # Identity registration, not readiness.
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
        outcome = 'server_error'
        try:
            server.run()
            lifecycle = getattr(server, 'lifespan', None)
            if not server.started:
                outcome = 'not_started'
            elif server.force_exit:
                outcome = 'forced_exit'
            elif any(getattr(lifecycle, key, False) for key in ('startup_failed', 'shutdown_failed', 'error_occurred')):
                outcome = 'lifespan_error'
            else:
                outcome = 'ok'
        finally:
            finished.set()
            thread.join(timeout=1)
            # Publish the outcome before removing identity/request. Failure to
            # persist leaves signals intact; absence alone never proves success.
            write_json(guard_path.with_suffix('.result.json'), dict(receipt, outcome=outcome))
            for path in (receipt_path, request_path):
                try:
                    if read_record(path).get('token') == token:
                        path.unlink()
                except (FileNotFoundError, ValueError):
                    # A malformed signal is not ours to delete. Preserve it
                    # without masking the already published lifecycle outcome.
                    pass
