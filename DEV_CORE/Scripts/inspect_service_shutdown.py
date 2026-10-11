"""Bounded read-only local evidence inspection; never infer service readiness."""
import sys
if __name__ == '__main__':
    sys.dont_write_bytecode = True
import argparse
import hashlib
import json
from pathlib import Path
import stat

sys.path.insert(0, str(Path(__file__).resolve().parent))
from service_runtime import SERVICES, paths, profile, valid_token, process_identity

OUTCOMES = ('ok', 'server_error', 'lifespan_error', 'not_started', 'forced_exit')


def read_evidence(path, kind, expected):
    try:
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode) or getattr(metadata, 'st_file_attributes', 0) & 0x400:
            return {'evidence': 'invalid_file'}
        with path.open('rb') as stream:
            raw = stream.read(4097)
        if len(raw) > 4096:
            return {'evidence': 'oversized'}
        data = json.loads(raw)
        if not isinstance(data, dict):
            return {'evidence': 'invalid_record'}
        identity = data.get('identity')
        if (type(data.get('protocol')) is not int or data['protocol'] != 1
            or not valid_token(data.get('token')) or type(data.get('pid')) is not int
            or not 1 <= data['pid'] < 2**32 or not isinstance(identity, dict)
            or type(identity.get('creation_100ns')) is not int or identity['creation_100ns'] <= 0
            or not isinstance(identity.get('image'), str) or not 1 <= len(identity['image']) <= 1024
            or '\x00' in identity['image']):
            return {'evidence': 'invalid_record'}
        if kind != 'request' and data.get('profile') != expected:
            return {'evidence': 'foreign_profile'}
        if kind == 'terminal' and data.get('outcome') not in OUTCOMES:
            return {'evidence': 'invalid_outcome'}
        reference = hashlib.sha256(json.dumps([data['token'], data['pid'], identity], sort_keys=True).encode()).hexdigest()[:16]
        result = {'evidence': 'valid', 'instance_ref': reference, 'pid': data['pid']}
        if kind == 'terminal':
            result['outcome'] = data['outcome']
        return result, identity
    except FileNotFoundError:
        return {'evidence': 'absent'}
    except (ValueError, UnicodeError, RecursionError):
        return {'evidence': 'invalid_record'}
    except OSError:
        return {'evidence': 'unavailable'}


def inspect(local_root, data_root, platform_root, service, *, verify_live=False):
    root = Path(local_root).resolve(strict=True)
    receipt, request, guard = paths(root, service)
    expected = profile(root, data_root, platform_root, service)
    records, identities = {}, {}
    for kind, path in [('identity', receipt), ('request', request), ('terminal', guard.with_suffix('.result.json'))]:
        evidence = read_evidence(path, kind, expected)
        if isinstance(evidence, tuple):
            records[kind], identities[kind] = evidence
        else:
            records[kind] = evidence
    live = 'not_checked'
    if verify_live and 'identity' in identities:
        try:
            live = 'matches' if process_identity(records['identity']['pid']) == identities['identity'] else 'mismatch'
        except (OSError, ValueError, RuntimeError):
            live = 'unavailable'  # Access failure is not proof of death.
    receipt_ref = records['identity'].get('instance_ref')
    request_ref = records['request'].get('instance_ref')
    terminal_ref = records['terminal'].get('instance_ref')
    return {'service': service, 'read_only': True, 'consistent_snapshot': False,
        'guard_checked': False, 'readiness_verified': False, 'live_identity': live,
        'records': records,
        'request_relation': ('not_available' if not request_ref else 'no_identity_record' if not receipt_ref
            else 'same_instance' if receipt_ref == request_ref else 'different_instance'),
        'terminal_relation': ('not_available' if not terminal_ref else 'historical_only' if not receipt_ref
            else 'same_instance' if receipt_ref == terminal_ref else 'different_instance')}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('local-root', 'data-root', 'platform-root'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--service', required=True, choices=SERVICES)
    parser.add_argument('--verify-live', action='store_true')
    args = parser.parse_args(argv)
    try:
        result = inspect(args.local_root, args.data_root, args.platform_root, args.service, verify_live=args.verify_live)
    except (OSError, ValueError) as exc:
        print(json.dumps({'error': type(exc).__name__}), file=sys.stderr)
        return 1
    print(json.dumps(result))
    return 1 if any(item['evidence'] not in ('valid', 'absent') for item in result['records'].values()) else 0


if __name__ == '__main__':
    raise SystemExit(main())
