"""Capacity stays bounded through streams/WS and is freed after failure."""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from Scripts.headroom_routes import RouteGuard
from Scripts.router.admission import AdmissionGuard, COUNTER_MAX


def http_scope(method='POST'):
    return {'type': 'http', 'path': '/v1/responses', 'method': method, 'headers': []}


def test_slow_body_is_refused_without_reading_and_health_stays_available():
    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()
        async def app(scope, receive, send):
            pytest.fail('Incomplete/refused body reached upstream')
        guard = RouteGuard(app, 'native', max_requests=1)
        async def slow_receive():
            entered.set()
            await release.wait()
            return {'type': 'http.disconnect'}
        async def no_receive():
            pytest.fail('Overload must be refused before reading the body')
        async def discard(event):
            pass
        output = []
        async def capture(event):
            output.append(event)
        slow = asyncio.create_task(guard(http_scope(), slow_receive, discard))
        try:
            await entered.wait()
            await asyncio.wait_for(guard(http_scope(), no_receive, capture), .5)
            assert output[0]['status'] == 503
            assert (b'retry-after', b'1') in output[0]['headers']
            assert json.loads(output[1]['body'])['error']['type'] == 'service_capacity_exceeded'
            health = dict(http_scope('GET'), path='/healthz')
            output.clear()
            await asyncio.wait_for(guard(health, no_receive, capture), .5)
            assert output[0]['status'] == 503  # Not ready, not capacity refusal.
            assert json.loads(output[1]['body'])['status'] == 'not_ready'
            assert not slow.done()
        finally:
            release.set()
            await asyncio.wait_for(slow, .5)
    asyncio.run(scenario())


@pytest.mark.parametrize('kind', ['http', 'websocket'])
def test_stream_or_websocket_keeps_slot_and_other_instance_is_independent(kind):
    async def scenario():
        started, release = asyncio.Event(), asyncio.Event()
        calls = []
        async def app(scope, receive, send):
            calls.append(scope['type'])
            await send({'type': 'websocket.accept'} if kind == 'websocket' else
                {'type': 'http.response.start', 'status': 200, 'headers': []})
            started.set()
            await release.wait()
        async def no_receive():
            pytest.fail('Fixture does not read')
        async def discard(event):
            pass
        output = []
        async def capture(event):
            output.append(event)
        guard = AdmissionGuard(app, max_requests=1)
        scope = http_scope() if kind == 'http' else {'type': 'websocket', 'path': '/v1/responses'}
        active = asyncio.create_task(guard(scope, no_receive, discard))
        try:
            await started.wait()
            await asyncio.wait_for(guard(scope, no_receive, capture), .5)
            assert calls == [kind] and not active.done()
            metrics = guard.snapshot()
            assert metrics['active'] == metrics['peak_active'] == metrics['admitted'] == 1
            assert metrics['finished'] == 0
            assert metrics['rejected_websocket' if kind == 'websocket' else 'rejected_http'] == 1
            if kind == 'websocket':
                assert output[0] == {'type': 'websocket.close', 'code': 1013}
            else:
                assert output[0]['status'] == 503
            async def other_app(scope, receive, send):
                await send({'type': 'http.response.start', 'status': 200, 'headers': []})
            other = AdmissionGuard(other_app, max_requests=1)
            output.clear()
            await other(http_scope(), no_receive, capture)
            assert output[0]['status'] == 200
            assert other.snapshot()['admitted'] == 1 and other.snapshot()['rejected_http'] == 0
        finally:
            release.set()
            await asyncio.wait_for(active, .5)
        output.clear()
        await guard(scope, no_receive, capture)
        assert calls == [kind, kind]
        assert guard.snapshot()['active'] == 0 and guard.snapshot()['finished'] == 2
    asyncio.run(scenario())


@pytest.mark.parametrize('failure', ['cancel', 'error'])
def test_slot_released_on_cancellation_or_application_error(failure):
    async def scenario():
        entered = asyncio.Event()
        count = 0
        async def app(scope, receive, send):
            nonlocal count
            count += 1
            if count == 1:
                entered.set()
                if failure == 'error':
                    raise RuntimeError('fixture')
                await asyncio.Event().wait()
        async def unused(*args):
            pass
        guard = AdmissionGuard(app, max_requests=1)
        task = asyncio.create_task(guard(http_scope(), unused, unused))
        await entered.wait()
        if failure == 'cancel':
            task.cancel()
        with pytest.raises(asyncio.CancelledError if failure == 'cancel' else RuntimeError):
            await task
        await guard(http_scope(), unused, unused)
        assert count == 2
        metrics = guard.snapshot()
        assert metrics['active'] == 0 and metrics['finished'] == 1
        assert metrics['cancelled' if failure == 'cancel' else 'exceptions'] == 1
    asyncio.run(scenario())


def test_diagnostic_remains_bounded_at_capacity_and_never_reads_sensitive_input():
    async def scenario():
        started, release = asyncio.Event(), asyncio.Event()
        async def app(scope, receive, send):
            started.set()
            await release.wait()
        async def no_receive():
            pytest.fail('Diagnostic must not read the request body')
        async def discard(event):
            pass
        output = []
        async def capture(event):
            output.append(event)
        guard = AdmissionGuard(app, max_requests=1)
        task = asyncio.create_task(guard(http_scope(), no_receive, discard))
        try:
            await started.wait()
            diagnostic = dict(http_scope('GET'), path='/devcore/admission',
                query_string=b'prompt=private', headers=[(b'authorization', b'Bearer private')])
            await asyncio.wait_for(guard(diagnostic, no_receive, capture), .5)
            assert output[0]['status'] == 200
            assert (b'cache-control', b'no-store') in output[0]['headers']
            raw = output[1]['body']
            assert len(raw) < 1024 and b'private' not in raw
            assert json.loads(raw)['active'] == 1
            assert guard.snapshot()['admitted'] == 1
            # Counters saturate without wrapping or unbounded output growth.
            guard.counters = dict.fromkeys(guard.counters, COUNTER_MAX)
            for key in guard.counters:
                guard.count(key)
            assert guard.snapshot()['counters_saturated']
            assert len(json.dumps(guard.snapshot()).encode()) < 1024
        finally:
            release.set()
            await task
    asyncio.run(scenario())
