"""Shared SSE refreshes: parallel clients, revisions, failures, cancellation."""
import asyncio
import importlib.util
from pathlib import Path
import sys
import threading

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from dashboard.refresh_coordinator import RefreshCoordinator


def test_twenty_waiters_share_refresh_and_newer_revision_runs_next():
    async def scenario():
        coordinator = RefreshCoordinator()
        started, release = threading.Event(), threading.Event()
        calls = []
        def producer():
            calls.append(1)
            started.set()
            assert release.wait(3)
        waiters = [asyncio.create_task(coordinator.refresh(1, producer)) for _ in range(20)]
        assert await asyncio.to_thread(started.wait, 3)
        newer = asyncio.create_task(coordinator.refresh(2, producer))
        await asyncio.sleep(0.02)
        assert len(calls) == 1
        release.set()
        assert all(revision >= 1 for revision in await asyncio.gather(*waiters))
        assert await newer == 2
        assert len(calls) == 2
        assert await coordinator.refresh(1, producer) == 2
        assert len(calls) == 2
    asyncio.run(scenario())


def test_cancelled_subscriber_does_not_cancel_shared_producer():
    async def scenario():
        coordinator = RefreshCoordinator()
        started, release = threading.Event(), threading.Event()
        calls = []
        def producer():
            calls.append(1)
            started.set()
            assert release.wait(3)
        first = asyncio.create_task(coordinator.refresh(1, producer))
        assert await asyncio.to_thread(started.wait, 3)
        second = asyncio.create_task(coordinator.refresh(1, producer))
        await asyncio.sleep(0.01)
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        release.set()
        assert await second == 1
        assert calls == [1]
    asyncio.run(scenario())


def test_failed_revision_can_retry_and_never_counts_as_completed():
    async def scenario():
        coordinator = RefreshCoordinator()
        calls = []
        def producer():
            calls.append(1)
            if len(calls) == 1:
                raise OSError('fixture failure')
        with pytest.raises(OSError):
            await coordinator.refresh(1, producer)
        assert await coordinator.refresh(1, producer) == 1
        assert calls == [1, 1]
    asyncio.run(scenario())


def test_twenty_real_event_generators_emit_delta_after_one_refresh(tmp_path, monkeypatch):
    for name in ('DEVCORE_LOCAL_ROOT', 'DEVCORE_DATA_ROOT', 'DEVCORE_PLATFORM_ROOT'):
        monkeypatch.setenv(name, str(tmp_path / name))
    spec = importlib.util.spec_from_file_location('sse_coordinator_api_fixture', Path(__file__).with_name('dashboard_api.py'))
    api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api)
    class Request:
        async def is_disconnected(self):
            return False
    revision = [1]
    calls = []
    def refresh():
        calls.append(1)
    probes = []
    def probe():
        probes.append(1)
        return revision[0]
    monkeypatch.setattr(api, 'get_dashboard_input_signature', probe)
    monkeypatch.setattr(api, 'refresh_dashboard_payload_cache', refresh)
    async def scenario():
        generators = [api.event_generator(Request()) for _ in range(20)]
        assert all('Connected' in message for message in await asyncio.gather(*(anext(g) for g in generators)))
        pending = [asyncio.create_task(anext(g)) for g in generators]
        await asyncio.sleep(0.15)
        revision[0] = 2
        messages = await asyncio.wait_for(asyncio.gather(*pending), 4)
        assert all('dashboard.delta' in message and 'ts_2' in message for message in messages)
        assert calls == [1]
        assert len(probes) == 2  # Initial sample and one changed sample for all twenty clients.
        await asyncio.gather(*(g.aclose() for g in generators))
    asyncio.run(scenario())



def test_failed_sse_refresh_retries_before_announcing_delta(tmp_path, monkeypatch):
    for name in ('DEVCORE_LOCAL_ROOT', 'DEVCORE_DATA_ROOT', 'DEVCORE_PLATFORM_ROOT'):
        monkeypatch.setenv(name, str(tmp_path / name))
    spec = importlib.util.spec_from_file_location('sse_retry_api_fixture', Path(__file__).with_name('dashboard_api.py'))
    api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api)
    class Request:
        async def is_disconnected(self):
            return False
    watched = iter([1, 2, 2, 2])
    calls = []
    monkeypatch.setattr(api, 'get_dashboard_input_signature', lambda: next(watched))
    def refresh():
        calls.append(1)
        if len(calls) == 1:
            raise OSError('fixture unavailable')
    monkeypatch.setattr(api, 'refresh_dashboard_payload_cache', refresh)
    async def scenario():
        generator = api.event_generator(Request())
        assert 'Connected' in await anext(generator)
        message = await asyncio.wait_for(anext(generator), 4)
        assert 'dashboard.delta' in message
        assert calls == [1, 1]
        await generator.aclose()
    asyncio.run(scenario())
