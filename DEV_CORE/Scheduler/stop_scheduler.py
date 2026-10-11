"""Request cooperative shutdown of an identified local scheduler; never kill it."""
import argparse
import json
import os
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scheduler_presence import verified_instance, validate_launch_token, instance_status
from scheduler_storage import write_json
from windows_process_identity import process_identity
from scheduler_control import pause, resume


def stop_path(local_root, token):
    validate_launch_token(token)
    return Path(local_root) / 'Scheduler' / f'scheduler.stop.{token}.json'


def request_stop(local_root, data_root, platform_root, *, inhibit_restart=False, wait_seconds=0):
    if type(wait_seconds) not in (int, float) or not 0 <= wait_seconds <= 30:
        raise ValueError('Wait must be between zero and 30 seconds')
    root = Path(local_root).resolve(strict=True)
    # Freshness may expire during a long job. OS identity/profile still required.
    receipt = verified_instance(root, data_root, platform_root, require_fresh=False)
    if receipt is None:
        raise RuntimeError('Scheduler identity/profile not verified; no stop request written')
    if inhibit_restart:
        pause(root, data_root, platform_root)
    write_json(stop_path(root, receipt['token']), {'protocol': 1, 'token': receipt['token'],
        'pid': receipt['pid'], 'creation_100ns': receipt['identity']['creation_100ns']})
    result = {'status': 'stop_requested', 'pid': receipt['pid'], 'stopped_confirmed': False,
        'policy': 'finish_current_job_then_stop', 'force': False, 'shutdown_completed': False}
    deadline = time.monotonic() + wait_seconds
    while wait_seconds and time.monotonic() < deadline:
        # Protocol completion, not independent OS process-death certification.
        if instance_status(root) == 'available' and not stop_path(root, receipt['token']).exists():
            result['shutdown_completed'] = True
            break
        time.sleep(min(.1, max(0, deadline - time.monotonic())))
    return result


def stop_requested(local_root, token):
    try:
        with stop_path(local_root, token).open('rb') as stream:
            raw = stream.read(2049)
        if len(raw) > 2048:
            return False
        data = json.loads(raw)
        return (type(data.get('protocol')) is int and data['protocol'] == 1
            and data.get('token') == token and type(data.get('pid')) is int and data['pid'] == os.getpid()
            and type(data.get('creation_100ns')) is int
            and data['creation_100ns'] == process_identity(os.getpid())['creation_100ns'])
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, AttributeError):
        return False


def idle_wait(stop_callback):
    if stop_callback is None:
        time.sleep(10)
        return
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if stop_callback():
            return
        time.sleep(min(.2, max(0, deadline - time.monotonic())))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--local-root', required=True, type=Path)
    parser.add_argument('--data-root', required=True, type=Path)
    parser.add_argument('--platform-root', required=True, type=Path)
    parser.add_argument('--wait-seconds', type=float, default=0)
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--pause', action='store_true', help='Persistently inhibit scheduler restarts')
    action.add_argument('--resume', action='store_true', help='Remove matching pause after daemon exits; does not launch')
    args = parser.parse_args(argv)
    try:
        result = (resume(args.local_root, args.data_root, args.platform_root) if args.resume else
            request_stop(args.local_root, args.data_root, args.platform_root,
                inhibit_restart=args.pause, wait_seconds=args.wait_seconds))
    except (OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps(result))
    return 2 if not args.resume and args.wait_seconds and not result['shutdown_completed'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
