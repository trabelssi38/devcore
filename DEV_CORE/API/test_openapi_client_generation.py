import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EXPORT_SCRIPT = ROOT / "DEV_CORE" / "API" / "export_openapi.py"
OPENAPI_PATH = ROOT / "DEV_CORE" / "Schemas" / "openapi-v1.json"
TS_CLIENT_PATH = ROOT / "DEV_CORE" / "API" / "clients" / "typescript" / "devcore-api-client.ts"


def test_openapi_export_generates_schema_and_typescript_client() -> None:
    result = subprocess.run(
        [sys.executable, str(EXPORT_SCRIPT)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert OPENAPI_PATH.exists()
    assert TS_CLIENT_PATH.exists()

    schema = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))
    assert schema["info"]["title"] == "DEV_CORE API Gateway"
    assert schema["info"]["version"] == "v1"
    assert "/api/v1/health" in schema["paths"]
    assert "/api/v1/contracts" in schema["paths"]
    assert "/api/v1/tasks" in schema["paths"]

    client = TS_CLIENT_PATH.read_text(encoding="utf-8")
    assert "export class DevCoreApiClient" in client
    assert "async health()" in client
    assert "async contracts()" in client
    assert "async tasks(project = \"devcore\")" in client
    assert "X-Trace-Id" in client
    assert "TaskListResponse" in client
