"""Instance identity administration for the local recipe, with transactional author history.

No HTTP bootstrap or task permission bypass. The OS operator remains a trust boundary.
"""

from contextlib import closing
from dataclasses import dataclass
import hashlib
import json
import secrets
import time
from uuid import uuid4

from .identity import (
    AuthenticationRequired, IdentityUnavailable, ProjectAccessDenied, ROLES,
    connect_existing, insert_credential,
)
from devcore_engine.context import validate_project_id

ADMIN = "identity.manage"


@dataclass(frozen=True)
class AdminPrincipal:
    user_id: str
    credential_id: str
    action: str = ADMIN


def require_admin_schema(conn):
    if conn.execute("SELECT version FROM identity_schema").fetchone()[0] != 4:
        raise IdentityUnavailable("Administration requires explicit schema upgrade")


def upgrade_admin_store(path):
    with closing(connect_existing(path, read_only=False)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        version = conn.execute("SELECT version FROM identity_schema").fetchone()[0]
        if version == 4:
            return
        if version != 3:
            raise IdentityUnavailable("Upgrade passwords before administration")
        conn.execute("CREATE TABLE identity_instance_admins(user_id TEXT PRIMARY KEY REFERENCES identity_users(id))")
        conn.execute("""CREATE TABLE identity_admin_credentials(
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES identity_users(id),
            token_hash TEXT NOT NULL UNIQUE, issued_at REAL NOT NULL, expires_at REAL NOT NULL,
            revoked INTEGER NOT NULL DEFAULT 0 CHECK(revoked IN (0,1)))""")
        conn.execute("CREATE TABLE identity_admin_state(id INTEGER PRIMARY KEY CHECK(id=1), bootstrapped INTEGER NOT NULL CHECK(bootstrapped IN (0,1)))")
        conn.execute("INSERT INTO identity_admin_state VALUES (1,0)")
        conn.execute("""CREATE TABLE identity_audit(
            id TEXT PRIMARY KEY, actor TEXT NOT NULL, action TEXT NOT NULL,
            target_user TEXT NOT NULL, project_id TEXT, details TEXT NOT NULL,
            created_at REAL NOT NULL)""")
        conn.execute("UPDATE identity_schema SET version=4")


def audit(conn, actor, operation, target, timestamp, *, project=None, details=None):
    # Only explicitly constructed metadata; no input dictionary or secret serialization.
    conn.execute("INSERT INTO identity_audit VALUES (?,?,?,?,?,?,?)", (
        str(uuid4()), actor, operation, target, project,
        json.dumps(details or {}, separators=(",", ":")), timestamp,
    ))


def bootstrap_admin(path, user_id, *, now=None):
    """Local OS operator only; one-shot, not exposed through a credential or HTTP."""
    user_id = validate_project_id(user_id)
    with closing(connect_existing(path, read_only=False)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        require_admin_schema(conn)
        state = conn.execute("SELECT bootstrapped FROM identity_admin_state WHERE id=1").fetchone()
        if state is None or state[0] != 0:
            raise ProjectAccessDenied("Initial administration already provisioned")
        user = conn.execute("""SELECT u.enabled FROM identity_users u
            JOIN identity_passwords p ON p.user_id=u.id WHERE u.id=?""", (user_id,)).fetchone()
        if user is None or user[0] != 1:
            raise ValueError("Enabled user with a password required")
        conn.execute("INSERT INTO identity_instance_admins VALUES (?)", (user_id,))
        conn.execute("UPDATE identity_admin_state SET bootstrapped=1 WHERE id=1")
        audit(conn, "local-operator", "admin.bootstrap", user_id, time.time() if now is None else now)


def admin_principal(conn, authorization, timestamp):
    require_admin_schema(conn)
    if not isinstance(authorization, str) or not authorization.startswith("Bearer "):
        raise AuthenticationRequired("Individual administrative credential required")
    token = authorization[7:].strip()
    if not token or len(token) > 512:
        raise AuthenticationRequired("Invalid administrative credential")
    row = conn.execute("""SELECT c.*,u.enabled FROM identity_admin_credentials c
        JOIN identity_users u ON u.id=c.user_id WHERE c.token_hash=?""",
        (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
    if row is None or row["enabled"] != 1 or row["revoked"] or not row["issued_at"] <= timestamp < row["expires_at"]:
        raise AuthenticationRequired("Invalid or expired administrative credential")
    if conn.execute("SELECT 1 FROM identity_instance_admins WHERE user_id=?", (row["user_id"],)).fetchone() is None:
        raise ProjectAccessDenied("Instance administration denied")
    return AdminPrincipal(row["user_id"], row["id"])


def authorize_admin(path, authorization, *, now=None):
    with closing(connect_existing(path)) as conn:
        return admin_principal(conn, authorization, time.time() if now is None else now)


def login_admin(path, user_id, password, *, ttl_seconds=900, now=None, deliver=None):
    """Same password verifier, cooldown and slots as browser login; separate capability."""
    if type(ttl_seconds) is not int or not 60 <= ttl_seconds <= 3600:
        raise ValueError("Administrative lifetime must be 60..3600 seconds")
    with closing(connect_existing(path)) as conn:
        require_admin_schema(conn)
    from .passwords import authenticate_password
    def admit(conn, user, timestamp):
        require_admin_schema(conn)
        if conn.execute("SELECT 1 FROM identity_instance_admins WHERE user_id=?", (user,)).fetchone() is None:
            raise ProjectAccessDenied("Instance administration denied")
        identifier, token = str(uuid4()), secrets.token_urlsafe(32)
        conn.execute("INSERT INTO identity_admin_credentials VALUES (?,?,?,?,?,0)", (
            identifier, user, hashlib.sha256(token.encode()).hexdigest(), timestamp, timestamp + ttl_seconds,
        ))
        audit(conn, user, "admin.login", user, timestamp, details={"credential_id": identifier})
        if deliver is not None:
            deliver(identifier, token)
        return identifier, token
    return authenticate_password(path, user_id, password, admit, now=now)


def keep_another_admin(conn, target):
    if conn.execute("SELECT 1 FROM identity_instance_admins WHERE user_id=?", (target,)).fetchone() is not None:
        others = conn.execute("""SELECT COUNT(*) FROM identity_instance_admins a
            JOIN identity_users u ON u.id=a.user_id WHERE u.enabled=1 AND u.id<>?""", (target,)).fetchone()[0]
        enabled = conn.execute("SELECT enabled FROM identity_users WHERE id=?", (target,)).fetchone()[0]
        if enabled and not others:
            raise ProjectAccessDenied("Cannot remove or disable the last enabled administrator")


def revoke_user_access(conn, target):
    conn.execute("UPDATE identity_credentials SET revoked=1 WHERE user_id=?", (target,))
    conn.execute("UPDATE identity_admin_credentials SET revoked=1 WHERE user_id=?", (target,))
    conn.execute("""UPDATE identity_browser_sessions SET revoked=1 WHERE credential_id IN
        (SELECT id FROM identity_credentials WHERE user_id=?)""", (target,))


def administer(path, authorization, operation, *, user=None, project=None, role=None,
               credential_id=None, password=None, projects=None, actions=None,
               ttl_seconds=3600, now=None, deliver=None):
    """Authenticate inside the transaction; mutation and audit either both commit or neither."""
    supported = {"add-user", "disable-user", "enable-user", "grant", "remove-membership",
                 "grant-admin", "remove-admin", "revoke-token", "revoke-admin-token",
                 "set-password", "reset-password", "issue-token"}
    if operation not in supported:
        raise ValueError("Unsupported administrative operation")
    encoded = None
    if operation in {"set-password", "reset-password"}:
        # Refuse unauthorized expensive work; repeat admission after hashing.
        authorize_admin(path, authorization, now=now)
        from .passwords import hash_password
        encoded = hash_password(password)
    target = validate_project_id(user) if user is not None else None
    project = validate_project_id(project) if project is not None else None
    with closing(connect_existing(path, read_only=False)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        timestamp = time.time() if now is None else now
        actor = admin_principal(conn, authorization, timestamp)
        if operation not in {"revoke-token", "revoke-admin-token", "add-user"}:
            if target is None or conn.execute("SELECT 1 FROM identity_users WHERE id=?", (target,)).fetchone() is None:
                raise ValueError("Existing user required")
        details, result = {}, None
        if operation == "add-user":
            if target is None:
                raise ValueError("User required")
            conn.execute("INSERT INTO identity_users VALUES (?,1)", (target,))
        elif operation in {"disable-user", "enable-user"}:
            if operation == "disable-user":
                keep_another_admin(conn, target)
                revoke_user_access(conn, target)
            conn.execute("UPDATE identity_users SET enabled=? WHERE id=?", (int(operation == "enable-user"), target))
        elif operation == "grant":
            if project is None or role not in ROLES:
                raise ValueError("Explicit project and supported role required")
            conn.execute("""INSERT INTO identity_memberships VALUES (?,?,?)
                ON CONFLICT(user_id,project_id) DO UPDATE SET role=excluded.role""", (target, project, role))
            details["role"] = role
        elif operation == "remove-membership":
            if project is None:
                raise ValueError("Explicit project required")
            conn.execute("DELETE FROM identity_memberships WHERE user_id=? AND project_id=?", (target, project))
        elif operation == "grant-admin":
            row = conn.execute("""SELECT u.enabled FROM identity_users u
                JOIN identity_passwords p ON p.user_id=u.id WHERE u.id=?""", (target,)).fetchone()
            if row is None or row[0] != 1:
                raise ValueError("Enabled user with a password required")
            conn.execute("INSERT OR IGNORE INTO identity_instance_admins VALUES (?)", (target,))
        elif operation == "remove-admin":
            keep_another_admin(conn, target)
            conn.execute("DELETE FROM identity_instance_admins WHERE user_id=?", (target,))
            conn.execute("UPDATE identity_admin_credentials SET revoked=1 WHERE user_id=?", (target,))
        elif operation in {"revoke-token", "revoke-admin-token"}:
            table = "identity_credentials" if operation == "revoke-token" else "identity_admin_credentials"
            row = conn.execute(f"SELECT user_id FROM {table} WHERE id=?", (credential_id,)).fetchone()
            if row is None:
                raise ValueError("Existing credential required")
            target = row[0]
            conn.execute(f"UPDATE {table} SET revoked=1 WHERE id=?", (credential_id,))
            details["credential_id"] = credential_id
        elif encoded is not None:
            from .passwords import replace_password
            replace_password(conn, target, encoded, timestamp)
        elif operation == "issue-token":
            result = insert_credential(conn, target, projects, actions, ttl_seconds, timestamp)
            details = {"credential_id": result[0], "projects": sorted(set(projects)), "actions": sorted(set(actions))}
        audit(conn, actor.user_id, "identity." + operation, target, timestamp, project=project, details=details)
        if deliver is not None and result is not None:
            deliver(*result)
        return result
