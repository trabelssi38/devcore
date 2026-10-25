"""Local qualification store for individual, scoped API credentials.

No implicit initialization, password handling, global account or shared token.
The deployed team persistence adapter remains part of the PostgreSQL cutover.
"""

from contextlib import closing
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import secrets
import sqlite3
import time
from typing import Protocol
from uuid import uuid4

from devcore_engine.context import validate_project_id


READ = "task.read"
WRITE = "task.mutate"
CONTEXT_READ = "context.read"
AUDIT_READ = "task.audit.read"
ACTIONS = frozenset({READ, WRITE, CONTEXT_READ, AUDIT_READ})
ROLES = {"reader": frozenset({READ, CONTEXT_READ}),
         "contributor": frozenset({READ, WRITE, CONTEXT_READ}), "owner": ACTIONS}


class IdentityUnavailable(RuntimeError):
    pass


class AuthenticationRequired(PermissionError):
    pass


class ProjectAccessDenied(PermissionError):
    pass


@dataclass(frozen=True)
class Principal:
    user_id: str
    credential_id: str
    project_id: str
    action: str


class IdentityProvider(Protocol):
    def authorize(self, authorization: str, project: str, action: str) -> Principal: ...


def store_path(path):
    path = Path(path)
    if not path.is_absolute():
        raise ValueError("Identity store requires an absolute path")
    return path.resolve()


def connect_existing(path, *, read_only=True):
    mode = "ro" if read_only else "rw"
    try:
        conn = sqlite3.connect(f"{store_path(path).as_uri()}?mode={mode}", uri=True, timeout=5)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        if read_only:
            conn.execute("PRAGMA query_only=ON")
        rows = conn.execute("SELECT version FROM identity_schema").fetchall()
        if len(rows) != 1 or rows[0][0] not in (1, 2, 3, 4):
            raise IdentityUnavailable("Unsupported identity schema")
        return conn
    except (sqlite3.Error, IdentityUnavailable) as exc:
        if "conn" in locals():
            conn.close()
        raise IdentityUnavailable("Individual identity store unavailable") from exc


def initialize_store(path):
    """Explicit local administration only; API readers never call this."""
    path = store_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        existing = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        if existing:
            with closing(connect_existing(path)):
                return
        conn.execute("CREATE TABLE identity_schema(version INTEGER NOT NULL)")
        conn.execute("INSERT INTO identity_schema VALUES (1)")
        conn.execute("""CREATE TABLE identity_users(
            id TEXT PRIMARY KEY, enabled INTEGER NOT NULL CHECK(enabled IN (0,1)))""")
        conn.execute("""CREATE TABLE identity_memberships(
            user_id TEXT NOT NULL REFERENCES identity_users(id), project_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('reader','contributor','owner')),
            PRIMARY KEY(user_id,project_id))""")
        conn.execute("""CREATE TABLE identity_credentials(
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES identity_users(id),
            token_hash TEXT NOT NULL UNIQUE, issued_at REAL NOT NULL,
            expires_at REAL NOT NULL, revoked INTEGER NOT NULL DEFAULT 0 CHECK(revoked IN (0,1)),
            projects TEXT NOT NULL, actions TEXT NOT NULL)""")


def add_user(path, user_id):
    user_id = validate_project_id(user_id)
    with closing(connect_existing(path, read_only=False)) as conn, conn:
        conn.execute("INSERT INTO identity_users(id,enabled) VALUES (?,1)", (user_id,))


def set_membership(path, user_id, project, role):
    user_id, project = validate_project_id(user_id), validate_project_id(project)
    if role not in ROLES:
        raise ValueError("Unknown project role")
    with closing(connect_existing(path, read_only=False)) as conn, conn:
        conn.execute("""INSERT INTO identity_memberships VALUES (?,?,?)
            ON CONFLICT(user_id,project_id) DO UPDATE SET role=excluded.role""", (user_id, project, role))


def remove_membership(path, user_id, project):
    with closing(connect_existing(path, read_only=False)) as conn, conn:
        conn.execute("DELETE FROM identity_memberships WHERE user_id=? AND project_id=?", (user_id, project))


