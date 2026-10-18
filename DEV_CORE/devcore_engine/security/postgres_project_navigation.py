"""Project catalogue and explicit rotation of password-admitted browser sessions."""
import hashlib
import json
import secrets
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4

from .browser_sessions import BrowserSession, csrf_for_session
from .identity import AuthenticationRequired, Principal, ProjectAccessDenied, READ
from .postgres_browser_sessions import _connect, _read_session, _scope, session_info


def _is_git_project(root_path):
    """Accept project roots inside a Git worktree, including linked worktrees."""
    if not root_path:
        return False
    try:
        root = Path(root_path)
        if not root.is_absolute() or not root.is_dir():
            return False
        return any((parent / '.git').is_dir() or (parent / '.git').is_file()
                   for parent in (root, *root.parents))
    except (OSError, ValueError):
        return False


def accessible_projects(dsn, secret, origin):
    session = session_info(dsn, secret, origin)
    connection = _connect(dsn)
    try:
        cursor = connection.cursor()
        cursor.execute('SELECT metadata FROM sessions WHERE id=%s', (session.session_id,))
        row = cursor.fetchone()
        metadata = row[0] if isinstance(row[0], dict) else json.loads(row[0])
        cursor.execute('''SELECT p.id,p.name,m.role,p.status,p.root_path FROM projects p
            JOIN project_memberships m ON m.project_id=p.id
            WHERE m.user_id=%s ORDER BY lower(p.name),p.id''',
            (session.principal.user_id,))
        projects = []
        for pid, name, role, status, root_path in cursor.fetchall():
            if READ not in _scope(role) or (metadata.get('password_admitted') is not True and pid != session.project_id):
                continue
            if not _is_git_project(root_path):
                continue
            cursor.execute("SELECT set_config('app.current_project_id',%s,true)", (pid,))
            cursor.execute("""SELECT count(*),count(*) FILTER (WHERE status='done'),
                count(*) FILTER (WHERE status IN ('active','in_progress')) FROM tasks WHERE project_id=%s""", (pid,))
            total, completed, active = cursor.fetchone()
            tokens = 0
            cursor.execute("SELECT to_regclass('public.project_llm_usage')")
            if cursor.fetchone()[0] is not None:
                cursor.execute("""SELECT coalesce(sum(prompt_tokens+completion_tokens),0)
                    FROM project_llm_usage WHERE project_id=%s""", (pid,))
                tokens = int(cursor.fetchone()[0] or 0)
            projects.append({'id': pid, 'name': name, 'role': role, 'status': status,
                             'tasks': int(total), 'completed_tasks': int(completed),
                             'active_tasks': int(active), 'tokens': tokens,
                             'can_archive': role in ('owner', 'maintainer', 'contributor')})
        return projects
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
            WHERE m.user_id=%s AND m.project_id=%s ''',
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


def set_project_archived(dsn, secret, project, origin, csrf, archived):
    if type(archived) is not bool:
        raise ValueError('Archive state must be boolean')
    session = session_info(dsn, secret, origin)
    connection = _connect(dsn)
    try:
        cursor = connection.cursor()
        cursor.execute('''SELECT metadata FROM sessions WHERE id=%s FOR UPDATE''',
                      (session.session_id,))
        session_row = cursor.fetchone()
        if session_row is None:
            raise AuthenticationRequired('Invalid session')
        session = _read_session(dsn, secret, session.project_id, READ, origin,
                                csrf=csrf, mutate=True, connection=connection)
        try:
            cursor.execute('SELECT devcore_set_project_archived(%s,%s,%s)',
                           (project, session.principal.user_id, archived))
        except Exception as exc:
            detail = exc.args[0] if exc.args else None
            code = detail.get('C', '') if isinstance(detail, dict) else detail if isinstance(detail, str) else ''
            if code == '42501':
                raise ProjectAccessDenied('Project access denied') from exc
            if code == '22023':
                raise ValueError('Project is already in the requested state') from exc
            raise
        result_status = cursor.fetchone()[0]
        connection.commit()
        return {'id': project, 'status': result_status}
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()
