"""Local password recipe: Argon2id, bounded verification and atomic session admission."""

from contextlib import closing
from functools import lru_cache
import hashlib
import json
import secrets
import threading
import time
from uuid import uuid4

from .identity import (
    AuthenticationRequired, IdentityUnavailable, ProjectAccessDenied, ROLES,
    connect_existing,
)
from .browser_sessions import insert_session
from devcore_engine.context import validate_project_id

try:
    from argon2 import PasswordHasher
    from argon2.exceptions import InvalidHashError, VerificationError
    from argon2.profiles import RFC_9106_LOW_MEMORY
except ImportError as exc:
    raise IdentityUnavailable("Password hashing dependency unavailable") from exc

MIN_PASSWORD_LENGTH = 15
MAX_PASSWORD_LENGTH = 256
MAX_FAILURES = 5
COOLDOWN_SECONDS = 60
_slots = threading.BoundedSemaphore(2)


class LoginBusy(RuntimeError):
    pass


@lru_cache(maxsize=1)
def hasher():
    return PasswordHasher.from_parameters(RFC_9106_LOW_MEMORY)


@lru_cache(maxsize=1)
def dummy_hash():
    return hasher().hash(secrets.token_urlsafe(32))


def require_passwords(conn):
    if conn.execute("SELECT version FROM identity_schema").fetchone()[0] not in (3, 4):
        raise IdentityUnavailable("Password schema requires explicit upgrade")


