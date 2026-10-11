"""Local maintenance gate for participating SystemWatcher launches."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scheduler_lock import SchedulerLeaseLock
from scheduler_storage import write_json


def launch_guard(local_root):
    return SchedulerLeaseLock(Path(local_root) / 'Runtime/services.launch', 'maintenance')._guard()


def paused_path(local_root):
    return Path(local_root) / 'Runtime/services.paused.json'


def services_paused(local_root):
    try:
        paused_path(local_root).lstat()
        return True
    except FileNotFoundError:
        return False
    except OSError:
        return True


def control(local_root, data_root, platform_root, action):
    if action not in ('pause', 'resume'):
        raise ValueError('Unknown control action')
    root = Path(local_root).resolve(strict=True)
    profile = {'protocol': 1, 'local_root': str(root),
        'data_root': str(Path(data_root).resolve()), 'platform_root': str(Path(platform_root).resolve())}
    # Nonblocking: in-flight launch must finish before pause can be accepted.
    with launch_guard(root):
        path = paused_path(root)
        if services_paused(root) or action == 'resume':
            with path.open('rb') as stream:
                raw = stream.read(4097)
            if len(raw) > 4096:
                raise ValueError('Oversized maintenance profile')
            stored = json.loads(raw)
            if stored != profile or type(stored.get('protocol')) is not int:
                raise ValueError('Maintenance profile mismatch')
        if action == 'pause':
            write_json(path, profile)
        else:
            path.unlink()
    return {'status': 'services_paused' if action == 'pause' else 'services_restart_enabled',
        'processes_stopped': False, 'processes_started': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('local-root', 'data-root', 'platform-root'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--action', choices=('pause', 'resume'), required=True)
    args = parser.parse_args(argv)
    try:
        result = control(args.local_root, args.data_root, args.platform_root, args.action)
    except (OSError, ValueError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
