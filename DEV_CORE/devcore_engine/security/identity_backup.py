"""Offline private identity snapshots; restore publishes only after access revocation."""

from contextlib import contextmanager, closing
import hashlib
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
from uuid import uuid4

from .administration import audit
from .identity import IdentityUnavailable, store_path
from .private_store import check_store_protection
from .secret_files import protect_empty_directory, protect_reserved_file


def validate_snapshot(conn):
    versions = conn.execute("SELECT version FROM identity_schema").fetchall()
    if versions != [(4,)]:
        raise IdentityUnavailable("Private snapshot requires schema 4")
    if conn.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
        raise IdentityUnavailable("Identity integrity check failed")
    if conn.execute("PRAGMA foreign_key_check").fetchall():
        raise IdentityUnavailable("Identity foreign key check failed")
    if conn.execute("SELECT bootstrapped FROM identity_admin_state WHERE id=1").fetchall() != [(1,)]:
        raise IdentityUnavailable("Bootstrapped identity snapshot required")
    if not conn.execute("SELECT 1 FROM identity_instance_admins LIMIT 1").fetchone():
        raise IdentityUnavailable("Existing administrator required")


@contextmanager
def locked_snapshot_source(path):
    protection = check_store_protection(path)  # Original path, before resolving aliases.
    with closing(sqlite3.connect(f"{store_path(path).as_uri()}?mode=rw", uri=True, timeout=1)) as conn:
        conn.execute("PRAGMA locking_mode=EXCLUSIVE")
        conn.execute("BEGIN EXCLUSIVE")
        current = check_store_protection(path)
        if current["owner_sid"] != protection["owner_sid"]:
            raise IdentityUnavailable("Snapshot operator changed")
        validate_snapshot(conn)
        # Retain EXCLUSIVE locks until close, without an active write transaction:
        # sqlite3.backup on a source in a write transaction would keep returning BUSY.
        conn.commit()
        conn.execute("PRAGMA query_only=ON")
        yield conn, current


def reserve_pending(destination):
    destination = Path(destination)
    if not destination.is_absolute():
        raise ValueError("Absolute identity destination required")
    protect_empty_directory(destination.parent)
    pending = destination.with_name("." + destination.name + ".pending-" + uuid4().hex)
    descriptor = os.open(pending, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(descriptor)
    protect_reserved_file(pending)
    return pending


def copy_snapshot(source, pending):
    deadline = time.monotonic() + 30
    def progress(status, remaining, total):
        if status in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED) or time.monotonic() > deadline:
            raise IdentityUnavailable("Snapshot copy unavailable or time limit exceeded")
    with closing(sqlite3.connect(f"{pending.as_uri()}?mode=rw", uri=True, timeout=1)) as target:
        source.backup(target, pages=256, progress=progress, sleep=0.05)
        # A portable archive and unpublished restore stage contain no live WAL state.
        if target.execute("PRAGMA journal_mode=DELETE").fetchone()[0] != "delete":
            raise IdentityUnavailable("Standalone identity snapshot required")
        validate_snapshot(target)


def file_digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def publish(pending, destination):
    protection = check_store_protection(pending)
    if protection["sidecars"]:
        raise IdentityUnavailable("Snapshot has remaining SQLite journals")
    with pending.open("r+b") as stream:
        stream.flush()
        os.fsync(stream.fileno())
    digest = file_digest(pending)
    # Same private directory, NTFS hard link, exclusive publication; never overwrite.
    os.link(pending, destination)
    pending.unlink()
    return {"store": str(destination), "sha256": digest, "operator_sid": protection["owner_sid"]}


def backup_identity_store(path, destination):
    """Logical source unchanged; archive retains credentials and must not be activated."""
    destination = Path(destination)
    with locked_snapshot_source(path) as (source, _):
        pending = reserve_pending(destination)
        copy_snapshot(source, pending)
    result = publish(pending, destination)
    result["archive_only"] = True
    return result


def restore_identity_store(backup, destination, expected_sha256):
    """New private store only; old passwords/capabilities cannot regain access."""
    if not isinstance(expected_sha256, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", expected_sha256):
        raise ValueError("Expected SHA-256 required")
    expected_sha256 = expected_sha256.lower()
    protection = check_store_protection(backup)
    if protection["sidecars"] or not secrets.compare_digest(file_digest(backup), expected_sha256):
        raise IdentityUnavailable("Standalone backup digest differs")
    destination = Path(destination)
    with locked_snapshot_source(backup) as (source, _):
        if source.execute("PRAGMA journal_mode").fetchone()[0] != "delete":
            raise IdentityUnavailable("Restore requires a standalone DELETE-mode archive")
        if not secrets.compare_digest(file_digest(backup), expected_sha256):
            raise IdentityUnavailable("Backup changed before restore")
        pending = reserve_pending(destination)
        copy_snapshot(source, pending)
    with closing(sqlite3.connect(f"{pending.as_uri()}?mode=rw", uri=True, timeout=1)) as target, target:
        target.execute("PRAGMA foreign_keys=ON")
        from .passwords import hash_password
        # Keep existing administrators eligible for OS recovery, with separate
        # unknown random passwords. Other accounts require a newly assigned secret.
        timestamp = time.time()
        administrators = target.execute("SELECT user_id FROM identity_instance_admins").fetchall()
        resets = [(user, hash_password(secrets.token_urlsafe(32))) for (user,) in administrators]
        target.execute("BEGIN EXCLUSIVE")
        target.execute("UPDATE identity_users SET enabled=0")
        target.execute("DELETE FROM identity_passwords WHERE user_id NOT IN (SELECT user_id FROM identity_instance_admins)")
        for user, encoded in resets:
            target.execute("""INSERT INTO identity_passwords VALUES (?,?,1,?,0,0)
                ON CONFLICT(user_id) DO UPDATE SET password_hash=excluded.password_hash,
                version=identity_passwords.version+1,updated_at=excluded.updated_at,
                failures=0,blocked_until=0""", (user, encoded, timestamp))
        for table in ("identity_credentials", "identity_admin_credentials", "identity_browser_sessions"):
            target.execute(f"UPDATE {table} SET revoked=1")
        audit(target, "windows:" + protection["owner_sid"], "identity.restore-local", "instance", timestamp,
              details={"backup_sha256": expected_sha256, "all_credentials_revoked": True,
                       "all_accounts_disabled": True, "password_reset_required": True})
        # Include audit-trigger effects in the guarantee before committing/publishing.
        for table in ("identity_credentials", "identity_admin_credentials", "identity_browser_sessions"):
            if target.execute(f"SELECT 1 FROM {table} WHERE revoked<>1 LIMIT 1").fetchone():
                raise IdentityUnavailable("Restore did not revoke all access")
        if target.execute("SELECT 1 FROM identity_users WHERE enabled<>0 LIMIT 1").fetchone():
            raise IdentityUnavailable("Restore did not disable all accounts")
        if dict(target.execute("SELECT user_id,password_hash FROM identity_passwords").fetchall()) != dict(resets):
            raise IdentityUnavailable("Restore did not reset all passwords")
        validate_snapshot(target)
    result = publish(pending, destination)
    result["relogin_required"] = True
    return result