def upgrade_password_store(path):
    """Explicit v2→v3 migration; preserves memberships, credentials and sessions."""
    with closing(connect_existing(path, read_only=False)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        version = conn.execute("SELECT version FROM identity_schema").fetchone()[0]
        if version in (3, 4):
            return
        if version != 2:
            raise IdentityUnavailable("Upgrade browser sessions before passwords")
        conn.execute("""CREATE TABLE identity_passwords(
            user_id TEXT PRIMARY KEY REFERENCES identity_users(id), password_hash TEXT NOT NULL,
            version INTEGER NOT NULL CHECK(version > 0), updated_at REAL NOT NULL,
            failures INTEGER NOT NULL DEFAULT 0 CHECK(failures BETWEEN 0 AND 5),
            blocked_until REAL NOT NULL DEFAULT 0)""")
        conn.execute("UPDATE identity_schema SET version=3")


def hash_password(password):
    if not isinstance(password, str) or not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH:
        raise ValueError("Password must have 15..256 characters")
    return hasher().hash(password)


def replace_password(conn, user_id, encoded, timestamp):
    """Caller owns the write transaction and any administrative authorization."""
    require_passwords(conn)
    if conn.execute("SELECT id FROM identity_users WHERE id=?", (user_id,)).fetchone() is None:
        raise ValueError("Existing user required")
    conn.execute("""INSERT INTO identity_passwords(user_id,password_hash,version,updated_at)
        VALUES (?,?,1,?) ON CONFLICT(user_id) DO UPDATE SET
        password_hash=excluded.password_hash,version=identity_passwords.version+1,
        updated_at=excluded.updated_at,failures=0,blocked_until=0""", (user_id, encoded, timestamp))
    conn.execute("UPDATE identity_credentials SET revoked=1 WHERE user_id=?", (user_id,))
    conn.execute("""UPDATE identity_browser_sessions SET revoked=1 WHERE credential_id IN
        (SELECT id FROM identity_credentials WHERE user_id=?)""", (user_id,))
    if conn.execute("SELECT version FROM identity_schema").fetchone()[0] == 4:
        conn.execute("UPDATE identity_admin_credentials SET revoked=1 WHERE user_id=?", (user_id,))


def set_password(path, user_id, password, *, now=None):
    """Local operator recovery: revoke all prior credentials, leave roles/enabled alone."""
    user_id = validate_project_id(user_id)
    encoded = hash_password(password)  # Outside the SQLite write transaction.
    timestamp = time.time() if now is None else now
    with closing(connect_existing(path, read_only=False)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        replace_password(conn, user_id, encoded, timestamp)


def verify_password(encoded, password):
    try:
        return hasher().verify(encoded, password)
    except InvalidHashError as exc:
        raise IdentityUnavailable("Password store contains an invalid hash") from exc
    except VerificationError:
        return False


def create_password_session(path, user_id, password, project, origin, *, previous=None, now=None):
    user_id, project = validate_project_id(user_id), validate_project_id(project)
    def admit(conn, user_id, timestamp):
        membership = conn.execute("SELECT role FROM identity_memberships WHERE user_id=? AND project_id=?", (user_id, project)).fetchone()
        if membership is None:
            raise ProjectAccessDenied("Project action denied")
        actions = sorted(ROLES[membership[0]])
        identifier = str(uuid4())
        # Internal source credential: raw token is neither returned nor delivered.
        token_hash = hashlib.sha256(secrets.token_bytes(32)).hexdigest()
        conn.execute("INSERT INTO identity_credentials VALUES (?,?,?,?,?,0,?,?)", (
            identifier, user_id, token_hash, timestamp, timestamp + 1800, json.dumps([project]), json.dumps(actions),
        ))
        credential = conn.execute("""SELECT c.*,u.enabled FROM identity_credentials c
            JOIN identity_users u ON u.id=c.user_id WHERE c.id=?""", (identifier,)).fetchone()
        return insert_session(conn, credential, project, origin, timestamp, previous=previous)
    return authenticate_password(path, user_id, password, admit, now=now)


def authenticate_password(path, user_id, password, admit, *, now=None):
    """Shared bounded password admission; callback executes after transactional recheck."""
    user_id = validate_project_id(user_id)
    if not isinstance(password, str) or not 1 <= len(password) <= MAX_PASSWORD_LENGTH:
        raise AuthenticationRequired("Invalid credentials")
    if not _slots.acquire(blocking=False):
        raise LoginBusy("Password verification capacity reached")
    try:
        return _authenticate_password(path, user_id, password, admit, now=now)
    finally:
        _slots.release()


def _authenticate_password(path, user_id, password, admit, *, now):
    timestamp = time.time() if now is None else now
    with closing(connect_existing(path)) as conn:
        require_passwords(conn)
        snapshot = conn.execute("""SELECT p.*,u.enabled FROM identity_passwords p
            JOIN identity_users u ON u.id=p.user_id WHERE p.user_id=?""", (user_id,)).fetchone()
    blocked = snapshot is not None and timestamp < snapshot["blocked_until"]
    encoded = snapshot["password_hash"] if snapshot is not None and not blocked else dummy_hash()
    verified = verify_password(encoded, password)
    if snapshot is None:
        raise AuthenticationRequired("Invalid credentials")
    valid = verified and snapshot["enabled"] == 1 and not blocked
    replacement = hasher().hash(password) if valid and hasher().check_needs_rehash(encoded) else None
    admitted = None
    with closing(connect_existing(path, read_only=False)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        require_passwords(conn)
        current = conn.execute("""SELECT p.*,u.enabled FROM identity_passwords p
            JOIN identity_users u ON u.id=p.user_id WHERE p.user_id=?""", (user_id,)).fetchone()
        timestamp = time.time() if now is None else now
        # A reset during expensive verification cannot admit the old password.
        if current is None or (current["version"], current["password_hash"]) != (snapshot["version"], snapshot["password_hash"]):
            raise AuthenticationRequired("Invalid credentials")
        if not valid or current["enabled"] != 1 or timestamp < current["blocked_until"]:
            if current["enabled"] == 1 and timestamp >= current["blocked_until"]:
                failures = (0 if current["failures"] == MAX_FAILURES else current["failures"]) + 1
                until = timestamp + COOLDOWN_SECONDS if failures == MAX_FAILURES else 0
                conn.execute("UPDATE identity_passwords SET failures=?,blocked_until=? WHERE user_id=?", (failures, until, user_id))
        else:
            admitted = admit(conn, user_id, timestamp)
            conn.execute("UPDATE identity_passwords SET password_hash=?,failures=0,blocked_until=0 WHERE user_id=?",
                         (replacement or encoded, user_id))
    if admitted is None:
        raise AuthenticationRequired("Invalid credentials")
    return admitted
