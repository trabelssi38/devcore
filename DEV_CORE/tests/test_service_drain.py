"""Real HTTP requests drain on isolated ephemeral Uvicorn instances."""
import asyncio
from contextlib import contextmanager
import http.client
import os
from pathlib import Path
import socket
import sys
import threading
import time

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Scripts'))
import service_runtime as runtime

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='Windows lifecycle identity')


@contextmanager
def fixture_server(tmp_path, monkeypatch, app, release):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    monkeypatch.setitem(runtime.SERVICES, 'drain-fixture', port)
    for key, leaf in [('DEVCORE_LOCAL_ROOT', ''), ('DEVCORE_DATA_ROOT', 'data'), ('DEVCORE_PLATFORM_ROOT', 'platform')]:
        monkeypatch.setenv(key, str(tmp_path / leaf))
    errors = []
    def run():
        try:
            runtime.run_managed(app, host='127.0.0.1', port=port, service='drain-fixture', log_level='error')
        except BaseException as exc:
            errors.append(exc)
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=.1):
                    break
            except OSError:
                time.sleep(.05)
        yield port, thread, errors
    finally:
        release.set()
        receipt, _, _ = runtime.paths(tmp_path, 'drain-fixture')
        if thread.is_alive() and receipt.exists():
            runtime.request_stop(tmp_path, tmp_path / 'data', tmp_path / 'platform', 'drain-fixture', 5)
        thread.join(timeout=5)
        assert not thread.is_alive(), 'Fixture server did not finish'


@pytest.mark.parametrize('streaming', [False, True])
def test_request_finishes_after_stop_wait_expires(tmp_path, monkeypatch, streaming):
    entered, release, completed = threading.Event(), threading.Event(), threading.Event()
    async def app(scope, receive, send):
        if scope['type'] == 'lifespan':
            while True:
                event = await receive()
                await send({'type': event['type'] + '.complete'})
                if event['type'] == 'lifespan.shutdown':
                    return
        entered.set()
        if streaming:
            await send({'type': 'http.response.start', 'status': 200, 'headers': []})
            await send({'type': 'http.response.body', 'body': b'first-', 'more_body': True})
        await asyncio.to_thread(release.wait, 8)
        if not streaming:
            await send({'type': 'http.response.start', 'status': 200, 'headers': []})
        await send({'type': 'http.response.body', 'body': b'finished'})
        completed.set()
    with fixture_server(tmp_path, monkeypatch, app, release) as (port, server, errors):
        responses, client_errors = [], []
        def get():
            connection = http.client.HTTPConnection('127.0.0.1', port, timeout=8)
            try:
                connection.request('GET', '/')
                response = connection.getresponse()
                responses.append((response.status, response.read()))
            except BaseException as exc:
                client_errors.append(exc)
            finally:
                connection.close()
        client = threading.Thread(target=get, daemon=True)
        client.start()
        try:
            assert entered.wait(3)
            result = runtime.request_stop(tmp_path, tmp_path / 'data', tmp_path / 'platform', 'drain-fixture', .5)
            assert not result['shutdown_completed'] and not result['force']
            assert server.is_alive() and not completed.is_set()
            receipt, request, _ = runtime.paths(tmp_path, 'drain-fixture')
            assert receipt.exists() and request.exists()
            release.set()
            client.join(timeout=5)
            server.join(timeout=5)
            assert completed.is_set() and not client_errors and not errors
            assert responses == [(200, b'first-finished' if streaming else b'finished')]
            assert not server.is_alive() and not receipt.exists() and not request.exists()
        finally:
            release.set()
            client.join(timeout=5)


def test_shutdown_hook_keeps_identity_until_completed(tmp_path, monkeypatch):
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()
    async def app(scope, receive, send):
        while True:
            event = await receive()
            if event['type'] == 'lifespan.startup':
                await send({'type': 'lifespan.startup.complete'})
            elif event['type'] == 'lifespan.shutdown':
                entered.set()
                await asyncio.to_thread(release.wait, 8)
                finished.set()
                await send({'type': 'lifespan.shutdown.complete'})
                return
    with fixture_server(tmp_path, monkeypatch, app, release) as (_, server, errors):
        result = runtime.request_stop(tmp_path, tmp_path / 'data', tmp_path / 'platform', 'drain-fixture', .5)
        assert entered.wait(2) and not result['shutdown_completed']
        receipt, request, _ = runtime.paths(tmp_path, 'drain-fixture')
        assert server.is_alive() and receipt.exists() and request.exists()
        release.set()
        server.join(timeout=5)
        assert finished.is_set() and not errors and not server.is_alive()
        assert not receipt.exists() and not request.exists()


