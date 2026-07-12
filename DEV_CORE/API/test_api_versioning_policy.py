import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[2]
API_ROOT = Path(__file__).resolve().parent
POLICY_PATH = ROOT / "docs" / "API_VERSIONING_POLICY.md"
OPENAPI_PATH = ROOT / "DEV_CORE" / "Schemas" / "openapi-v1.json"

if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))


def test_public_openapi_paths_are_explicitly_versioned() -> None:
    from devcore_api import create_app

    client = TestClient(create_app())
    schema = client.get("/api/v1/openapi.json").json()

    assert schema["info"]["version"] == "v1"
    assert schema["paths"]
    assert all(path.startswith("/api/v1/") for path in schema["paths"])


def test_committed_openapi_matches_runtime_contract_version() -> None:
    from devcore_api import create_app

    runtime_schema = create_app().openapi()
    committed_schema = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))

    assert committed_schema["info"] == runtime_schema["info"]
    assert set(committed_schema["paths"]) == set(runtime_schema["paths"])


def test_api_versioning_policy_is_documented() -> None:
    policy = POLICY_PATH.read_text(encoding="utf-8")

    assert "# API Versioning Policy" in policy
    assert "`/api/v1`" in policy
    assert "breaking change" in policy.lower()
    assert "OpenAPI" in policy
    assert "TypeScript client" in policy
