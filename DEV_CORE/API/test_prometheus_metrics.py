import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[2]
API_ROOT = Path(__file__).resolve().parent
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))


def test_metrics_endpoint_exposes_prometheus_text() -> None:
    from devcore_api import create_app
    from devcore_api.metrics import InMemoryMetricsRegistry, configure_metrics

    registry = InMemoryMetricsRegistry()
    app = configure_metrics(create_app(), registry=registry)
    client = TestClient(app)

    client.get("/api/v1/health")
    response = client.get("/api/v1/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "devcore_http_requests_total" in response.text
    assert 'path="/api/v1/health"' in response.text


def test_grafana_dashboard_is_versioned_json() -> None:
    dashboard_path = ROOT / "DEV_CORE" / "Metrics" / "grafana" / "devcore-api-worker.json"
    dashboard = json.loads(dashboard_path.read_text(encoding="utf-8"))

    assert dashboard["title"] == "DEV_CORE API and Worker"
    panels = {panel["title"] for panel in dashboard["panels"]}
    assert "HTTP Requests" in panels
    assert "Worker Runs" in panels