def test_cancelling_graceful_timeout_refused_before_registration(tmp_path, monkeypatch):
    for key in ['DEVCORE_LOCAL_ROOT', 'DEVCORE_DATA_ROOT', 'DEVCORE_PLATFORM_ROOT']:
        monkeypatch.setenv(key, str(tmp_path))
    with pytest.raises(ValueError, match='must not cancel'):
        runtime.run_managed(None, host='127.0.0.1', port=20130, service='router', timeout_graceful_shutdown=1)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('raises', [False, True])
def test_failed_shutdown_hook_never_reports_success(tmp_path, monkeypatch, raises):
    release = threading.Event()
    async def app(scope, receive, send):
        while True:
            event = await receive()
            if event['type'] == 'lifespan.startup':
                await send({'type': 'lifespan.startup.complete'})
            elif event['type'] == 'lifespan.shutdown':
                if raises:
                    raise RuntimeError('fixture hook failure')
                await send({'type': 'lifespan.shutdown.failed', 'message': 'fixture hook failure'})
                return
    with fixture_server(tmp_path, monkeypatch, app, release) as (_, server, errors):
        result = runtime.request_stop(tmp_path, tmp_path / 'data', tmp_path / 'platform', 'drain-fixture', 5)
        server.join(timeout=3)
        assert not server.is_alive() and not errors
        assert result['shutdown_finished'] and not result['shutdown_completed']
        assert result['status'] == 'shutdown_failed' and result['outcome'] == 'lifespan_error'
        _, _, guard = runtime.paths(tmp_path, 'drain-fixture')
        assert runtime.read_record(guard.with_suffix('.result.json'))['outcome'] == 'lifespan_error'


def test_terminal_publication_failure_preserves_signals(tmp_path, monkeypatch):
    release = threading.Event()
    async def app(scope, receive, send):
        while True:
            event = await receive()
            await send({'type': event['type'] + '.complete'})
            if event['type'] == 'lifespan.shutdown':
                return
    original = runtime.write_json
    def fail_result(path, payload):
        if str(path).endswith('.result.json'):
            raise OSError('fixture result disk failure')
        return original(path, payload)
    monkeypatch.setattr(runtime, 'write_json', fail_result)
    with fixture_server(tmp_path, monkeypatch, app, release) as (_, server, errors):
        result = runtime.request_stop(tmp_path, tmp_path / 'data', tmp_path / 'platform', 'drain-fixture', 1)
        server.join(timeout=3)
        receipt, request, _ = runtime.paths(tmp_path, 'drain-fixture')
        assert not server.is_alive() and len(errors) == 1 and isinstance(errors[0], OSError)
        assert not result['shutdown_completed'] and not result['shutdown_finished']
        assert receipt.exists() and request.exists()


@pytest.mark.parametrize('defer_cleanup', [False, True])
def test_real_websocket_closes_with_restart_code_and_finishes_hook(tmp_path, monkeypatch, defer_cleanup):
    from websockets.sync.client import connect
    from websockets.exceptions import ConnectionClosed
    release, disconnected, hook_done = threading.Event(), threading.Event(), threading.Event()
    disconnect_codes = []
    async def app(scope, receive, send):
        if scope['type'] == 'lifespan':
            while True:
                event = await receive()
                await send({'type': event['type'] + '.complete'})
                if event['type'] == 'lifespan.shutdown':
                    hook_done.set()
                    return
        assert scope['type'] == 'websocket'
        event = await receive()
        assert event['type'] == 'websocket.connect'
        await send({'type': 'websocket.accept'})
        while True:
            event = await receive()
            if event['type'] == 'websocket.disconnect':
                disconnect_codes.append(event['code'])
                disconnected.set()
                if defer_cleanup:
                    await asyncio.to_thread(release.wait, 8)
                return
            await send({'type': 'websocket.send', 'text': event['text']})
    with fixture_server(tmp_path, monkeypatch, app, release) as (port, server, errors):
        with connect(f'ws://127.0.0.1:{port}/', open_timeout=3, close_timeout=2, proxy=None) as client:
            client.send('fixture')
            assert client.recv(timeout=3) == 'fixture'
            result = runtime.request_stop(tmp_path, tmp_path / 'data', tmp_path / 'platform', 'drain-fixture', .5 if defer_cleanup else 5)
            with pytest.raises(ConnectionClosed) as closed:
                client.recv(timeout=3)
            assert closed.value.rcvd.code == 1012
        if defer_cleanup:
            assert disconnected.wait(2) and server.is_alive() and not hook_done.is_set()
            assert not result['shutdown_completed']
            receipt, request, _ = runtime.paths(tmp_path, 'drain-fixture')
            assert receipt.exists() and request.exists()
            release.set()
        server.join(timeout=3)
        assert disconnected.is_set() and disconnect_codes == [1012]
        assert hook_done.is_set() and not errors and not server.is_alive()
        _, _, guard = runtime.paths(tmp_path, 'drain-fixture')
        assert runtime.read_record(guard.with_suffix('.result.json'))['outcome'] == 'ok'
        assert result['shutdown_completed'] is (not defer_cleanup)
