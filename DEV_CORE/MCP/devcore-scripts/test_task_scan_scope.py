import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
MCP_ROOT = REPO_ROOT / "DEV_CORE" / "MCP" / "devcore-scripts"


def test_mcp_scan_requires_and_forwards_explicit_project(tmp_path):
    env = os.environ.copy()
    env.update(
        DEVCORE_PLATFORM_ROOT=str(REPO_ROOT / "DEV_CORE"),
        DEVCORE_DATA_ROOT=str(tmp_path / "data"),
        DEVCORE_LOCAL_ROOT=str(tmp_path / "local"),
    )
    snippet = r'''
import sys
sys.path.insert(0, sys.argv[1])
from handlers import tool_handlers as handlers

captured = []
handlers.run_python_script = lambda path, args=None: captured.append((path, args)) or {"success": True}
missing = handlers.handle_task_scan({})
assert missing["success"] is False and not captured
scanned = handlers.handle_task_scan({"project": "alpha"})
assert scanned["success"] is True
assert captured[0][1] == ["--project", "alpha"]
schema = next(tool for tool in handlers.TOOLS if tool["name"] == "devcore_task_scan")["input_schema"]
assert schema["required"] == ["project"]
assert schema["additionalProperties"] is False
'''
    result = subprocess.run(
        [sys.executable, "-c", snippet, str(MCP_ROOT)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
