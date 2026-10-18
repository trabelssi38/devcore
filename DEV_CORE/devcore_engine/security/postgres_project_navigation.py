"""Project catalogue and explicit rotation of password-admitted browser sessions."""
import hashlib
import json
import secrets
from datetime import datetime, timezone
from uuid import uuid4

from .browser_sessions import BrowserSession, csrf_for_session
from .identity import AuthenticationRequired, Principal, ProjectAccessDenied, READ
from .postgres_browser_sessions import _connect, _read_session, _scope, session_info


def accessible_projects(dsn, secret, origin):
    session = session_info(dsn, secret, origin)
    connection = _connect(dsn)
    try:
        cursor = connection.cursor()
        cursor.execute('SELECT metadata FROM sessions WHERE id=%s', (session.session_id,))
        row = cursor.fetchone()
        metadata = row[0] if isinstance(row[0], dict) else json.loads(row[0])
        cursor.execute('''SELECT p.id,p.name,m.role FROM projects p
            JOIN project_memberships m ON m.project_id=p.id
            WHERE m.user_id=%s AND p.status IN ('active','needs_review') ORDER BY lower(p.name),p.id''',
            (session.principal.user_id,))
        return [{'id': pid, 'name': name, 'role': role}
                for pid, name, role in cursor.fetchall()
                if READ in _scope(role) and
                (metadata.get('password_admitted') is True or pid == session.project_id)]
    finally:
        connection.close()


def switch_project(dsn, secret, project, origin, csrf):
    current = session_info(dsn, secret, origin)
    connection = _connect(dsn)
    try:
        cursor = connection.cursor()
        cursor.execute('SELECT metadata FROM sessions WHERE id=%s FOR UPDATE', (current.session_id,))
        row = cursor.fetchone()
        if row is None:
            raise AuthenticationRequired('Invalid session')
        current = _read_session(dsn, secret, current.project_id, READ, origin,
                                csrf=csrf, mutate=True, connection=connection)
        metadata = row[0] if isinstance(row[0], dict) else json.loads(row[0])
        if metadata.get('password_admitted') is not True:
            raise ProjectAccessDenied('Password session required to switch projects')
        cursor.execute('''SELECT m.role FROM project_memberships m JOIN projects p ON p.id=m.project_id
            WHERE m.user_id=%s AND m.project_id=%s AND p.status IN ('active','needs_review') ''',
            (current.principal.user_id, project))
        row = cursor.fetchone()
        actions = _scope(row[0]) if row else ()
        if READ not in actions:
            raise ProjectAccessDenied('Project access denied')
        now = datetime.now(timezone.utc)
        expiry = datetime.fromtimestamp(current.expires_at, timezone.utc)
        new_secret = secrets.token_urlsafe(32)
        identifier = 'password-' + str(uuid4())
        metadata = {'projects':[project], 'actions':list(actions), 'origin':origin,
                    'browser':True, 'password_admitted':True}
        cursor.execute('''INSERT INTO sessions
            (id,user_id,token_hash,csrf_token_hash,expires_at,revoked_at,metadata,created_at)
            VALUES (%s,%s,%s,%s,%s,null,%s,%s)''',
            (identifier, current.principal.user_id, hashlib.sha256(new_secret.encode()).hexdigest(),
             hashlib.sha256(csrf_for_session(new_secret).encode()).hexdigest(), expiry, json.dumps(metadata), now))
        cursor.execute('UPDATE sessions SET revoked_at=%s WHERE id=%s', (now, current.session_id))
        connection.commit()
        return BrowserSession(Principal(current.principal.user_id, identifier, project, READ),
                              identifier, project, expiry.timestamp(), actions), new_secret
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()
