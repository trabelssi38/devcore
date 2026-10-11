import sys
from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor
import pytest
from pathlib import Path


API_ROOT = Path(__file__).resolve().parent
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))


def test_langfuse_event_uses_standard_correlation_and_usage() -> None:
    from devcore_api.correlation import CorrelationContext
    from devcore_api.llmops import LlmUsage, LangfuseEvent

    event = LangfuseEvent.from_generation(
        name="router.choice",
        model="gpt-test",
        prompt_tokens=10,
        completion_tokens=5,
        cost_usd=0.0123,
        correlation=CorrelationContext(
            trace_id="trace-1",
            run_id="run-1",
            task_id="T-175",
            project_id="devcore",
        ),
    )

    assert event.trace_id == "trace-1"
    assert event.run_id == "run-1"
    assert event.task_id == "T-175"
    assert event.project_id == "devcore"
    assert event.usage == LlmUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15, cost_usd=0.0123)
    assert event.as_langfuse_payload()["usage"]["total"] == 15


def test_llmops_client_buffers_when_langfuse_not_configured(monkeypatch) -> None:
    from devcore_api.correlation import CorrelationContext
    from devcore_api.llmops import LlmOpsClient, LangfuseEvent

    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    client = LlmOpsClient()
    event = LangfuseEvent.from_generation(
        name="generation",
        model="gpt-test",
        prompt_tokens=1,
        completion_tokens=2,
        cost_usd=0.0,
        correlation=CorrelationContext(trace_id="trace-buffered"),
    )

    assert client.capture(event) == "buffered"
    assert client.buffered_events == [event]


def test_llmops_client_can_use_transport_for_langfuse_payload(monkeypatch) -> None:
    from devcore_api.correlation import CorrelationContext
    from devcore_api.llmops import LlmOpsClient, LangfuseEvent

    sent = []
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")
    client = LlmOpsClient(transport=sent.append)
    event = LangfuseEvent.from_generation(
        name="generation",
        model="gpt-test",
        prompt_tokens=1,
        completion_tokens=2,
        cost_usd=0.01,
        correlation=CorrelationContext(trace_id="trace-sent", run_id="run-sent"),
    )

    assert client.capture(event) == "sent"
    assert sent[0]["traceId"] == "trace-sent"
    assert sent[0]["metadata"]["run_id"] == "run-sent"


def event_fixture():
    from devcore_api.correlation import CorrelationContext
    from devcore_api.llmops import LangfuseEvent
    return LangfuseEvent.from_generation(name='generation', model='gpt-test', prompt_tokens=1,
        completion_tokens=2, cost_usd=0.01, correlation=CorrelationContext(trace_id='trace-fixture'))


def test_buffer_caps_count_and_bytes_and_cannot_be_mutated_by_reader(monkeypatch):
    from devcore_api.llmops import LlmOpsClient
    monkeypatch.delenv('LANGFUSE_PUBLIC_KEY', raising=False)
    event = event_fixture()
    client = LlmOpsClient(max_events=2)
    assert [client.capture(event) for _ in range(4)] == ['buffered', 'buffered', 'dropped', 'dropped']
    client.buffered_events.clear()
    assert len(client.buffered_events) == 2 and client.snapshot()['dropped'] == 2
    byte_limited = LlmOpsClient(max_events=100, max_bytes=1024)
    results = [byte_limited.capture(event) for _ in range(20)]
    metrics = byte_limited.snapshot()
    assert metrics['buffered_bytes'] <= 1024 and 0 < metrics['buffered'] < 20
    assert results.count('dropped') == metrics['dropped'] == 20 - metrics['buffered']


@pytest.mark.parametrize('field,value', [('prompt_tokens', True), ('prompt_tokens', -1),
    ('total_tokens', 8), ('cost_usd', float('nan')), ('cost_usd', float('inf'))])
def test_invalid_usage_never_buffered_or_sent(monkeypatch, field, value):
    from devcore_api.llmops import LlmOpsClient
    monkeypatch.setenv('LANGFUSE_PUBLIC_KEY', 'pk-test')
    monkeypatch.setenv('LANGFUSE_SECRET_KEY', 'sk-test')
    client = LlmOpsClient(transport=lambda _: pytest.fail('Invalid event was sent'))
    event = event_fixture()
    event = replace(event, usage=replace(event.usage, **{field: value}))
    assert client.capture(event) == 'invalid'
    assert client.snapshot()['invalid'] == 1 and not client.buffered_events


@pytest.mark.parametrize('field,value', [('name', 'prompt\nsecret'), ('model', 'x' * 129),
    ('project_id', {'secret': 'hidden'})], ids=['newline', 'oversized', 'object'])
def test_invalid_identifiers_refused_without_raw_diagnostic(monkeypatch, field, value):
    from devcore_api.llmops import LlmOpsClient
    monkeypatch.delenv('LANGFUSE_PUBLIC_KEY', raising=False)
    client = LlmOpsClient()
    assert client.capture(replace(event_fixture(), **{field: value})) == 'invalid'
    assert 'secret' not in str(client.snapshot()) and not client.buffered_events


def test_transport_error_is_bounded_and_not_propagated_or_retried(monkeypatch):
    from devcore_api.llmops import LlmOpsClient
    monkeypatch.setenv('LANGFUSE_PUBLIC_KEY', 'pk-test')
    monkeypatch.setenv('LANGFUSE_SECRET_KEY', 'sk-test')
    calls = []
    def fail(payload):
        calls.append(payload)
        raise RuntimeError('private transport detail')
    client = LlmOpsClient(transport=fail, max_events=1)
    assert client.capture(event_fixture()) == 'buffered'
    assert client.capture(event_fixture()) == 'dropped'
    assert len(calls) == 2
    metrics = client.snapshot()
    assert metrics['transport_errors'] == 2 and metrics['sent'] == 0
    assert 'private' not in str(metrics)


def test_concurrent_capture_cannot_overflow_capacity(monkeypatch):
    from devcore_api.llmops import LlmOpsClient
    monkeypatch.delenv('LANGFUSE_PUBLIC_KEY', raising=False)
    client = LlmOpsClient(max_events=8)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(client.capture, [event_fixture()] * 128))
    assert results.count('buffered') == 8 and results.count('dropped') == 120
    assert client.snapshot()['buffered'] == 8 and client.snapshot()['dropped'] == 120
