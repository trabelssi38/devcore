"""Expiring browser sessions bound to an existing scoped API credential."""

from contextlib import closing
from dataclasses import dataclass
import hashlib
import hmac
import secrets
import time
from uuid import uuid4

from .identity import (
    AuthenticationRequired, IdentityUnavailable, ProjectAccessDenied, READ, WRITE, CONTEXT_READ, AUDIT_READ,
    Principal, SqliteIdentityProvider, connect_existing, principal_for_credential,
)

COOKIE = "devcore_session"


def upgrade_session_store(path):
    """Explicit transactional v1→v2 upgrade; never invoked by HTTP."""
    with closing(connect_existing(path, read_only=False)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        if conn.execute("SELECT version FROM identity_schema").fetchone()[0] in (2, 3, 4):
            return
        conn.execute("""CREATE TABLE identity_browser_sessions(
            id TEXT PRIMARY KEY, credential_id TEXT NOT NULL REFERENCES identity_credentials(id),
            session_hash TEXT NOT NULL UNIQUE, project_id TEXT NOT NULL, origin TEXT NOT NULL,
            issued_at REAL NOT NULL, expires_at REAL NOT NULL,
            revoked INTEGER NOT NULL DEFAULT 0 CHECK(revoked IN (0,1)))""")
        conn.execute("UPDATE identity_schema SET version=2")


def csrf_for_session(secret):
    return hmac.new(secret.encode(), b"devcore-browser-csrf-v1", hashlib.sha256).hexdigest()


def digest(secret):
    if not isinstance(secret, str) or not secret or len(secret) > 512:
        raise AuthenticationRequired("Invalid session")
    return hashlib.sha256(secret.encode()).hexdigest()


@dataclass(frozen=True)
class BrowserSession:
    principal: Principal
    session_id: str
    project_id: str
    expires_at: float
    actions: tuple[str, ...]


def permitted_actions(conn, credential, project, timestamp):
    """Describe current rights using the same checks as resource authorization."""
    actions = []
    for action in (READ, WRITE, CONTEXT_READ, AUDIT_READ):
        try:
            principal_for_credential(conn, credential, project, action, timestamp)
        except ProjectAccessDenied:
            continue
        actions.append(action)
    return tuple(actions)


def create_session(path, authorization, project, origin, *, previous=None, now=None, ttl_seconds=1800):
    if type(ttl_seconds) is not int or not 60 <= ttl_seconds <= 1800:
        raise ValueError("Session lifetime must be 60..1800 seconds")
    timestamp = time.time() if now is None else now
    principal = SqliteIdentityProvider(path).authorize(authorization, project, READ, now=timestamp)
    with closing(connect_existing(path, read_only=False)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        require_sessions(conn)
        row = conn.execute("""SELECT c.*,u.enabled FROM identity_credentials c
            JOIN identity_users u ON u.id=c.user_id WHERE c.id=?""", (principal.credential_id,)).fetchone()
        return insert_session(conn, row, project, origin, timestamp, previous=previous, ttl_seconds=ttl_seconds)


def insert_session(conn, credential, project, origin, timestamp, *, previous=None, ttl_seconds=1800):
    """Caller owns the transaction, including source credential admission."""
    require_sessions(conn)
    principal = principal_for_credential(conn, credential, project, READ, timestamp)
    actions = permitted_actions(conn, credential, project, timestamp)
    expires_at = min(timestamp + ttl_seconds, credential["expires_at"])
    secret, identifier = secrets.token_urlsafe(32), str(uuid4())
    conn.execute("INSERT INTO identity_browser_sessions VALUES (?,?,?,?,?,?,?,0)", (
        identifier, principal.credential_id, digest(secret), project, origin, timestamp, expires_at,
    ))
    if previous:
        try:
            previous_hash = digest(previous)
        except AuthenticationRequired:
            previous_hash = None
        if previous_hash:
            conn.execute("UPDATE identity_browser_sessions SET revoked=1 WHERE session_hash=?", (previous_hash,))
    return BrowserSession(principal, identifier, project, expires_at, actions), secret


def require_sessions(conn):
    if conn.execute("SELECT version FROM identity_schema").fetchone()[0] not in (2, 3, 4):
        raise IdentityUnavailable("Browser session schema requires explicit upgrade")


def authorize_session(path, secret, project, action, origin, *, csrf=None, mutate=False, now=None):
    timestamp = time.time() if now is None else now
    with closing(connect_existing(path)) as conn:
        require_sessions(conn)
        session = conn.execute("SELECT * FROM identity_browser_sessions WHERE session_hash=?", (digest(secret),)).fetchone()
        if session is None or session["revoked"] != 0 or not session["issued_at"] <= timestamp < session["expires_at"]:
            raise AuthenticationRequired("Invalid or expired session")
        if project != session["project_id"] or origin != session["origin"]:
            raise ProjectAccessDenied("Session project or origin denied")
        if mutate and (not isinstance(csrf, str) or not csrf.isascii() or len(csrf) != 64 or not hmac.compare_digest(csrf_for_session(secret), csrf)):
            raise ProjectAccessDenied("Invalid session CSRF")
        credential = conn.execute("""SELECT c.*,u.enabled FROM identity_credentials c
            JOIN identity_users u ON u.id=c.user_id WHERE c.id=?""", (session["credential_id"],)).fetchone()
        principal = principal_for_credential(conn, credential, project, action, timestamp)
        actions = permitted_actions(conn, credential, project, timestamp)
        return BrowserSession(principal, session["id"], project, session["expires_at"], actions)


def session_info(path, secret, origin):
    with closing(connect_existing(path)) as conn:
        require_sessions(conn)
        row = conn.execute("SELECT project_id FROM identity_browser_sessions WHERE session_hash=?", (digest(secret),)).fetchone()
        if row is None:
            raise AuthenticationRequired("Invalid session")
    return authorize_session(path, secret, row[0], READ, origin)


def revoke_session(path, secret):
    with closing(connect_existing(path, read_only=False)) as conn, conn:
        require_sessions(conn)
        conn.execute("UPDATE identity_browser_sessions SET revoked=1 WHERE session_hash=?", (digest(secret),))
