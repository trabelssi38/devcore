"""Participating daemon lifetime guard and launch-scoped readiness evidence."""
import json
import os
from pathlib import Path
import sys
import time
import math

from scheduler_lock import SchedulerLeaseLock, SchedulerGuardBusy
from scheduler_storage import write_json
from windows_process_identity import process_identity


def instance_guard(local_root):
    return SchedulerLeaseLock(Path(local_root) / 'Scheduler/scheduler.instance', 'daemon')._guard()


def instance_available(local_root):
    return instance_status(local_root) == 'available'


def instance_status(local_root):
    try:
        with instance_guard(local_root):
            return 'available'
    except SchedulerGuardBusy:
        return 'busy'
    except OSError:
        return 'unavailable'  # Permission/storage failure is not proven contention.


def validate_launch_token(token):
    if not isinstance(token, str) or len(token) != 32 or any(c not in '0123456789abcdef' for c in token):
        raise ValueError('Invalid launch token')


def publish_ready(local_root, token, *, data_root=None, platform_root=None):
    validate_launch_token(token)
    write_json(Path(local_root) / 'Scheduler/scheduler.ready.json', {
        'protocol': 2, 'token': token, 'pid': os.getpid(), 'parent_pid': os.getppid(),
        'python': str(Path(sys.executable).resolve()),
        'identity': process_identity(os.getpid()),
        'script': str((Path(__file__).resolve().parent / 'scheduler_tick.py').resolve()),
        'data_root': str(Path(data_root if data_root is not None else os.environ['DEVCORE_DATA_ROOT']).resolve()),
        'platform_root': str(Path(platform_root if platform_root is not None else os.environ['DEVCORE_PLATFORM_ROOT']).resolve()),
        'local_root': str(Path(local_root).resolve()), 'ready_at': time.time()})


def child_ready(local_root, token, process):
    if process.poll() is not None:
        return False
    try:
        path = Path(local_root) / 'Scheduler/scheduler.ready.json'
        with path.open('rb') as stream:
            raw = stream.read(4097)
        if len(raw) > 4096:
            return False
        data = json.loads(raw)
        stamp = data['ready_at']
        return (type(data.get('protocol')) is int and data['protocol'] == 2
            and data.get('token') == token and type(data.get('pid')) is int and data['pid'] > 0
            and (data['pid'] == process.pid or (os.name == 'nt'
                and type(data.get('parent_pid')) is int and data['parent_pid'] == process.pid))
            and data.get('python') == str(Path(sys.executable).resolve())
            and data.get('local_root') == str(Path(local_root).resolve())
            and type(stamp) in (int, float) and 0 <= time.time() - stamp <= 30
            and _identity_matches(data)
            and process.poll() is None)
    except (OSError, ValueError, TypeError, KeyError, RuntimeError):
        return False


def _identity_matches(data):
    identity = data.get('identity')
    return (isinstance(identity, dict) and type(identity.get('creation_100ns')) is int
        and identity['creation_100ns'] > 0 and isinstance(identity.get('image'), str)
        and identity == process_identity(data['pid'])
        and identity['image'] == process_identity(os.getpid())['image'])


def adopt_ready(local_root, data_root, platform_root):
    return verified_instance(local_root, data_root, platform_root) is not None


def verified_instance(local_root, data_root, platform_root, *, require_fresh=True):
    """Recognize a fresh participating daemon under trusted local receipt storage.

    This is a point-in-time OS identity/profile check, not administrative auth.
    """
    if instance_status(local_root) != 'busy':
        return None
    try:
        with (Path(local_root) / 'Scheduler/scheduler.ready.json').open('rb') as stream:
            raw = stream.read(4097)
        if len(raw) > 4096:
            return None
        data = json.loads(raw)
        token, stamp = data['token'], data['ready_at']
        valid = (type(data.get('protocol')) is int and data['protocol'] == 2
            and isinstance(token, str) and len(token) == 32 and all(c in '0123456789abcdef' for c in token)
            and type(data.get('pid')) is int and data['pid'] > 0
            and data.get('local_root') == str(Path(local_root).resolve())
            and data.get('data_root') == str(Path(data_root).resolve())
            and data.get('platform_root') == str(Path(platform_root).resolve())
            and data.get('script') == str((Path(__file__).resolve().parent / 'scheduler_tick.py').resolve())
            and data.get('python') == str(Path(sys.executable).resolve())
            and type(stamp) in (int, float) and math.isfinite(stamp) and 0 <= stamp <= time.time()
            and (not require_fresh or time.time() - stamp <= 30)
            and _identity_matches(data) and instance_status(local_root) == 'busy')
        return data if valid else None
    except (OSError, ValueError, TypeError, KeyError, RuntimeError):
        return None


def clear_ready(local_root, token):
    path = Path(local_root) / 'Scheduler/scheduler.ready.json'
    try:
        with path.open('rb') as stream:
            raw = stream.read(4097)
        if len(raw) <= 4096 and json.loads(raw).get('token') == token:
            path.unlink()
    except FileNotFoundError:
        pass
