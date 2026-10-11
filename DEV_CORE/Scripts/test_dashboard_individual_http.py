"""Individual project boundaries through a temporary real HTTP server."""
import asyncio
import json
import os
import sqlite3
from pathlib import Path
import subprocess
import sys
import time

import httpx
import pytest

from test_dashboard_individual_access import runtime
from devcore_engine.security.identity import revoke_credential


@pytest.mark.parametrize('mutation', [None, ('POST', '/api/done', 'done', 'task.complete'),
                                     ('DELETE', '/api/delete', 'deleted', 'task.delete'),
                                     ('POST', '/api/pause', 'paused', 'task.pause'),
                                     ('POST', '/api/resume', 'in_progress', 'task.resume')])
def test_two_individual_clients_and_global_stream_denial_on_real_http(runtime, tmp_path, mutation):
    _, _, credentials, identity, local = runtime
    if mutation is not None and mutation[1] == '/api/resume':
        with sqlite3.connect(local / 'devcore.db') as conn:
            conn.execute("UPDATE tasks SET status='paused' WHERE project_id='alpha'")
    with sqlite3.connect(local / 'devcore.db') as conn:
        initial_status, initial_version = conn.execute("SELECT status,version FROM tasks WHERE project_id='alpha'").fetchone()

    launcher, port_file, violation = (tmp_path / name for name in ('server.py', 'port.json', 'global-called'))
    launcher.write_text(r'''
import importlib.util,json,socket,sys
from pathlib import Path
import uvicorn
spec=importlib.util.spec_from_file_location('individual_socket_fixture',sys.argv[1])
api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)
def forbidden(*args,**kwargs):
    Path(sys.argv[3]).write_text('global data or stream was accessed')
    raise AssertionError('Individual recipe cannot use global cache/stream')
api.event_generator=forbidden
api.read_cached_dashboard_payload=forbidden
api.read_dashboard_html=forbidden
sock=socket.socket();sock.bind(('127.0.0.1',0))
Path(sys.argv[2]).write_text(json.dumps({'port':sock.getsockname()[1],'uvicorn':uvicorn.__version__}))
uvicorn.Server(uvicorn.Config(api.app,log_level='warning',lifespan='off')).run(sockets=[sock])
''', encoding='utf-8')
    env = os.environ.copy()  # runtime fixture defines roots/identity before any child import.
    env['DEVCORE_PLATFORM_ROOT'] = str(tmp_path / 'platform')
    assert env['DEVCORE_DASHBOARD_AUTH_PROFILE'] == 'individual'
    log_path = tmp_path / 'server.log'
    with log_path.open('w', encoding='utf-8') as log:
        process = subprocess.Popen([sys.executable, str(launcher), str(Path(__file__).with_name('dashboard_api.py')),
                                    str(port_file), str(violation)], env=env, stdout=log, stderr=log,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        try:
            deadline = time.monotonic() + 15
            while not port_file.exists():
                assert process.poll() is None, log_path.read_text(encoding='utf-8')
                assert time.monotonic() < deadline, 'Temporary individual server did not start'
                time.sleep(0.05)
            metadata = json.loads(port_file.read_text())
            async def scenario():
                base = 'http://127.0.0.1:' + str(metadata['port'])
                options = {'base_url': base, 'trust_env': False, 'timeout': 5}
                async with httpx.AsyncClient(**options) as anonymous, \
                        httpx.AsyncClient(**options, headers={'Authorization': 'Bearer ' + credentials['alice'][1]}) as alice, \
                        httpx.AsyncClient(**options, headers={'Authorization': 'Bearer ' + credentials['bob'][1]}) as bob:
                    for _ in range(100):
                        try:
                            if (await anonymous.get('/api/status')).status_code == 200:
                                break
                        except httpx.ConnectError:
                            pass
                        await asyncio.sleep(0.05)
                    else:
                        raise AssertionError('Temporary individual API did not become ready')
                    a, b = await asyncio.gather(alice.get('/api/dashboard/tasks?project=alpha'),
                                                bob.get('/api/dashboard/tasks?project=beta'))
                    assert a.status_code == b.status_code == 200
                    assert a.json()[0]['title'] == 'alpha'
                    assert b.json()[0]['title'] == 'beta'
                    assert a.headers['cache-control'] == b.headers['cache-control'] == 'no-store'
                    assert (await anonymous.get('/api/dashboard/tasks?project=alpha')).status_code == 401
                    crossed = await asyncio.gather(alice.get('/api/dashboard/tasks?project=beta'),
                                                   bob.get('/api/dashboard/tasks?project=alpha'))
                    assert all(r.status_code == 403 for r in crossed)
                    paths = ['/', '/index.html', '/index_terminal.html', '/api/dashboard',
                             '/api/dashboard/stream', '/api/settings', '/api/memory/search', '/api/refresh']
                    denied = await asyncio.gather(*(alice.get(path) for path in paths))
                    assert all(r.status_code == 403 and r.json()['detail']['code'] == 'individual_route_unavailable' for r in denied)
                    # Repeated global stream attempts cannot reach a reader or admission.
                    burst = await asyncio.gather(*(bob.get('/api/dashboard/stream', headers={
                        'Last-Event-ID': 'invalid'}) for _ in range(32)))
                    assert all(r.status_code == 403 for r in burst)
                    assert not violation.exists()
                    if mutation is not None:
                        method, path, status, action = mutation
                        body = {'project': 'alpha', 'id': 'T-01', 'expected_version': initial_version,
                                'actor': 'mallory', 'user_id': 'mallory', 'trace_id': 'forged-trace',
                                'password': 'fixture-secret-password', 'token': 'fixture-secret-token'}
                        assert (await bob.request(method, path, json=body)).status_code == 403
                        assert (await alice.request(method, path, json=body, headers={
                            'Authorization': 'Bearer ' + credentials['reader'][1]})).status_code == 403
                        conflict = await alice.request(method, path, json={**body, 'expected_version': initial_version + 1})
                        assert conflict.status_code == 409
                        assert conflict.json()['detail']['code'] == 'stale_task_version'
                        # Independent sockets start the same conditional mutation together.
                        async with httpx.AsyncClient(**options, headers={
                            'Authorization': 'Bearer ' + credentials['alice'][1]}) as parallel:
                            first, second, beta_read = await asyncio.gather(
                                alice.request(method, path, json=body, headers={'X-User-Id': 'mallory'}),
                                parallel.request(method, path, json=body, headers={'X-User-Id': 'mallory'}),
                                bob.get('/api/dashboard/tasks?project=beta'))
                        statuses = [first.status_code, second.status_code]
                        assert statuses.count(200) == 1
                        assert all(code in (200, 404, 409) for code in statuses)
                        loser = second if first.status_code == 200 else first
                        if loser.status_code == 409:
                            assert loser.json()['detail']['code'] in ({'stale_task_version', 'task_transition_conflict'} if path == '/api/resume' else {'stale_task_version'})
                        assert beta_read.status_code == 200 and beta_read.json()[0]['title'] == 'beta'
                        repeated = await alice.request(method, path, json=body)
                        assert repeated.status_code in (404, 409)
                        with sqlite3.connect(local / 'devcore.db') as check:
                            assert check.execute("SELECT status,version FROM tasks WHERE project_id='alpha'").fetchone() == (status, initial_version + 1)
                            assert check.execute("SELECT status,version FROM tasks WHERE project_id='beta'").fetchone() == ('in_progress', 1)
                            audit = check.execute('SELECT project_id,actor,action,entity_id,details FROM audit_log').fetchall()
                        assert len(audit) == 1  # Denials/conflicts/repeated requests do not add successful mutations.
                        assert audit[0][:4] == ('alpha', 'alice', action, 'T-01')
                        detail = json.loads(audit[0][4])
                        assert detail['before'] == {'status': initial_status, 'version': initial_version}
                        assert detail['after'] == {'status': status, 'version': initial_version + 1}
                        for forbidden in ('mallory', 'forged-trace', 'fixture-secret-password', 'fixture-secret-token',
                                          credentials['alice'][1], credentials['bob'][1]):
                            assert forbidden not in str(audit)
                        assert (await bob.get('/api/dashboard/tasks?project=beta')).status_code == 200
                    await asyncio.to_thread(revoke_credential, identity, credentials['alice'][0])
                    revoked, unaffected = await asyncio.gather(alice.get('/api/dashboard/tasks?project=alpha'),
                                                               bob.get('/api/dashboard/tasks?project=beta'))
                    assert revoked.status_code == 401
                    assert unaffected.status_code == 200 and unaffected.json()[0]['title'] == 'beta'
                    assert not violation.exists()
            asyncio.run(scenario())
            print(json.dumps({'users': 2, 'projects': 2, 'global_stream_denied': True,
                              'mutation': None if mutation is None else mutation[3],
                              'concurrent_same_task_single_winner': mutation is not None,
                              'revocation_other_project_available': True, 'uvicorn': metadata['uvicorn']}))
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
