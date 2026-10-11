"""Snapshot resynchronization across reconnection and API module restart."""
import asyncio
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from dashboard import snapshots
from dashboard.sse_cursor import parse_snapshot_cursor, event_frame


@pytest.mark.parametrize('bad', ['', 'snapshot:../foreign', 'snapshot:' + 'a' * 33,
    'snapshot:' + 'A' * 32, 'snapshot:' + 'a' * 32 + '\nretry:0', 'ts_2', 1])
def test_invalid_or_injectable_cursors_refused(bad):
    with pytest.raises(ValueError):
        parse_snapshot_cursor(bad)


@pytest.fixture
def api(tmp_path, monkeypatch):
    for name in ('DEVCORE_LOCAL_ROOT', 'DEVCORE_DATA_ROOT', 'DEVCORE_PLATFORM_ROOT'):
        monkeypatch.setenv(name, str(tmp_path / name))
    def load():
        spec = importlib.util.spec_from_file_location('sse_cursor_fixture', Path(__file__).with_name('dashboard_api.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        monkeypatch.setattr(module, 'refresh_dashboard_payload_cache', lambda: pytest.fail('reconnect regenerated snapshot'))
        return module
    return load


def publish(api, label):
    text = json.dumps({'schema_version': 1, 'label': label})
    return snapshots.publish_snapshot(api.get_local_path('Dashboard'), {
        'dashboard_payload.json': text, 'payload_hash.txt': hashlib.sha256(text.encode()).hexdigest(),
        'index.html': '<html>fixture</html>', 'index_terminal.html': '<html>fixture</html>',
    })


@pytest.mark.parametrize('mismatch', [False, True])
def test_reconnect_current_cursor_or_old_cursor_after_restart(api, mismatch):
    first = api()
    old = 'snapshot:' + publish(first, 'previous')
    current = 'snapshot:' + publish(first, 'current') if mismatch else old
    restarted = api()
    class Request:
        headers = {'last-event-id': old}
        async def is_disconnected(self):
            return True
    async def scenario():
        generator = restarted.event_generator(Request())
        connected = await anext(generator)
        assert 'Connected' in connected
        if mismatch:
            assert 'id:' not in connected  # Interrupted connection retains its previous cursor.
        else:
            assert 'id: ' + current in connected
        if mismatch:
            frame = await anext(generator)
            assert 'event: dashboard.delta' in frame
            assert 'id: ' + current in frame
            data = json.loads(next(line[6:] for line in frame.splitlines() if line.startswith('data: ')))
            assert data['snapshot_required'] is True
            assert data['recovery'] == 'reload_snapshot'
        with pytest.raises(StopAsyncIteration):
            await anext(generator)
    asyncio.run(scenario())


@pytest.mark.parametrize('change', ['input_during_cursor', 'input_after_connected', 'publication_after_connected'])
def test_handshake_window_changes_are_not_absorbed_as_baseline(api, monkeypatch, change):
    from dashboard.input_watcher import InputWatcher
    module = api()
    cursor_a = 'snapshot:' + publish(module, 'initial')
    signature = [1]
    probes = []
    regenerated = []
    current = [cursor_a]
    monkeypatch.setattr(module, '_sse_inputs', InputWatcher(interval=0))
    monkeypatch.setattr(module, '_sse_publications', InputWatcher(interval=0))
    def probe():
        probes.append(signature[0])
        return signature[0]
    monkeypatch.setattr(module, 'get_dashboard_input_signature', probe)
    original_cursor = module.get_dashboard_snapshot_cursor
    cursor_reads = []
    def read_cursor():
        cursor = original_cursor()
        cursor_reads.append(cursor)
        if len(cursor_reads) == 1:
            assert probes == [1]  # Baseline precedes the first cursor read.
            if change == 'input_during_cursor':
                signature[0] = 2
        return cursor
    monkeypatch.setattr(module, 'get_dashboard_snapshot_cursor', read_cursor)
    def regenerate():
        regenerated.append(signature[0])
        current[0] = 'snapshot:' + publish(module, 'regenerated')
    monkeypatch.setattr(module, 'refresh_dashboard_payload_cache', regenerate)
    real_sleep = asyncio.sleep
    async def poll_without_delay(_):
        await real_sleep(0)
    monkeypatch.setattr(module.asyncio, 'sleep', poll_without_delay)
    class Request:
        headers = {'last-event-id': cursor_a}
        checks = 0
        async def is_disconnected(self):
            self.checks += 1
            return self.checks > 1
    async def scenario():
        generator = module.event_generator(Request())
        try:
            connected = await anext(generator)
            assert 'id: ' + cursor_a in connected
            if change == 'input_after_connected':
                signature[0] = 2
            elif change == 'publication_after_connected':
                current[0] = 'snapshot:' + publish(module, 'independent')
            frame = await asyncio.wait_for(anext(generator), timeout=3)
            assert 'event: dashboard.delta' in frame
            assert 'id: ' + current[0] in frame
            assert current[0] != cursor_a
            payload = json.loads(next(line[6:] for line in frame.splitlines() if line.startswith('data: ')))
            assert payload['has_changes'] is True
            assert payload['cursor'] == current[0]
            if change == 'publication_after_connected':
                assert payload['snapshot_required'] is True
                assert regenerated == []  # An existing publication needs no producer.
                assert probes == [1, 1]
            else:
                assert regenerated == [2]
                assert probes == [1, 2]
            with pytest.raises(StopAsyncIteration):
                await anext(generator)
        finally:
            await generator.aclose()
    asyncio.run(scenario())


def test_publication_after_recovery_frame_is_not_reannounced_when_stable(api, monkeypatch):
    from dashboard.input_watcher import InputWatcher
    module = api()
    old = 'snapshot:' + publish(module, 'old')
    cursor_a = 'snapshot:' + publish(module, 'initial')
    monkeypatch.setattr(module, '_sse_inputs', InputWatcher(interval=0))
    monkeypatch.setattr(module, '_sse_publications', InputWatcher(interval=0))
    monkeypatch.setattr(module, 'get_dashboard_input_signature', lambda: 1)
    monkeypatch.setattr(module, 'DASHBOARD_SSE_HEARTBEAT_SECONDS', 0)
    real_sleep = asyncio.sleep
    async def poll_without_delay(_):
        await real_sleep(0)
    monkeypatch.setattr(module.asyncio, 'sleep', poll_without_delay)
    class Request:
        headers = {'last-event-id': old}
        checks = 0
        async def is_disconnected(self):
            self.checks += 1
            return self.checks > 2
    async def scenario():
        generator = module.event_generator(Request())
        try:
            assert 'id:' not in await anext(generator)
            assert 'id: ' + cursor_a in await anext(generator)
            cursor_b = 'snapshot:' + publish(module, 'after_recovery')
            delta = await asyncio.wait_for(anext(generator), 3)
            assert 'event: dashboard.delta' in delta
            assert 'id: ' + cursor_b in delta
            # Stable generation must heartbeat, not send another reset/producer.
            assert await asyncio.wait_for(anext(generator), 3) == ': heartbeat\n\n'
            with pytest.raises(StopAsyncIteration):
                await anext(generator)
        finally:
            await generator.aclose()
    asyncio.run(scenario())


def test_twenty_streams_share_periodic_generation_probe(api, monkeypatch):
    from dashboard.input_watcher import InputWatcher
    module = api()
    cursor_a = 'snapshot:' + publish(module, 'initial')
    watcher = InputWatcher(interval=60)
    monkeypatch.setattr(module, '_sse_publications', watcher)
    monkeypatch.setattr(module, 'get_dashboard_input_signature', lambda: 1)
    original = module.get_dashboard_snapshot_cursor
    calls = []
    def probe():
        calls.append(1)
        return original()
    monkeypatch.setattr(module, 'get_dashboard_snapshot_cursor', probe)
    class Request:
        headers = {'last-event-id': cursor_a}
        async def is_disconnected(self):
            return False
    async def scenario():
        generators = [module.event_generator(Request()) for _ in range(20)]
        try:
            frames = await asyncio.gather(*(anext(g) for g in generators))
            assert all('id: ' + cursor_a in frame for frame in frames)
            assert len(calls) == 21  # Shared observation plus twenty fresh handshakes.
            cursor_b = 'snapshot:' + publish(module, 'independent')
            watcher.interval = 0  # Force the next shared observation without a clock delay.
            frames = await asyncio.wait_for(asyncio.gather(*(anext(g) for g in generators)), 4)
            assert all('event: dashboard.delta' in frame and 'id: ' + cursor_b in frame for frame in frames)
            assert len(calls) == 22  # Exactly one periodic pin for twenty streams.
        finally:
            await asyncio.gather(*(g.aclose() for g in generators))
    asyncio.run(scenario())


def test_old_shared_sample_does_not_reannounce_cursor_before_fresh_handshake(api, monkeypatch):
    from dashboard.input_watcher import InputWatcher
    module = api()
    watcher = InputWatcher(interval=60)
    monkeypatch.setattr(module, '_sse_publications', watcher)
    monkeypatch.setattr(module, 'get_dashboard_input_signature', lambda: 1)
    cursor_a = 'snapshot:' + 'a' * 32
    cursor_b = 'snapshot:' + 'b' * 32
    cursors = iter([cursor_a, cursor_b])
    monkeypatch.setattr(module, 'get_dashboard_snapshot_cursor', lambda: next(cursors))
    monkeypatch.setattr(module, 'DASHBOARD_SSE_HEARTBEAT_SECONDS', 0)
    class Request:
        headers = {'last-event-id': cursor_b}
        async def is_disconnected(self):
            return False
    async def scenario():
        generator = module.event_generator(Request())
        try:
            assert 'id: ' + cursor_b in await anext(generator)
            # The cached A sample is older than fresh B; no false reset to A.
            assert await asyncio.wait_for(anext(generator), 3) == ': heartbeat\n\n'
        finally:
            await generator.aclose()
    asyncio.run(scenario())


def test_twenty_faulting_streams_log_once_and_do_not_emit_success(api, monkeypatch):
    from dashboard.error_reporter import SseErrorReporter
    module = api()
    messages = []
    monkeypatch.setattr(module, '_sse_errors', SseErrorReporter(emit=messages.append))
    failing = [False]
    class Inputs:
        async def revision(self, _):
            if failing[0]:
                raise OSError('fixture storage unavailable')
            return 1
    monkeypatch.setattr(module, '_sse_inputs', Inputs())
    class Request:
        headers = {}
        checks = 0
        async def is_disconnected(self):
            self.checks += 1
            return self.checks > 1
    async def scenario():
        generators = [module.event_generator(Request()) for _ in range(20)]
        try:
            assert all('Connected' in frame for frame in await asyncio.gather(*(anext(g) for g in generators)))
            failing[0] = True
            results = await asyncio.wait_for(asyncio.gather(
                *(anext(g) for g in generators), return_exceptions=True), 4)
            assert all(isinstance(result, StopAsyncIteration) for result in results)
            assert len(messages) == 1
            assert 'loop: fixture storage unavailable' in messages[0]
        finally:
            await asyncio.gather(*(g.aclose() for g in generators))
    asyncio.run(scenario())


def test_route_rejects_bad_cursor_before_opening_stream(api):
    from fastapi import HTTPException
    module = api()
    class Request:
        headers = {'last-event-id': 'invalid'}
    with pytest.raises(HTTPException) as error:
        asyncio.run(module.dashboard_stream_route(Request()))
    assert error.value.status_code == 400


def test_frame_keeps_payload_on_one_data_line():
    cursor = 'snapshot:' + 'a' * 32
    frame = event_frame('dashboard.delta', {'text': '\nid:fake'}, cursor)
    assert frame.count('\nid:') == 0
    assert parse_snapshot_cursor(cursor) == cursor
    assert parse_snapshot_cursor(None) is None
