"""Read-only diagnostics preserve fixture bytes/mtimes and disclose no raw records."""
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / 'Scripts'
sys.path.insert(0, str(SCRIPTS))
import inspect_service_shutdown as inspector
from service_runtime import paths, profile
from scheduler_storage import write_json


def evidence(root, *, token=None):
    return {'protocol': 1, 'token': token or uuid.uuid4().hex, 'pid': 1234,
        'identity': {'creation_100ns': 123456, 'image': 'fixture-image'},
        'profile': profile(root, root / 'data', root / 'platform', 'router')}


def snapshot(root):
    return {str(p.relative_to(root)): (p.read_bytes(), p.stat().st_mtime_ns)
        for p in root.rglob('*') if p.is_file()}


def test_matching_records_and_historical_failure_are_read_only(tmp_path):
    receipt, request, guard = paths(tmp_path, 'router')
    data = evidence(tmp_path)
    write_json(receipt, data)
    write_json(request, {k: data[k] for k in ['protocol', 'token', 'pid', 'identity']})
    write_json(guard.with_suffix('.result.json'), dict(data, outcome='lifespan_error', extra_secret='do-not-print'))
    before = snapshot(tmp_path)
    result = inspector.inspect(tmp_path, tmp_path / 'data', tmp_path / 'platform', 'router')
    assert snapshot(tmp_path) == before
    assert result['request_relation'] == result['terminal_relation'] == 'same_instance'
    assert result['records']['terminal']['outcome'] == 'lifespan_error'
    assert not result['guard_checked'] and not result['readiness_verified'] and not result['consistent_snapshot']
    text = json.dumps(result)
    assert data['token'] not in text and 'do-not-print' not in text and 'fixture-image' not in text
    assert len(text.encode()) < 2048
    receipt.unlink()
    result = inspector.inspect(tmp_path, tmp_path / 'data', tmp_path / 'platform', 'router')
    assert result['terminal_relation'] == 'historical_only' and result['request_relation'] == 'no_identity_record'


def test_different_instance_and_foreign_profile_do_not_confirm_success(tmp_path):
    receipt, request, guard = paths(tmp_path, 'router')
    data = evidence(tmp_path)
    write_json(receipt, data)
    foreign = evidence(tmp_path)
    write_json(request, foreign)
    write_json(guard.with_suffix('.result.json'), dict(foreign, outcome='ok'))
    result = inspector.inspect(tmp_path, tmp_path / 'data', tmp_path / 'platform', 'router')
    assert result['request_relation'] == result['terminal_relation'] == 'different_instance'
    data['profile'] = {}
    write_json(receipt, data)
    assert inspector.inspect(tmp_path, tmp_path / 'data', tmp_path / 'platform', 'router')['records']['identity']['evidence'] == 'foreign_profile'


@pytest.mark.parametrize('raw', [b'{', b'[]', b'\xff', b'x' * 4097, b'[' * 1500 + b'0' + b']' * 1500])
def test_corrupt_records_preserved(tmp_path, raw):
    receipt, _, _ = paths(tmp_path, 'router')
    receipt.parent.mkdir()
    receipt.write_bytes(raw)
    before = snapshot(tmp_path)
    result = inspector.inspect(tmp_path, tmp_path / 'data', tmp_path / 'platform', 'router')
    assert result['records']['identity']['evidence'] in ('invalid_record', 'oversized')
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize('field,value', [('protocol', True), ('token', 'bad'), ('pid', True), ('pid', 2**32),
    ('identity', {}), ('identity', {'creation_100ns': True, 'image': 'image'})])
def test_invalid_schema_redacted(tmp_path, field, value):
    receipt, _, _ = paths(tmp_path, 'router')
    data = evidence(tmp_path)
    data[field] = value
    write_json(receipt, data)
    result = inspector.inspect(tmp_path, tmp_path / 'data', tmp_path / 'platform', 'router')
    assert result['records']['identity'] == {'evidence': 'invalid_record'}


def test_missing_evidence_does_not_create_runtime_or_guard(tmp_path):
    result = inspector.inspect(tmp_path, tmp_path / 'data', tmp_path / 'platform', 'router')
    assert all(row['evidence'] == 'absent' for row in result['records'].values())
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('mode,expected', [('match', 'matches'), ('mismatch', 'mismatch'), ('denied', 'unavailable')])
def test_optional_live_snapshot_is_not_readiness(tmp_path, monkeypatch, mode, expected):
    receipt, _, _ = paths(tmp_path, 'router')
    data = evidence(tmp_path)
    write_json(receipt, data)
    def identity(pid):
        assert pid == 1234
        if mode == 'denied':
            raise PermissionError('fixture denied')
        return data['identity'] if mode == 'match' else {}
    monkeypatch.setattr(inspector, 'process_identity', identity)
    assert inspector.inspect(tmp_path, tmp_path / 'data', tmp_path / 'platform', 'router')['live_identity'] == 'not_checked'
    result = inspector.inspect(tmp_path, tmp_path / 'data', tmp_path / 'platform', 'router', verify_live=True)
    assert result['live_identity'] == expected and not result['readiness_verified']


def test_directory_record_refused_without_open(tmp_path):
    receipt, _, _ = paths(tmp_path, 'router')
    receipt.mkdir(parents=True)
    result = inspector.inspect(tmp_path, tmp_path / 'data', tmp_path / 'platform', 'router')
    assert result['records']['identity']['evidence'] == 'invalid_file'


def test_isolated_cli_missing_root_does_not_create_it(tmp_path):
    local = tmp_path / 'missing'
    result = subprocess.run([sys.executable, '-I', str(SCRIPTS / 'inspect_service_shutdown.py'),
        '--local-root', str(local), '--data-root', str(tmp_path / 'data'),
        '--platform-root', str(tmp_path / 'platform'), '--service', 'router'],
        capture_output=True, text=True, timeout=5)
    assert result.returncode == 1 and json.loads(result.stderr)['error'] == 'FileNotFoundError'
    assert list(tmp_path.iterdir()) == []


@pytest.mark.skipif(os.name != 'nt', reason='Windows OS identity snapshot')
def test_real_live_identity_snapshot_preserves_evidence(tmp_path):
    receipt, _, _ = paths(tmp_path, 'router')
    data = evidence(tmp_path)
    data['pid'] = os.getpid()
    data['identity'] = inspector.process_identity(os.getpid())
    write_json(receipt, data)
    before = snapshot(tmp_path)
    result = inspector.inspect(tmp_path, tmp_path / 'data', tmp_path / 'platform', 'router', verify_live=True)
    assert result['live_identity'] == 'matches' and not result['guard_checked']
    assert snapshot(tmp_path) == before


def test_isolated_cli_preserves_valid_terminal_record(tmp_path):
    _, _, guard = paths(tmp_path, 'router')
    write_json(guard.with_suffix('.result.json'), dict(evidence(tmp_path), outcome='server_error'))
    before = snapshot(tmp_path)
    result = subprocess.run([sys.executable, '-I', str(SCRIPTS / 'inspect_service_shutdown.py'),
        '--local-root', str(tmp_path), '--data-root', str(tmp_path / 'data'),
        '--platform-root', str(tmp_path / 'platform'), '--service', 'router'],
        capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['terminal_relation'] == 'historical_only'
    assert snapshot(tmp_path) == before and len(result.stdout.encode()) < 2048
