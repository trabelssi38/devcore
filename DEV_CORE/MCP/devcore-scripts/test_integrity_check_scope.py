import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
MCP_ROOT = REPO_ROOT / "DEV_CORE" / "MCP" / "devcore-scripts"


def test_health_check_requires_and_forwards_project_and_server_repo_root(tmp_path):
    env = os.environ.copy()
    env.update(
        DEVCORE_PLATFORM_ROOT=str(REPO_ROOT / "DEV_CORE"),
        DEVCORE_DATA_ROOT=str(tmp_path / "data"),
        DEVCORE_LOCAL_ROOT=str(tmp_path / "local"),
        DEVCORE_MCP_REPO_ROOT=str(tmp_path),
    )
    snippet = r'''
import os
import sys
sys.path.insert(0, sys.argv[1])
from handlers import tool_handlers as handlers

captured = []
handlers.run_python_script = lambda path, args=None: captured.append((path, args)) or {"success": True}
assert handlers.handle_health_check({})["success"] is False and not captured
assert handlers.handle_health_check({"project": "../beta"})["success"] is False and not captured
assert handlers.handle_health_check({"project": "alpha"})["success"] is True
assert captured[0][1] == ["--project", "alpha", "--repo", os.path.realpath(os.environ["DEVCORE_MCP_REPO_ROOT"])]
schema = next(tool for tool in handlers.TOOLS if tool["name"] == "devcore_health_check")["input_schema"]
assert schema["required"] == ["project"]
assert schema["additionalProperties"] is False
os.environ.pop("DEVCORE_MCP_REPO_ROOT")
assert handlers.handle_health_check({"project": "alpha"})["success"] is False
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
