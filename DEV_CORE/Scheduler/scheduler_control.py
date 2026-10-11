"""Persistent local restart inhibition; unreadable state fails closed."""
from pathlib import Path
import json

from scheduler_storage import write_json


def pause_path(local_root):
    return Path(local_root) / 'Scheduler/scheduler.paused.json'


def is_paused(local_root):
    try:
        pause_path(local_root).lstat()
        return True
    except FileNotFoundError:
        return False
    except OSError:
        return True


def pause(local_root, data_root, platform_root):
    write_json(pause_path(local_root), {'protocol': 1,
        'local_root': str(Path(local_root).resolve()),
        'data_root': str(Path(data_root).resolve()),
        'platform_root': str(Path(platform_root).resolve())})


def resume(local_root, data_root, platform_root):
    from scheduler_presence import instance_guard
    # Explicit maintenance, only once the daemon lifetime guard is released.
    with instance_guard(local_root):
        path = pause_path(local_root)
        with path.open('rb') as stream:
            raw = stream.read(4097)
        if len(raw) > 4096:
            raise ValueError('Invalid pause record')
        data = json.loads(raw)
        expected = {'protocol': 1, 'local_root': str(Path(local_root).resolve()),
            'data_root': str(Path(data_root).resolve()), 'platform_root': str(Path(platform_root).resolve())}
        if data != expected or type(data.get('protocol')) is not int:
            raise ValueError('Pause profile mismatch')
        path.unlink()
    return {'status': 'restart_enabled', 'started': False}
