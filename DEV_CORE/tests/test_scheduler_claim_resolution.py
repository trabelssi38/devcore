"""Controlled maintenance never retries effects and audits in the same transaction."""
from pathlib import Path
import sqlite3
import subprocess
import sys
import json

import pytest

SCHEDULER = Path(__file__).resolve().parents[1] / 'Scheduler'
sys.path.insert(0, str(SCHEDULER))
import scheduler_history
from scheduler_lock import SchedulerLeaseLock
from resolve_claim import resolve_claim


def fixture_db(tmp_path):
    path = tmp_path / 'scheduler.db'
    assert scheduler_history.record_run('fixture', 'date', 'started', 2, 'running',
        error='original', db_path=path)
    return path


def resolve(path, **kwargs):
    return resolve_claim(path, **dict({'claim_id': 1, 'expected_status': 'running',
        'action': 'confirm-success', 'evidence': 'Fixture effect independently verified'}, **kwargs))


@pytest.mark.parametrize('action,status', [('confirm-success', 'ok'), ('skip', 'skipped')])
def test_resolution_audits_and_preserves_execution_details(tmp_path, action, status):
    path = fixture_db(tmp_path)
    registry = tmp_path / 'jobs.json'
    registry.write_bytes(b'fixture unchanged')
    result = resolve(path, action=action)
    assert not result['command_executed'] and not result['schedule_modified']
    assert result['resolved_status'] == status
    with sqlite3.connect(path) as conn:
        assert conn.execute('SELECT status,run_at,duration,error FROM run_history').fetchone() == (status, 'started', 2, 'original')
        row = conn.execute('SELECT claim_id,previous_status,resolved_status,evidence,local_account FROM claim_resolution_audit').fetchone()
        assert row[:3] == (1, 'running', status) and row[3] and row[4]
    assert registry.read_bytes() == b'fixture unchanged'
    assert scheduler_history.is_run_completed('fixture', 'date', path)
    with pytest.raises(ValueError, match='status changed'):
        resolve(path)
    with sqlite3.connect(path) as conn:
        assert conn.execute('SELECT count(*) FROM claim_resolution_audit').fetchone()[0] == 1


def test_active_lease_or_busy_cycle_refuses_without_db_mutation(tmp_path):
    path = fixture_db(tmp_path)
    before = path.read_bytes()
    lock = SchedulerLeaseLock(tmp_path / 'scheduler.lock', 'fixture')
    assert lock.acquire()
    with pytest.raises(RuntimeError, match='Stop the scheduler'):
        resolve(path)
    with lock.hold():
        with pytest.raises(OSError):
            resolve(path)
    assert path.read_bytes() == before


@pytest.mark.parametrize('failure', ['audit', 'update'])
def test_failure_rolls_back_both_history_and_audit(tmp_path, failure):
    path = fixture_db(tmp_path)
    resolve(path, action='skip')  # Create audited schema, then restore fixture state.
    with sqlite3.connect(path) as conn:
        conn.execute("UPDATE run_history SET status='running'")
        target = 'claim_resolution_audit' if failure == 'audit' else 'run_history'
        operation = 'INSERT' if failure == 'audit' else 'UPDATE'
        conn.execute(f"CREATE TRIGGER fixture_denial BEFORE {operation} ON {target} BEGIN SELECT RAISE(ABORT,'fixture failure'); END")
    with pytest.raises(sqlite3.IntegrityError):
        resolve(path)
    with sqlite3.connect(path) as conn:
        assert conn.execute('SELECT status FROM run_history').fetchone()[0] == 'running'
        assert conn.execute('SELECT count(*) FROM claim_resolution_audit').fetchone()[0] == 1


@pytest.mark.parametrize('kwargs', [{'claim_id': True}, {'claim_id': 0}, {'claim_id': 2**63},
    {'expected_status': 'ok'}, {'action': 'retry'}, {'evidence': ''}, {'evidence': 'é' * 2049}])
def test_invalid_request_creates_nothing(tmp_path, kwargs):
    with pytest.raises(ValueError):
        resolve(tmp_path / 'absent' / 'scheduler.db', **kwargs)
    assert list(tmp_path.iterdir()) == []


def test_cli_and_corrupt_lease(tmp_path):
    path = fixture_db(tmp_path)
    command = [sys.executable, '-I', str(SCHEDULER / 'resolve_claim.py'), '--database', str(path),
        '--claim-id', '1', '--expected-status', 'running', '--action', 'skip', '--evidence', 'fixture deliberate skip']
    lease = tmp_path / 'scheduler.lock'
    lease.write_bytes(b'broken')
    before = path.read_bytes()
    failed = subprocess.run(command, capture_output=True, text=True, timeout=10)
    assert failed.returncode == 1 and not failed.stdout
    assert 'error' in json.loads(failed.stderr)
    assert path.read_bytes() == before and lease.read_bytes() == b'broken'
    lease.unlink()
    result = subprocess.run(command, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['resolved_status'] == 'skipped'


def test_error_resolution_and_absent_claim(tmp_path):
    path = fixture_db(tmp_path)
    before = path.read_bytes()
    with pytest.raises(ValueError, match='Claim absent'):
        resolve(path, claim_id=99)
    assert path.read_bytes() == before
    with sqlite3.connect(path) as conn:
        conn.execute("UPDATE run_history SET status='error'")
    assert resolve(path, expected_status='error')['resolved_status'] == 'ok'


def test_missing_database_and_wal_refused(tmp_path):
    with pytest.raises(FileNotFoundError):
        resolve(tmp_path / 'absent' / 'scheduler.db')
    assert not (tmp_path / 'absent').exists()
    path = fixture_db(tmp_path)
    with sqlite3.connect(path) as conn:
        assert conn.execute('PRAGMA journal_mode=WAL').fetchone()[0] == 'wal'
    before = path.read_bytes()
    with pytest.raises(ValueError, match='DELETE-journal'):
        resolve(path)
    assert path.read_bytes() == before
    assert not (tmp_path / 'scheduler.lock.guard').exists()
