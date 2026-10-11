"""Observation preserves provider result/errors; real loopback export only."""
import asyncio
from dataclasses import replace
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from devcore_api.llmops_generation import GenerationObserver
from devcore_api.otlp_worker import OtlpWorker
from test_otlp_export import event, exporter, receiver


def test_generation_returns_before_export_and_retains_model_usage_and_timing():
    with receiver(delayed=True) as (endpoint, calls, entered, release):
        async def scenario():
            worker = OtlpWorker(exporter(endpoint))
            worker.start()
            times = iter((10, 20))
            observer = GenerationObserver(worker, clock=lambda: next(times))
            result = {'content': 'private prompt and output', 'model': 'gpt-test', 'usage': (1, 2)}
            async def operation():
                await asyncio.sleep(0)
                return result
            try:
                def factory(value):
                    template = event()
                    prompt, completion = value['usage']
                    return replace(template, model=value['model'], usage=replace(template.usage,
                        prompt_tokens=prompt, completion_tokens=completion,
                        total_tokens=prompt + completion))
                returned = await observer.run(operation, event_from_result=factory)
                assert returned is result
                assert observer.snapshot()['queued'] == 1
                assert await asyncio.to_thread(entered.wait, 1)
                assert worker.snapshot()['accepted'] == 0
                body = json.loads(calls[0][2])
                span = body['resourceSpans'][0]['scopeSpans'][0]['spans'][0]
                attrs = {v['key']: v['value']['stringValue'] for v in span['attributes']}
                assert span['startTimeUnixNano'] == '10' and span['endTimeUnixNano'] == '20'
                assert attrs['gen_ai.request.model'] == 'gpt-test'
                assert attrs['devcore.prompt_tokens'] == '1'
                assert attrs['devcore.completion_tokens'] == '2'
                assert 'private' not in str(body) + str(observer.snapshot())
            finally:
                release.set()
                assert await worker.aclose()
        asyncio.run(scenario())


@pytest.mark.parametrize('failure', [RuntimeError('private failure'), asyncio.CancelledError()])
def test_provider_failure_and_cancellation_propagate_without_event(failure):
    with receiver() as (endpoint, calls, _, _):
        async def scenario():
            worker = OtlpWorker(exporter(endpoint))
            worker.start()
            observer = GenerationObserver(worker)
            factory_called = False
            def factory(value):
                nonlocal factory_called
                factory_called = True
                return event()
            async def operation():
                raise failure
            try:
                with pytest.raises(type(failure)) as caught:
                    await observer.run(operation, event_from_result=factory)
                assert caught.value is failure and not factory_called
                assert worker.snapshot()['pending'] == 0
            finally:
                assert await worker.aclose()
        asyncio.run(scenario())
        assert calls == []


def test_saturated_export_does_not_block_next_generation():
    with receiver(delayed=True) as (endpoint, calls, entered, release):
        async def scenario():
            worker = OtlpWorker(exporter(endpoint), max_events=1)
            worker.start()
            observer = GenerationObserver(worker)
            result = object()
            async def operation():
                return result
            try:
                assert await observer.run(operation, event_from_result=lambda value: event()) is result
                assert await asyncio.to_thread(entered.wait, 1)
                assert await observer.run(operation, event_from_result=lambda value: event()) is result
                assert observer.snapshot()['queued'] == observer.snapshot()['refused'] == 1
                assert worker.snapshot()['pending'] == worker.snapshot()['dropped'] == 1
            finally:
                release.set()
                assert await worker.aclose()
        asyncio.run(scenario())
        assert len(calls) == 1


@pytest.mark.parametrize('mode', ['factory_error', 'invalid', 'closed', 'clock_error', 'backward_clock'])
def test_observation_failure_does_not_change_result_or_call_provider_twice(mode):
    with receiver() as (endpoint, calls, _, _):
        async def scenario():
            worker = OtlpWorker(exporter(endpoint))
            worker.start()
            if mode == 'closed':
                assert await worker.aclose()
            times = iter((20, 10))
            def clock():
                if mode == 'clock_error':
                    raise RuntimeError('private clock')
                return next(times) if mode == 'backward_clock' else 10
            observer = GenerationObserver(worker, clock=clock)
            count = 0
            result = object()
            async def operation():
                nonlocal count
                count += 1
                return result
            def factory(value):
                if mode == 'factory_error':
                    raise ValueError('private factory')
                return None if mode == 'invalid' else event()
            try:
                assert await observer.run(operation, event_from_result=factory) is result
                assert count == 1
                metrics = observer.snapshot()
                key = 'errors' if mode in ('factory_error', 'clock_error') else (
                    'refused' if mode == 'closed' else 'invalid')
                assert metrics[key] == 1 and metrics['queued'] == 0
                assert 'private' not in str(metrics)
            finally:
                assert await worker.aclose()
        asyncio.run(scenario())
        assert calls == []
