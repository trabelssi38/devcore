"""PostgreSQL browser-session adapter for the qualified team profile."""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from uuid import uuid4

from .browser_sessions import BrowserSession, COOKIE, csrf_for_session
from .identity import (
    ACTIONS, AuthenticationRequired, IdentityUnavailable, Principal,
    ProjectAccessDenied, ROLES, READ, PostgresIdentityProvider,
)


def _connect(dsn: str):
    try:
        import pg8000.dbapi as pg
        parsed = urlparse(dsn.replace("postgresql+pg8000://", "postgresql://", 1))
        return pg.connect(user=parsed.username, password=parsed.password,
                          host=parsed.hostname or "127.0.0.1", port=parsed.port or 5432,
                          database=(parsed.path or "/postgres").lstrip("/"))
    except Exception as exc:
        raise IdentityUnavailable("PostgreSQL identity store unavailable") from exc


def _scope(role: str | None) -> tuple[str, ...]:
    return tuple(sorted(ACTIONS if role in ("owner", "maintainer") else ROLES.get(role, ())))


def create_session(dsn: str, authorization: str, project: str, origin: str,
                   *, previous: str | None = None, ttl_seconds: int = 1800) -> tuple[BrowserSession, str]:
    if not isinstance(origin, str) or not origin:
        raise ValueError("Session origin required")
    principal = PostgresIdentityProvider(dsn).authorize(authorization, project, READ)
    now = datetime.now(timezone.utc)
    secret = secrets.token_urlsafe(32)
    csrf = csrf_for_session(secret)
    conn = _connect(dsn)
    try:
        cur = conn.cursor()
        cur.execute("""select s.expires_at,s.metadata,m.role from sessions s
            join project_memberships m on m.user_id=s.user_id and m.project_id=%s
            where s.id=%s""", (project, principal.credential_id))
        row = cur.fetchone()
        if row is None:
            raise AuthenticationRequired("Invalid or expired individual credential")
        actions = _scope(row[2])
        expires = row[0]
        expires = expires if hasattr(expires, "tzinfo") else now + timedelta(seconds=ttl_seconds)
        expires = min(expires, now + timedelta(seconds=ttl_seconds))
        metadata = {"projects": [project], "actions": list(actions), "origin": origin, "browser": True}
        if previous:
            cur.execute("update sessions set revoked_at=%s where token_hash=%s",
                        (now, hashlib.sha256(previous.encode()).hexdigest()))
        sid = "browser-" + str(uuid4())
        cur.execute("""insert into sessions
            (id,user_id,token_hash,csrf_token_hash,expires_at,revoked_at,metadata,created_at)
            values (%s,%s,%s,%s,%s,null,%s,%s)""",
                    (sid, principal.user_id, hashlib.sha256(secret.encode()).hexdigest(),
                     hashlib.sha256(csrf.encode()).hexdigest(), expires, json.dumps(metadata), now))
        conn.commit()
        return BrowserSession(Principal(principal.user_id, sid, project, READ), sid,
                               project, expires.timestamp(), actions), secret
    except (AuthenticationRequired, ProjectAccessDenied, IdentityUnavailable):
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise IdentityUnavailable("PostgreSQL identity store unavailable") from exc
    finally:
        conn.close()


def _read_session(dsn: str, secret: str, project: str, action: str, origin: str,
                  *, csrf: str | None = None, mutate: bool = False,
                  connection=None) -> BrowserSession:
    if not isinstance(secret, str) or not secret or len(secret) > 512:
        raise AuthenticationRequired("Invalid session")
    conn = connection if connection is not None else _connect(dsn)
    try:
        cur = conn.cursor()
        cur.execute("""select s.id,s.user_id,s.expires_at,s.revoked_at,s.metadata,m.role,u.status
            from sessions s join users u on u.id=s.user_id
            left join project_memberships m on m.user_id=s.user_id and m.project_id=%s
            where s.token_hash=%s""", (project, hashlib.sha256(secret.encode()).hexdigest()))
        row = cur.fetchone()
        if row is None or row[6] != "active" or row[3] is not None:
            raise AuthenticationRequired("Invalid or expired session")
        expires = row[2]
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires <= datetime.now(timezone.utc):
            raise AuthenticationRequired("Invalid or expired session")
        metadata = row[4] if isinstance(row[4], dict) else json.loads(row[4] or "{}")
        if metadata.get("browser") is not True:
            raise AuthenticationRequired("Invalid session")
        if project not in metadata.get("projects", []) or origin != metadata.get("origin"):
            raise ProjectAccessDenied("Session project or origin denied")
        if mutate:
            cur.execute("select csrf_token_hash from sessions where id=%s", (row[0],))
            csrf_hash = cur.fetchone()[0]
            if not isinstance(csrf, str) or not hmac.compare_digest(hashlib.sha256(csrf.encode()).hexdigest(), csrf_hash or ""):
                raise ProjectAccessDenied("Invalid session CSRF")
        actions = tuple(metadata.get("actions", ()))
        role = row[5]
        if action not in actions or action not in _scope(role):
            raise ProjectAccessDenied("Project action denied")
        return BrowserSession(Principal(row[1], row[0], project, action), row[0], project,
                              expires.timestamp(), tuple(actions))
    except (AuthenticationRequired, ProjectAccessDenied):
        raise
    except Exception as exc:
        raise IdentityUnavailable("PostgreSQL identity store unavailable") from exc
    finally:
        if connection is None:
            conn.close()


def authorize_session(dsn: str, secret: str, project: str, action: str, origin: str,
                      *, csrf: str | None = None, mutate: bool = False,
                      connection=None) -> BrowserSession:
    return _read_session(dsn, secret, project, action, origin, csrf=csrf,
                         mutate=mutate, connection=connection)


def session_info(dsn: str, secret: str, origin: str) -> BrowserSession:
    if not isinstance(secret, str) or not secret or len(secret) > 512:
        raise AuthenticationRequired("Invalid session")
    conn = _connect(dsn)
    try:
        cur = conn.cursor()
        cur.execute("select metadata from sessions where token_hash=%s",
                    (hashlib.sha256(secret.encode()).hexdigest(),))
        row = cur.fetchone()
        if row is None:
            raise AuthenticationRequired("Invalid session")
        metadata = row[0] if isinstance(row[0], dict) else json.loads(row[0] or "{}")
        projects = metadata.get("projects", [])
        if not projects:
            raise AuthenticationRequired("Invalid session")
        return _read_session(dsn, secret, projects[0], READ, origin)
    finally:
        conn.close()


def revoke_session(dsn: str, secret: str) -> None:
    conn = _connect(dsn)
    try:
        cur = conn.cursor()
        cur.execute("update sessions set revoked_at=%s where token_hash=%s",
                    (datetime.now(timezone.utc), hashlib.sha256(secret.encode()).hexdigest()))
        conn.commit()
        cur.close()
    finally:
        conn.close()
