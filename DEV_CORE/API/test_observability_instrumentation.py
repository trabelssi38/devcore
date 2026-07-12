import sys
from pathlib import Path

from fastapi.testclient import TestClient


API_ROOT = Path(__file__).resolve().parent
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))


def test_api_adds_trace_id_header_and_span_attributes() -> None:
    from devcore_api import create_app
    from devcore_api.observability import InMemorySpanRecorder, configure_observability

    recorder = InMemorySpanRecorder()
    app = configure_observability(create_app(), recorder=recorder)

    response = TestClient(app).get("/api/v1/health", headers={"X-Trace-Id": "trace-test"})

    assert response.status_code == 200
    assert response.headers["X-Trace-Id"] == "trace-test"
    assert recorder.spans[-1]["name"] == "http.request"
    assert recorder.spans[-1]["attributes"]["trace_id"] == "trace-test"
    assert recorder.spans[-1]["attributes"]["path"] == "/api/v1/health"


def test_worker_records_run_span() -> None:
    from devcore_api.observability import InMemorySpanRecorder
    from devcore_api.worker import Worker, WorkerRun

    class Repository:
        def __init__(self):
            self.transitions = []

        def claim_next_queued(self):
            return WorkerRun(id="run-otel", task_id="T-172", status="queued")

        def transition(self, run_id: str, action: str):
            self.transitions.append((run_id, action))

    recorder = InMemorySpanRecorder()
    result = Worker(repository=Repository(), handler=lambda run: None, span_recorder=recorder).run_once()

    assert result == "succeeded"
    assert recorder.spans[-1]["name"] == "worker.run"
    assert recorder.spans[-1]["attributes"]["run_id"] == "run-otel"
    assert recorder.spans[-1]["attributes"]["task_id"] == "T-172"
