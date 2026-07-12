import sys
from pathlib import Path

from fastapi.testclient import TestClient


API_ROOT = Path(__file__).resolve().parent
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))


def test_correlation_context_normalizes_ids_from_headers() -> None:
    from devcore_api.correlation import CorrelationContext

    context = CorrelationContext.from_headers(
        {
            "X-Trace-Id": " trace-1 ",
            "X-Run-Id": "run-1",
            "X-Task-Id": "T-173",
            "X-Project-Id": "devcore",
        }
    )

    assert context.trace_id == "trace-1"
    assert context.run_id == "run-1"
    assert context.task_id == "T-173"
    assert context.project_id == "devcore"
    assert context.as_span_attributes() == {
        "trace_id": "trace-1",
        "run_id": "run-1",
        "task_id": "T-173",
        "project_id": "devcore",
    }


def test_observability_middleware_propagates_standard_headers() -> None:
    from devcore_api import create_app
    from devcore_api.observability import InMemorySpanRecorder, configure_observability

    recorder = InMemorySpanRecorder()
    app = configure_observability(create_app(), recorder=recorder)
    response = TestClient(app).get(
        "/api/v1/health",
        headers={
            "X-Trace-Id": "trace-173",
            "X-Run-Id": "run-173",
            "X-Task-Id": "T-173",
            "X-Project-Id": "devcore",
        },
    )

    assert response.status_code == 200
    assert response.headers["X-Trace-Id"] == "trace-173"
    assert recorder.spans[-1]["attributes"]["run_id"] == "run-173"
    assert recorder.spans[-1]["attributes"]["task_id"] == "T-173"
    assert recorder.spans[-1]["attributes"]["project_id"] == "devcore"


def test_worker_span_uses_standard_correlation_context() -> None:
    from devcore_api.correlation import CorrelationContext
    from devcore_api.observability import InMemorySpanRecorder
    from devcore_api.worker import Worker, WorkerRun

    class Repository:
        def claim_next_queued(self):
            return WorkerRun(
                id="run-173",
                task_id="T-173",
                status="queued",
                project_id="devcore",
                trace_id="trace-173",
            )

        def transition(self, run_id: str, action: str):
            pass

    recorder = InMemorySpanRecorder()
    Worker(repository=Repository(), handler=lambda run: None, span_recorder=recorder).run_once()

    assert recorder.spans[-1]["attributes"] == CorrelationContext(
        trace_id="trace-173",
        run_id="run-173",
        task_id="T-173",
        project_id="devcore",
    ).as_span_attributes()
