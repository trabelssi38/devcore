"""Password admission for the PostgreSQL team profile."""
from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from .browser_sessions import BrowserSession, csrf_for_session
from .identity import AuthenticationRequired, IdentityUnavailable, Principal, ProjectAccessDenied, ROLES
from .postgres_browser_sessions import _connect, _scope


def create_password_session(dsn: str, user_id: str, password: str, project: str, origin: str,
                            *, previous: str | None = None) -> tuple[BrowserSession, str]:
    if not isinstance(password, str) or not 1 <= len(password) <= 256:
        raise AuthenticationRequired("Invalid credentials")
    try:
        from argon2 import PasswordHasher
        from argon2.exceptions import InvalidHashError, VerificationError
        hasher = PasswordHasher()
    except ImportError as exc:
        raise IdentityUnavailable("Password hashing dependency unavailable") from exc
    conn = _connect(dsn)
    try:
        cur = conn.cursor()
        cur.execute("""select u.password_hash,u.status,m.role from users u
            left join project_memberships m on m.user_id=u.id and m.project_id=%s
            where u.id=%s""", (project, user_id))
        row = cur.fetchone()
        if row is None or row[0] is None or row[1] != "active" or row[2] is None:
            raise AuthenticationRequired("Invalid credentials")
        try:
            valid = hasher.verify(row[0], password)
        except (InvalidHashError, VerificationError):
            valid = False
        if not valid:
            raise AuthenticationRequired("Invalid credentials")
        actions = _scope(row[2])
        now = datetime.now(timezone.utc)
        expiry = now + timedelta(minutes=30)
        secret = secrets.token_urlsafe(32)
        csrf = csrf_for_session(secret)
        metadata = {"projects": [project], "actions": list(actions), "origin": origin, "browser": True, "password_admitted": True}
        if previous:
            cur.execute("update sessions set revoked_at=%s where token_hash=%s",
                        (now, hashlib.sha256(previous.encode()).hexdigest()))
        sid = "password-" + str(uuid4())
        cur.execute("""insert into sessions
            (id,user_id,token_hash,csrf_token_hash,expires_at,revoked_at,metadata,created_at)
            values (%s,%s,%s,%s,%s,null,%s,%s)""",
                    (sid, user_id, hashlib.sha256(secret.encode()).hexdigest(),
                     hashlib.sha256(csrf.encode()).hexdigest(), expiry, json.dumps(metadata), now))
        conn.commit()
        return BrowserSession(Principal(user_id, sid, project, "task.read"), sid, project,
                              expiry.timestamp(), actions), secret
    except (AuthenticationRequired, ProjectAccessDenied, IdentityUnavailable):
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise IdentityUnavailable("PostgreSQL identity store unavailable") from exc
    finally:
        conn.close()
