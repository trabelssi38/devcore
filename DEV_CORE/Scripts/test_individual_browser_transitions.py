"""Two disposable browser profiles against the real individual project API."""
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import threading
import time

import httpx
import pytest
import uvicorn

from test_dashboard_individual_access import runtime  # noqa: F401
from devcore_engine.security.browser_sessions import COOKIE, upgrade_session_store
from devcore_engine.security.identity import AUDIT_READ, READ, WRITE, issue_credential, set_membership
from devcore_engine.security import passwords
from test_dashboard_project_context import write_context


class _RequestProbe:
    def __init__(self, app):
        self.app = app
        self.pause_methods = []

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http' and scope['path'] == '/api/pause':
            self.pause_methods.append(scope['method'])
        await self.app(scope, receive, send)


@pytest.mark.parametrize('authentication', ['cookie', 'password'])
def test_real_browser_pause_resume_audit_and_independent_logout(tmp_path, monkeypatch, request, authentication):
    browser = Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
    if not browser.is_file():
        pytest.skip('Local qualification requires Microsoft Edge')
    node = shutil.which('node')
    assert node, 'Node with WebSocket support is required'
    monkeypatch.setenv('DEVCORE_PLATFORM_ROOT', str(tmp_path / 'platform'))
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    origin = 'http://127.0.0.1:' + str(sock.getsockname()[1])
    trusted_origin = 'http://trusted.devcore.test'
    monkeypatch.setenv('DEVCORE_CORS_ALLOWED_ORIGINS', origin + ',' + trusted_origin)
    module, _, credentials, identity, local = request.getfixturevalue('runtime')
    upgrade_session_store(identity)
    set_membership(identity, 'alice', 'alpha', 'owner')
    credentials['alice'] = issue_credential(identity, 'alice', ['alpha'], [READ, WRITE, AUDIT_READ])
    password = 'Une phrase de recette uniquement'
    if authentication == 'password':
        passwords.upgrade_password_store(identity)
        with sqlite3.connect(local / 'devcore.db') as db:
            for user, project in [('alice', 'alpha'), ('bob', 'beta')]:
                passwords.set_password(identity, user, password)
                repository = tmp_path / (project + '-repository')
                write_context(repository / 'docs' / 'project-context', project)
                db.execute('UPDATE projects SET root_path=? WHERE id=?', (str(repository), project))
    request_probe = _RequestProbe(module.app)
    server = uvicorn.Server(uvicorn.Config(request_probe, log_level='warning', lifespan='off'))
    thread = threading.Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 15
        while not server.started:
            assert thread.is_alive() and time.monotonic() < deadline
            time.sleep(.05)
        with httpx.Client(base_url=origin, trust_env=False, timeout=5) as client:
            allowed_preflight = client.options('/api/pause', headers={
                'Origin': trusted_origin,
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'content-type,x-csrf-token',
            })
            assert allowed_preflight.status_code == 200
            assert allowed_preflight.headers.get('access-control-allow-origin') == trusted_origin
            assert allowed_preflight.headers.get('access-control-allow-credentials') == 'true'
            assert 'POST' in allowed_preflight.headers.get('access-control-allow-methods', '')
            allowed_headers = allowed_preflight.headers.get('access-control-allow-headers', '').lower()
            assert 'content-type' in allowed_headers and 'x-csrf-token' in allowed_headers
        request_probe.pause_methods.clear()
        cookies = {}
        for user, project in ([] if authentication == 'password' else [('alice', 'alpha'), ('bob', 'beta')]):
            with httpx.Client(base_url=origin, trust_env=False, timeout=5) as client:
                response = client.post('/api/auth/session', json={'project': project},
                                       headers={'Origin': origin, 'Authorization': 'Bearer ' + credentials[user][1]})
                assert response.status_code == 200
                cookies[user] = client.cookies.get(COOKIE)
        fixture = tmp_path / 'browser-fixture.json'
        fixture.write_text(json.dumps({'origin': origin, 'cookies': cookies,
                                      'authentication': authentication, 'password': password}), encoding='utf-8')
        result = subprocess.run([node, str(Path(__file__).with_name('individual_browser_transitions.cjs')),
                                 str(browser), str(tmp_path), str(fixture)],
                                capture_output=True, text=True, timeout=100, env=os.environ.copy())
        assert result.returncode == 0, result.stdout + result.stderr
        report = json.loads(result.stdout)
        print(json.dumps(report))
        assert report['browser_contexts'] == 2 and report['audit_rows'] == 2
        assert report['authentication'] == authentication
        if authentication == 'password':
            assert report['context_reloaded'] is True
        # Alice's pause and Bob's HTML form each reach the app. The browser's
        # cross-origin JSON fetch must stop at OPTIONS and never deliver POST.
        assert request_probe.pause_methods.count('POST') == 2
        assert request_probe.pause_methods.count('OPTIONS') == 1
        with sqlite3.connect(local / 'devcore.db') as db:
            assert db.execute("SELECT status,version FROM tasks WHERE project_id='alpha'").fetchone() == ('in_progress', 3)
            assert db.execute("SELECT status,version FROM tasks WHERE project_id='beta'").fetchone() == ('in_progress', 1)
            assert sorted(db.execute("SELECT actor,action FROM audit_log WHERE project_id='alpha'").fetchall()) == [
                ('alice', 'task.pause'), ('alice', 'task.resume')]
            assert db.execute("SELECT COUNT(*) FROM audit_log WHERE project_id='beta'").fetchone()[0] == 0
    finally:
        server.should_exit = True
        thread.join(10)
        sock.close()
        # Also clean up our exact child PIDs if Node timed out before its finally.
        pids = tmp_path / 'owned-pids.json'
        if pids.exists():
            for pid in json.loads(pids.read_text()):
                subprocess.run(['taskkill', '/PID', str(pid), '/T', '/F'], capture_output=True,
                               timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
        fixture = tmp_path / 'browser-fixture.json'
        if fixture.exists():
            fixture.unlink()  # Disposable synthetic cookies need not survive the recipe.
        assert not thread.is_alive(), 'Owned temporary HTTP server did not stop'