def issue_credential(path, user_id, projects, actions, *, ttl_seconds=3600, now=None):
    timestamp = time.time() if now is None else now
    with closing(connect_existing(path, read_only=False)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        return insert_credential(conn, user_id, projects, actions, ttl_seconds, timestamp)


def insert_credential(conn, user_id, projects, actions, ttl_seconds, timestamp):
    """Caller owns the transaction; shared issuance checks also apply to administrators."""
    if type(ttl_seconds) is not int or not 60 <= ttl_seconds <= 86400:
        raise ValueError("Credential lifetime must be 60..86400 seconds")
    if not isinstance(projects, (list, tuple)) or not isinstance(actions, (list, tuple)):
        raise ValueError("Scope lists required")
    projects = sorted({validate_project_id(p) for p in projects})
    actions = sorted(set(actions))
    if not projects or not actions or not set(actions) <= ACTIONS:
        raise ValueError("Explicit projects and supported actions required")
    token, identifier = secrets.token_urlsafe(32), str(uuid4())
    user = conn.execute("SELECT enabled FROM identity_users WHERE id=?", (user_id,)).fetchone()
    if user is None or user[0] != 1:
        raise ValueError("Enabled user required")
    for project in projects:
        membership = conn.execute("SELECT role FROM identity_memberships WHERE user_id=? AND project_id=?", (user_id, project)).fetchone()
        if membership is None or not set(actions) <= ROLES[membership[0]]:
            raise ValueError("Credential scope exceeds current project role")
    conn.execute("INSERT INTO identity_credentials VALUES (?,?,?,?,?,0,?,?)", (
        identifier, user_id, hashlib.sha256(token.encode()).hexdigest(), timestamp,
        timestamp + ttl_seconds, json.dumps(projects), json.dumps(actions),
    ))
    return identifier, token


def revoke_credential(path, identifier):
    with closing(connect_existing(path, read_only=False)) as conn, conn:
        conn.execute("UPDATE identity_credentials SET revoked=1 WHERE id=?", (identifier,))


def disable_user(path, user_id):
    with closing(connect_existing(path, read_only=False)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        if conn.execute("SELECT version FROM identity_schema").fetchone()[0] == 4:
            from .administration import keep_another_admin, revoke_user_access
            keep_another_admin(conn, user_id)
            revoke_user_access(conn, user_id)
        conn.execute("UPDATE identity_users SET enabled=0 WHERE id=?", (user_id,))


def enable_user(path, user_id):
    """Explicit local recovery; password reset never enables an account."""
    with closing(connect_existing(path, read_only=False)) as conn, conn:
        if conn.execute("UPDATE identity_users SET enabled=1 WHERE id=?", (user_id,)).rowcount != 1:
            raise ValueError("Existing user required")


class SqliteIdentityProvider:
    def __init__(self, path):
        self.path = store_path(path)

    def authorize(self, authorization, project, action, *, now=None):
        project = validate_project_id(project)
        if action not in ACTIONS:
            raise ProjectAccessDenied("Unsupported action")
        if not isinstance(authorization, str) or not authorization.startswith("Bearer "):
            raise AuthenticationRequired("Individual credential required")
        token = authorization[7:].strip()
        if not token or len(token) > 512:
            raise AuthenticationRequired("Invalid individual credential")
        timestamp = time.time() if now is None else now
        with closing(connect_existing(self.path)) as conn:
            row = conn.execute("""SELECT c.*,u.enabled FROM identity_credentials c
                JOIN identity_users u ON u.id=c.user_id WHERE c.token_hash=?""",
                (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
            return principal_for_credential(conn, row, project, action, timestamp)


class PostgresIdentityProvider:
    """Read-only bearer authorization against the qualified team schema."""

    def __init__(self, dsn: str):
        if not isinstance(dsn, str) or not dsn.strip():
            raise ValueError("PostgreSQL identity DSN required")
        self.dsn = dsn

    def authorize(self, authorization, project, action, *, now=None):
        project = validate_project_id(project)
        if action not in ACTIONS:
            raise ProjectAccessDenied("Unsupported action")
        if not isinstance(authorization, str) or not authorization.startswith("Bearer "):
            raise AuthenticationRequired("Individual credential required")
        token = authorization[7:].strip()
        if not token or len(token) > 512:
            raise AuthenticationRequired("Invalid individual credential")
        timestamp = time.time() if now is None else now
        try:
            from urllib.parse import urlparse
            import pg8000.dbapi as pg
            parsed = urlparse(self.dsn.replace("postgresql+pg8000://", "postgresql://", 1))
            conn = pg.connect(
                user=parsed.username,
                password=parsed.password,
                host=parsed.hostname or "127.0.0.1",
                port=parsed.port or 5432,
                database=(parsed.path or "/postgres").lstrip("/"),
            )
            try:
                cur = conn.cursor()
                cur.execute(
                    """select s.id,s.user_id,s.expires_at,s.revoked_at,s.metadata,u.status,m.role
                       from sessions s join users u on u.id=s.user_id
                       left join project_memberships m
                         on m.user_id=s.user_id and m.project_id=%s
                       where s.token_hash=%s""",
                    (project, hashlib.sha256(token.encode()).hexdigest()),
                )
                row = cur.fetchone()
            finally:
                conn.close()
        except Exception as exc:
            raise IdentityUnavailable("PostgreSQL identity store unavailable") from exc
        if row is None or row[5] != "active" or row[3] is not None:
            raise AuthenticationRequired("Invalid or expired individual credential")
        expires = row[2]
        if hasattr(expires, "timestamp"):
            expires = expires.timestamp()
        if float(expires) <= timestamp:
            raise AuthenticationRequired("Invalid or expired individual credential")
        try:
            metadata = row[4] if isinstance(row[4], dict) else json.loads(row[4] or "{}")
            projects, actions = metadata["projects"], metadata["actions"]
            if not isinstance(projects, list) or not isinstance(actions, list):
                raise ValueError("Invalid scope")
        except (KeyError, TypeError, ValueError):
            raise AuthenticationRequired("Invalid individual credential scope") from None
        if project not in projects or action not in actions:
            raise ProjectAccessDenied("Project action denied")
        role = row[6]
        allowed = ACTIONS if role in ("owner", "maintainer") else ROLES.get(role, ())
        if action not in allowed:
            raise ProjectAccessDenied("Project action denied")
        return Principal(row[1], row[0], project, action)


def principal_for_credential(conn, row, project, action, timestamp):
    if row is None or row["enabled"] != 1 or row["revoked"] != 0 or not row["issued_at"] <= timestamp < row["expires_at"]:
        raise AuthenticationRequired("Invalid or expired individual credential")
    try:
        projects, actions = json.loads(row["projects"]), json.loads(row["actions"])
        if not isinstance(projects, list) or not isinstance(actions, list):
            raise ValueError("Invalid scope")
    except (ValueError, TypeError) as exc:
        raise AuthenticationRequired("Invalid individual credential scope") from exc
    if project not in projects or action not in actions:
        raise ProjectAccessDenied("Project action denied")
    membership = conn.execute("SELECT role FROM identity_memberships WHERE user_id=? AND project_id=?", (row["user_id"], project)).fetchone()
    if membership is None or action not in ROLES.get(membership[0], ()):
        raise ProjectAccessDenied("Project action denied")
    return Principal(row["user_id"], row["id"], project, action)
