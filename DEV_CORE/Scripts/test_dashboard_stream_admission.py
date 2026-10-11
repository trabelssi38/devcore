"""ASGI stream lifetime must release admission even before a first chunk."""
import asyncio
import gc
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from dashboard.stream_admission import AdmittedStreamingResponse, StreamCapacityExceeded, StreamSlots


@pytest.mark.parametrize('limit', [0, -1, True, None, 1.5, '32'])
def test_invalid_capacity_refused(limit):
    with pytest.raises(ValueError):
        StreamSlots(limit)


def test_slot_release_is_idempotent_and_loops_are_independent():
    slots = StreamSlots(1)
    async def scenario():
        release = slots.reserve()
        with pytest.raises(StreamCapacityExceeded):
            slots.reserve()
        release()
        release()
        release = slots.reserve()
        with pytest.raises(StreamCapacityExceeded):
            slots.reserve()
        release()
    asyncio.run(scenario())
    asyncio.run(scenario())


def test_response_abandoned_before_asgi_dispatch_releases_slot_on_collection():
    async def scenario():
        slots = StreamSlots(1)
        async def content():
            yield 'data: Connected\n\n'
        response = AdmittedStreamingResponse(content(), slots)
        with pytest.raises(StreamCapacityExceeded):
            slots.reserve()
        del response
        gc.collect()
        release = slots.reserve()
        release()
    asyncio.run(scenario())


@pytest.mark.parametrize('outcome', ['complete', 'generator_error', 'send_error', 'cancel_before_chunk'])
def test_asgi_lifetime_releases_slot_and_closes_generator(outcome):
    async def scenario():
        slots = StreamSlots(1)
        started, block = asyncio.Event(), asyncio.Event()
        closed = []
        async def content():
            try:
                started.set()
                if outcome == 'cancel_before_chunk':
                    await block.wait()
                if outcome == 'generator_error':
                    raise OSError('fixture read unavailable')
                yield 'data: Connected\n\n'
            finally:
                closed.append(True)
        response = AdmittedStreamingResponse(content(), slots, media_type='text/event-stream')
        with pytest.raises(StreamCapacityExceeded):
            slots.reserve()
        async def send(message):
            if outcome == 'send_error' and message['type'] == 'http.response.body':
                raise OSError('fixture disconnected')
        async def receive():
            return {'type': 'http.disconnect'}
        task = asyncio.create_task(response({'type': 'http', 'asgi': {'spec_version': '2.4'}}, receive, send))
        if outcome == 'cancel_before_chunk':
            await started.wait()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        elif outcome in ('generator_error', 'send_error'):
            with pytest.raises(Exception):
                await task
        else:
            await task
        assert closed == [True]
        release = slots.reserve()
        release()
    asyncio.run(scenario())


def test_route_admits_32_refuses_burst_and_status_remains_available(tmp_path, monkeypatch):
    for name in ('DEVCORE_LOCAL_ROOT', 'DEVCORE_DATA_ROOT', 'DEVCORE_PLATFORM_ROOT'):
        monkeypatch.setenv(name, str(tmp_path / name))
    spec = importlib.util.spec_from_file_location('stream_admission_fixture', Path(__file__).with_name('dashboard_api.py'))
    api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api)
    from fastapi import HTTPException
    class Request:
        headers = {}
    async def content(_):
        yield 'data: Connected\n\n'
    monkeypatch.setattr(api, 'event_generator', content)
    async def scenario():
        responses = [await api.dashboard_stream_route(Request()) for _ in range(32)]
        for _ in range(68):
            with pytest.raises(HTTPException) as error:
                await api.dashboard_stream_route(Request())
            assert error.value.status_code == 503
            assert error.value.headers == {'Retry-After': '5'}
        # A short endpoint goes through the actual isolated ASGI application.
        import httpx
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app), base_url='http://fixture') as client:
            assert (await client.get('/api/status')).status_code == 200
        async def receive():
            return {'type': 'http.disconnect'}
        async def send(_):
            pass
        await asyncio.gather(*(r({'type': 'http', 'asgi': {'spec_version': '2.4'}}, receive, send) for r in responses))
        # All slots return after normal ASGI completion.
        response = await api.dashboard_stream_route(Request())
        await response({'type': 'http', 'asgi': {'spec_version': '2.4'}}, receive, send)
    asyncio.run(scenario())


