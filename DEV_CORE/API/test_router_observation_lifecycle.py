"""Lifespan owns and drains fresh OTLP workers on isolated loopback fixtures."""
import asyncio
from pathlib import Path
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Scripts.router.observation import observation_lifespan
from devcore_api.llmops_generation import GenerationObserver
from devcore_api.otlp_worker import OtlpWorker
from test_otlp_export import event, exporter, receiver
from Scripts import gemini_router as router


def test_shutdown_stays_pending_until_delayed_export_is_drained():
    with receiver(delayed=True) as (endpoint, calls, entered, release):
        async def scenario():
            worker = OtlpWorker(exporter(endpoint, timeout=5))
            observer = GenerationObserver(worker)
            app = FastAPI(lifespan=observation_lifespan)
            app.state.observation_factory = lambda app: (observer, lambda request, result: event())
            lifecycle = app.router.lifespan_context(app)
            await lifecycle.__aenter__()
            closing = None
            try:
                assert app.state.generation_observer is observer
                worker.submit(event(), start_ns=1, end_ns=2)
                assert await asyncio.to_thread(entered.wait, 1)
                # Shorten only the waiting budget, retaining the real worker/network.
                original_close = worker.aclose
                async def brief_close():
                    return await original_close(wait_seconds=.02)
                worker.aclose = brief_close
                closing = asyncio.create_task(lifecycle.__aexit__(None, None, None))
                await asyncio.sleep(.07)
                assert not closing.done() and worker.snapshot()['running']
                assert not worker.snapshot()['accepting']
                assert worker.submit(event(), start_ns=1, end_ns=2) == 'closed'
                release.set()
                await closing
                assert worker.exporter.closed and worker.snapshot()['accepted'] == 1
                assert not hasattr(app.state, 'generation_observer')
                assert not hasattr(app.state, 'generation_event_factory')
            finally:
                release.set()
                if closing is None:
                    await lifecycle.__aexit__(None, None, None)
                else:
                    await closing
        asyncio.run(scenario())
        assert len(calls) == 1


def test_disabled_lifespan_never_constructs_dependencies():
    async def scenario():
        app = FastAPI(lifespan=observation_lifespan)
        async with app.router.lifespan_context(app):
            assert not hasattr(app.state, 'generation_observer')
        assert not hasattr(app.state, 'generation_event_factory')
    asyncio.run(scenario())


def test_each_lifespan_constructs_and_closes_a_new_worker():
    with receiver() as (endpoint, calls, _, _):
        async def scenario():
            workers = []
            app = FastAPI(lifespan=observation_lifespan)
            def factory(app):
                worker = OtlpWorker(exporter(endpoint))
                workers.append(worker)
                return GenerationObserver(worker), lambda request, result: event()
            app.state.observation_factory = factory
            for _ in range(2):
                async with app.router.lifespan_context(app):
                    app.state.generation_observer.worker.submit(event(), start_ns=1, end_ns=2)
                assert workers[-1].exporter.closed
            assert len(workers) == 2 and workers[0] is not workers[1]
        asyncio.run(scenario())
        assert len(calls) == 2


def test_invalid_factory_callback_fails_startup_and_closes_owned_exporter():
    with receiver() as (endpoint, calls, _, _):
        async def scenario():
            worker = OtlpWorker(exporter(endpoint))
            app = FastAPI(lifespan=observation_lifespan)
            app.state.observation_factory = lambda app: (GenerationObserver(worker), None)
            with pytest.raises(ValueError):
                async with app.router.lifespan_context(app):
                    pytest.fail('Startup must fail')
            assert worker.exporter.closed and not hasattr(app.state, 'generation_observer')
        asyncio.run(scenario())
        assert calls == []


def test_lifespan_body_exception_is_preserved_after_drain():
    with receiver() as (endpoint, calls, _, _):
        async def scenario():
            worker = OtlpWorker(exporter(endpoint))
            app = FastAPI(lifespan=observation_lifespan)
            app.state.observation_factory = lambda app: (GenerationObserver(worker), lambda request, result: event())
            error = RuntimeError('fixture operation failed')
            with pytest.raises(RuntimeError) as caught:
                async with app.router.lifespan_context(app):
                    worker.submit(event(), start_ns=1, end_ns=2)
                    raise error
            assert caught.value is error and worker.exporter.closed
            assert worker.snapshot()['accepted'] == 1
        asyncio.run(scenario())
        assert len(calls) == 1


def test_router_asgi_startup_and_shutdown_own_observation(monkeypatch):
    with receiver() as (endpoint, calls, _, _):
        workers = []
        def factory(app):
            worker = OtlpWorker(exporter(endpoint))
            workers.append(worker)
            return GenerationObserver(worker), lambda request, result: event()
        monkeypatch.setattr(router.app.state, 'observation_factory', factory, raising=False)
        with TestClient(router.app) as client:
            assert client.get('/health').status_code == 200
            assert len(workers) == 1 and workers[0].snapshot()['running']
        assert workers[0].exporter.closed and not workers[0].snapshot()['running']
        assert not hasattr(router.app.state, 'generation_observer') and calls == []


def test_existing_dependencies_are_not_overwritten_or_closed():
    async def scenario():
        app = FastAPI(lifespan=observation_lifespan)
        installed = object()
        app.state.generation_observer = installed
        constructed = []
        app.state.observation_factory = lambda app: constructed.append(1)
        with pytest.raises(RuntimeError, match='already installed'):
            async with app.router.lifespan_context(app):
                pytest.fail('Must refuse conflicting ownership')
        assert constructed == [] and app.state.generation_observer is installed
    asyncio.run(scenario())
