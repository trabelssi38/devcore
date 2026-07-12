import sys
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
