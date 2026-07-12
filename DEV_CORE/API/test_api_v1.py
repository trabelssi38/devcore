import sys
from pathlib import Path

from fastapi.testclient import TestClient


API_ROOT = Path(__file__).resolve().parent
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))


def test_api_v1_health_contract():
    from devcore_api import create_app

    client = TestClient(create_app())
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == 1
    assert payload["service"] == "devcore-api"
    assert payload["status"] == "ok"
    assert payload["api_version"] == "v1"
    assert payload["trace_id"]


def test_api_v1_openapi_is_versioned():
    from devcore_api import create_app

    client = TestClient(create_app())
    response = client.get("/api/v1/openapi.json")

    assert response.status_code == 200
    payload = response.json()
    assert payload["info"]["title"] == "DEV_CORE API Gateway"
    assert payload["info"]["version"] == "v1"
    assert "/api/v1/health" in payload["paths"]


def test_api_v1_errors_use_stable_envelope():
    from devcore_api import create_app

    client = TestClient(create_app())
    response = client.get("/api/v1/missing")

    assert response.status_code == 404
    payload = response.json()
    assert payload["schema_version"] == 1
    assert payload["error"]["code"] == "not_found"
    assert payload["error"]["message"]
    assert isinstance(payload["error"]["details"], dict)
    assert payload["trace_id"]
