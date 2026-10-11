"""Tracked nonblocking export/drain with real loopback receiver."""
import asyncio
from dataclasses import replace
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from devcore_api.otlp_worker import OtlpWorker
from test_otlp_export import event, exporter, receiver


def test_queued_export_bounds_include_inflight_and_shutdown_timeout_preserves_drain():
    with receiver(delayed=True) as (endpoint, calls, entered, release):
        async def scenario():
            client = exporter(endpoint)
            worker = OtlpWorker(client, max_events=2)
            assert worker.submit(event(), start_ns=1, end_ns=2) == 'not_started'
            worker.start()
            try:
                assert worker.submit(event(), start_ns=1, end_ns=2) == 'queued'
                assert await asyncio.to_thread(entered.wait, 1)
                assert worker.submit(event(), start_ns=1, end_ns=2) == 'queued'
                assert worker.submit(event(), start_ns=1, end_ns=2) == 'dropped'
                metrics = worker.snapshot()
                assert metrics['pending'] == 2 and metrics['queued'] == 1
                assert metrics['dropped'] == 1 and metrics['pending_bytes'] <= metrics['max_bytes']
                await asyncio.sleep(.01)
                assert worker.snapshot()['accepted'] == 0
                assert not await worker.aclose(wait_seconds=.02)
                assert worker.snapshot()['running'] and worker.snapshot()['pending'] == 2
                assert worker.submit(event(), start_ns=1, end_ns=2) == 'closed'
                release.set()
                assert await worker.aclose()
                metrics = worker.snapshot()
                assert metrics['accepted'] == 2 and metrics['pending'] == metrics['pending_bytes'] == 0
                assert not metrics['running'] and client.closed and len(calls) == 2
            finally:
                release.set()
                await worker.aclose()
        asyncio.run(scenario())


def test_byte_limit_refuses_before_network_and_invalid_event_is_not_queued():
    with receiver() as (endpoint, calls, _, _):
        async def scenario():
            worker = OtlpWorker(exporter(endpoint), max_events=100, max_bytes=1024)
            worker.start()
            try:
                assert worker.submit(event(), start_ns=2, end_ns=1) == 'invalid'
                # Explicitly construct and measure a valid oversized fixture.
                large = replace(event(), name='n' * 128, model='m' * 128,
                    project_id='p' * 128, run_id='r' * 128, task_id='t' * 128)
                assert len(worker.exporter.payload(large, 1, 2)) > 1024
                assert worker.submit(large, start_ns=1, end_ns=2) == 'dropped'
                assert worker.snapshot()['pending'] == 0
            finally:
                assert await worker.aclose()
        asyncio.run(scenario())
        assert calls == []


def test_cancelled_shutdown_wait_does_not_cancel_worker():
    with receiver(delayed=True) as (endpoint, calls, entered, release):
        async def scenario():
            worker = OtlpWorker(exporter(endpoint))
            worker.start()
            waiter = None
            try:
                worker.submit(event(), start_ns=1, end_ns=2)
                assert await asyncio.to_thread(entered.wait, 1)
                waiter = asyncio.create_task(worker.aclose())
                await asyncio.sleep(.01)
                waiter.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await waiter
                assert worker.snapshot()['running'] and worker.snapshot()['pending'] == 1
                release.set()
                assert await worker.aclose()
                assert worker.snapshot()['accepted'] == 1 and len(calls) == 1
            finally:
                release.set()
                if waiter is not None and not waiter.done():
                    await waiter
                await worker.aclose()
        asyncio.run(scenario())


@pytest.mark.parametrize('body,status,key', [(b'{"partialSuccess":{"rejectedSpans":"1"}}', 200, 'failed'),
    (b'{"partialSuccess":{"rejectedSpans":"0"}}', 200, 'warnings'), (b'private', 500, 'failed')])
def test_failed_or_warning_exports_are_counted_without_retry(body, status, key):
    with receiver(body=body, status=status) as (endpoint, calls, _, _):
        async def scenario():
            worker = OtlpWorker(exporter(endpoint))
            worker.start()
            worker.submit(event(), start_ns=1, end_ns=2)
            assert await worker.aclose()
            metrics = worker.snapshot()
            assert metrics[key] == 1 and metrics['accepted'] == 0 and metrics['pending'] == 0
            assert 'private' not in str(metrics)
        asyncio.run(scenario())
        assert len(calls) == 1


def test_worker_exception_is_contained_and_queue_continues():
    with receiver() as (endpoint, calls, _, _):
        async def scenario():
            client = exporter(endpoint)
            original = client.export
            attempts = 0
            async def fail_once(*args, **kwargs):
                nonlocal attempts
                attempts += 1
                if attempts == 1:
                    raise RuntimeError('private failure')
                return await original(*args, **kwargs)
            client.export = fail_once
            worker = OtlpWorker(client)
            worker.start()
            for _ in range(2):
                worker.submit(event(), start_ns=1, end_ns=2)
            assert await worker.aclose()
            assert worker.snapshot()['failed'] == worker.snapshot()['accepted'] == 1
            assert len(calls) == 1
        asyncio.run(scenario())
