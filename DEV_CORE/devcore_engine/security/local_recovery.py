"""Explicit local recovery of an existing administrator on a private NTFS store.

The Windows owner is trusted. No credential, HTTP handler or new admin role is
created here. Run as maintenance after stopping services using this store.
"""

from contextlib import closing
import sqlite3
import time

from devcore_engine.context import validate_project_id
from .administration import audit, require_admin_schema
from .identity import ProjectAccessDenied, connect_existing, store_path
from .private_store import check_store_protection


def recovery_target(conn, user):
    require_admin_schema(conn)
    state = conn.execute("SELECT bootstrapped FROM identity_admin_state WHERE id=1").fetchone()
    if state is None or state[0] != 1:
        raise ProjectAccessDenied("Local recovery requires completed initial administration")
    target = conn.execute("""SELECT u.enabled FROM identity_users u
        JOIN identity_instance_admins a ON a.user_id=u.id
        JOIN identity_passwords p ON p.user_id=u.id WHERE u.id=?""", (user,)).fetchone()
    if target is None:
        raise ProjectAccessDenied("Local recovery requires an existing administrator with a password")
    return bool(target[0])


def preflight_recovery(path, user):
    """Validate native protection and target before prompting for a new secret."""
    user = validate_project_id(user)
    protection = check_store_protection(path)
    with closing(connect_existing(path)) as conn:
        enabled = recovery_target(conn, user)
    return {"operator_sid": protection["owner_sid"], "previously_enabled": enabled}


def recover_admin(path, user, password, *, now=None):
    """Reset/reactivate only the named existing admin; audit and revocations are atomic."""
    user = validate_project_id(user)
    admission = preflight_recovery(path, user)
    from .passwords import hash_password, replace_password
    encoded = hash_password(password)  # Before acquiring the maintenance write lock.
    # Set EXCLUSIVE before any schema access, including in WAL mode. Never create a DB.
    with closing(sqlite3.connect(f"{store_path(path).as_uri()}?mode=rw", uri=True, timeout=1)) as conn, conn:
        conn.execute("PRAGMA foreign_keys=ON")
        if conn.execute("PRAGMA locking_mode=EXCLUSIVE").fetchone()[0] != "exclusive":
            raise ProjectAccessDenied("Exclusive local recovery unavailable")
        conn.execute("BEGIN EXCLUSIVE")
        protection = check_store_protection(path)
        if protection["owner_sid"] != admission["operator_sid"]:
            raise ProjectAccessDenied("Recovery operator changed")
        enabled = recovery_target(conn, user)  # Repeat admission after expensive hashing.
        timestamp = time.time() if now is None else now
        replace_password(conn, user, encoded, timestamp)
        conn.execute("UPDATE identity_users SET enabled=1 WHERE id=?", (user,))
        audit(conn, "windows:" + protection["owner_sid"], "admin.recover-local", user, timestamp,
              details={"operator_sid": protection["owner_sid"], "previously_enabled": enabled,
                       "maintenance": True})
    return {"user": user, "operator_sid": protection["owner_sid"], "relogin_required": True}
