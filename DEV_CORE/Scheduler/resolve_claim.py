"""Explicit local maintenance: confirm success or skip, never repeat a command."""
import argparse
from datetime import datetime, timezone
import getpass
import json
import os
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scheduler_lock import SchedulerLeaseLock


def resolve_claim(database: Path, *, claim_id: int, expected_status: str,
                  action: str, evidence: str) -> dict:
    if type(claim_id) is not int or not 1 <= claim_id < 2**63:
        raise ValueError('Invalid claim ID')
    if expected_status not in ('running', 'error'):
        raise ValueError('Expected status must be running or error')
    if action not in ('confirm-success', 'skip'):
        raise ValueError('Action must be confirm-success or skip')
    if not isinstance(evidence, str) or not evidence.strip() or len(evidence.encode('utf-8')) > 4096:
        raise ValueError('Evidence required, at most 4096 UTF-8 bytes')
    path = Path(database).resolve(strict=True)
    # Fixed sibling guard: caller cannot choose an unrelated lock to bypass it.
    if path.name != 'scheduler.db' or not path.is_file():
        raise ValueError('Expected an existing scheduler.db')
    with path.open('rb') as stream:
        header = stream.read(100)
    if header[:16] != b'SQLite format 3\x00' or header[18:20] != b'\x01\x01':
        raise ValueError('Expected a DELETE-journal SQLite database')
    lock = SchedulerLeaseLock(path.parent / 'scheduler.lock', 'claim-maintenance')
    with lock.maintenance_guard():
        conn = sqlite3.connect(path.as_uri() + '?mode=rw', uri=True, timeout=1)
        try:
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute('SELECT status,idempotency_key FROM run_history WHERE id=?', (claim_id,)).fetchone()
            if row is None or row[0] != expected_status:
                raise ValueError('Claim absent or status changed; inspect again')
            new_status = 'ok' if action == 'confirm-success' else 'skipped'
            conn.execute('''CREATE TABLE IF NOT EXISTS claim_resolution_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_id INTEGER NOT NULL, idempotency_key TEXT NOT NULL,
                previous_status TEXT NOT NULL, resolved_status TEXT NOT NULL,
                action TEXT NOT NULL, evidence TEXT NOT NULL,
                resolved_at TEXT NOT NULL, local_account TEXT NOT NULL,
                process_id INTEGER NOT NULL)''')
            timestamp = datetime.now(timezone.utc).isoformat()
            # Local account is metadata, not authenticated API identity/SID proof.
            cursor = conn.execute('''INSERT INTO claim_resolution_audit
                (claim_id,idempotency_key,previous_status,resolved_status,action,evidence,
                 resolved_at,local_account,process_id) VALUES (?,?,?,?,?,?,?,?,?)''',
                (claim_id, row[1], expected_status, new_status, action, evidence,
                 timestamp, getpass.getuser(), os.getpid()))
            audit_id = cursor.lastrowid
            updated = conn.execute('UPDATE run_history SET status=? WHERE id=? AND status=?',
                (new_status, claim_id, expected_status))
            if updated.rowcount != 1:
                raise ValueError('Claim changed during resolution')
            conn.commit()
            return {'claim_id': claim_id, 'previous_status': expected_status,
                    'resolved_status': new_status, 'audit_id': audit_id,
                    'command_executed': False, 'schedule_modified': False}
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True, type=Path)
    parser.add_argument('--claim-id', required=True, type=int)
    parser.add_argument('--expected-status', required=True, choices=('running', 'error'))
    parser.add_argument('--action', required=True, choices=('confirm-success', 'skip'))
    parser.add_argument('--evidence', required=True)
    args = parser.parse_args(argv)
    try:
        result = resolve_claim(args.database, claim_id=args.claim_id,
            expected_status=args.expected_status, action=args.action, evidence=args.evidence)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, sqlite3.Error) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=True), file=sys.stderr)
        return 1
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
