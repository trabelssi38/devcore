"""Explicit cooperative shutdown of a registered local DevCore service."""
import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parent))
from service_runtime import request_stop, SERVICES


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('local-root', 'data-root', 'platform-root'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--service', required=True, choices=SERVICES)
    parser.add_argument('--wait-seconds', type=float, default=0)
    args = parser.parse_args(argv)
    try:
        result = request_stop(args.local_root, args.data_root, args.platform_root, args.service, args.wait_seconds)
    except (OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({'service': args.service, 'error': str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps(result))
    if result.get('status') == 'shutdown_failed':
        return 3
    return 2 if args.wait_seconds and not result['shutdown_completed'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