@pytest.mark.parametrize('with_snapshot', [False, True])
def test_real_http_streams_release_capacity_through_uvicorn_and_middlewares(tmp_path, monkeypatch, with_snapshot):
    launcher = tmp_path / 'server_fixture.py'
    port_file = tmp_path / 'port.json'
    spec_file = tmp_path / 'asgi.json'
    launcher.write_text(r'''
import importlib.util,json,socket,sys
from pathlib import Path
import uvicorn
spec=importlib.util.spec_from_file_location('socket_admission_fixture',sys.argv[1])
api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)
def refuse_producer():
    Path(sys.argv[3]+'.producer-called').write_text('unexpected producer attempt')
    raise AssertionError('Network recipe must not run the dashboard producer')
api.refresh_dashboard_payload_cache=refuse_producer
async def application(scope,receive,send):
    if scope['type']=='http':
        Path(sys.argv[3]).write_text(json.dumps(scope.get('asgi',{})))
    await api.app(scope,receive,send)
sock=socket.socket();sock.bind(('127.0.0.1',0))
Path(sys.argv[2]).write_text(json.dumps({'port':sock.getsockname()[1],'uvicorn':uvicorn.__version__}))
uvicorn.Server(uvicorn.Config(application,log_level='warning',lifespan='off')).run(sockets=[sock])
''', encoding='utf-8')
    env = os.environ.copy()
    for name in ('DEVCORE_LOCAL_ROOT', 'DEVCORE_DATA_ROOT', 'DEVCORE_PLATFORM_ROOT'):
        env[name] = str(tmp_path / name.lower())
        monkeypatch.setenv(name, env[name])
    env['DEVCORE_DASHBOARD_AUTH_PROFILE'] = 'legacy'
    from dashboard.snapshots import publish_snapshot
    from dashboard.generation_lock import DashboardLock
    def publish(label):
        text = json.dumps({'schema_version': 1, 'sections': {}, 'label': label})
        with DashboardLock(wait_timeout=1):
            return 'snapshot:' + publish_snapshot(Path(env['DEVCORE_LOCAL_ROOT']) / 'Dashboard', {
                'dashboard_payload.json': text, 'payload_hash.txt': hashlib.sha256(text.encode()).hexdigest(),
                'index.html': '<html>fixture</html>', 'index_terminal.html': '<html>fixture</html>',
            })
    cursor_a = publish('A') if with_snapshot else None
    log_path = tmp_path / 'server.log'
    with log_path.open('w', encoding='utf-8') as log:
        process = subprocess.Popen([sys.executable, str(launcher), str(Path(__file__).with_name('dashboard_api.py')),
                                    str(port_file), str(spec_file)], env=env, stdout=log, stderr=log,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        try:
            deadline = time.monotonic() + 15
            while not port_file.exists():
                assert process.poll() is None, log_path.read_text(encoding='utf-8')
                assert time.monotonic() < deadline, 'Temporary server did not start'
                time.sleep(0.05)
            metadata = json.loads(port_file.read_text())
            async def scenario():
                import httpx
                responses, iterators = [], []
                async with httpx.AsyncClient(base_url='http://127.0.0.1:' + str(metadata['port']),
                                             trust_env=False, timeout=5,
                                             limits=httpx.Limits(max_connections=64)) as client:
                    try:
                        for _ in range(100):
                            try:
                                ready = await client.get('/api/status')
                                if ready.status_code == 200:
                                    break
                            except httpx.ConnectError:
                                pass
                            await asyncio.sleep(0.05)
                        else:
                            pytest.fail('Temporary API did not become ready')
                        async def open_stream(headers=None):
                            response = await client.send(client.build_request('GET', '/api/dashboard/stream', headers=headers), stream=True)
                            responses.append(response)
                            return response
                        async def frame(lines):
                            fields = {}
                            async for line in lines:
                                if not line and fields:
                                    return fields
                                if ': ' in line:
                                    name, value = line.split(': ', 1)
                                    fields[name] = value
                            pytest.fail('Stream ended before a complete SSE frame')
                        initial = await asyncio.gather(*(open_stream() for _ in range(32)))
                        assert all(r.status_code == 200 for r in initial)
                        for response in initial:
                            lines = response.aiter_lines()
                            iterators.append(lines)
                            connected = await frame(lines)
                            assert connected['event'] == 'message'
                            assert connected['data'] == 'Connected'
                            assert connected.get('id') == cursor_a
                        refused = await client.get('/api/dashboard/stream')
                        assert refused.status_code == 503
                        assert refused.headers['retry-after'] == '5'
                        assert (await client.get('/api/status')).status_code == 200
                        if with_snapshot:
                            cursor_b = publish('B')
                            deltas = await asyncio.wait_for(asyncio.gather(*(frame(it) for it in iterators)), 4)
                            assert all(delta['event'] == 'dashboard.delta' and delta['id'] == cursor_b for delta in deltas)
                            assert all(json.loads(delta['data'])['snapshot_required'] is True for delta in deltas)
                            snapshot = await client.get('/api/dashboard')
                            assert snapshot.status_code == 200
                            assert snapshot.json()['label'] == 'B'
                            assert snapshot.json()['cache']['snapshot_cursor'] == cursor_b
                        await initial[0].aclose()  # Real TCP/client closure, not a synthetic ASGI send error.
                        for _ in range(40):
                            replacement = await open_stream({'Last-Event-ID': cursor_a} if with_snapshot else None)
                            if replacement.status_code == 200:
                                break
                            assert replacement.status_code == 503
                            await replacement.aclose()
                            await asyncio.sleep(0.05)
                        else:
                            pytest.fail('Closed client did not release SSE admission')
                        if with_snapshot:
                            lines = replacement.aiter_lines()
                            iterators.append(lines)
                            connected = await frame(lines)
                            assert connected['data'] == 'Connected' and 'id' not in connected
                            recovery = await frame(lines)
                            assert recovery['id'] == cursor_b
                            assert json.loads(recovery['data'])['recovery'] == 'reload_snapshot'
                        await asyncio.gather(*(response.aclose() for response in responses))
                        # Full capacity is available again after all sockets close.
                        for _ in range(40):
                            reopened = await asyncio.gather(*(open_stream() for _ in range(32)))
                            if all(r.status_code == 200 for r in reopened):
                                break
                            await asyncio.gather(*(r.aclose() for r in reopened))
                            await asyncio.sleep(0.05)
                        else:
                            pytest.fail('All closed streams did not return full capacity')
                        assert (await client.get('/api/status')).status_code == 200
                    finally:
                        await asyncio.gather(*(r.aclose() for r in responses))
                        await asyncio.gather(*(it.aclose() for it in iterators))
            asyncio.run(scenario())
            assert not Path(str(spec_file) + '.producer-called').exists(), 'Network recipe attempted regeneration'
            print(json.dumps({'connections': 32, 'closed_and_reopened': True, 'publication_and_recovery': with_snapshot,
                              'uvicorn': metadata['uvicorn'], 'asgi': json.loads(spec_file.read_text())}))
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
