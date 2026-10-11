"""Tests for CLI and MCP routing to the active API instance (Lot L2 Item 395).

Verifies:
1. Equivalent operations via HTTP, CLI, and MCP produce the same state and same errors.
2. In client mode (DEVCORE_CLIENT_MODE=1), direct access to the database is forbidden.
3. Python services remain directly callable in tests and migration scripts.
4. MCP stdio protocol correctly routes to the active API instance.
"""

from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

DEVCORE_DIR = Path(__file__).resolve().parents[1]
if str(DEVCORE_DIR / "API") not in sys.path:
    sys.path.insert(0, str(DEVCORE_DIR / "API"))
if str(DEVCORE_DIR / "MCP" / "devcore-scripts") not in sys.path:
    sys.path.insert(0, str(DEVCORE_DIR / "MCP" / "devcore-scripts"))
if str(DEVCORE_DIR) not in sys.path:
    sys.path.insert(0, str(DEVCORE_DIR))

import pytest
from fastapi.testclient import TestClient

from devcore_api import create_app
from devcore_api.ports import SqliteTaskRepository
from devcore_engine.db import init_db
from devcore_engine.services.tasks import TaskService
from devcore_engine.services.task_mutations import complete_task_usecase


def _setup_test_db(db_path: Path, project: str = "proj_alpha") -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = init_db(db_path)
    conn.execute("INSERT OR IGNORE INTO projects(id, name, root_path) VALUES (?, ?, ?)", (project, project, "."))
    conn.commit()
    conn.close()

    service = TaskService(db_path.parent)
    try:
        service.add_task("First task", mode="coding", project_id=project)
        service.add_task("Second task", mode="reasoning", project_id=project)
        service.add_task("Third task", mode="bulk", project_id=project)
    finally:
        service.conn.close()


@pytest.fixture
def test_env(tmp_path, monkeypatch):
    local_root = tmp_path / "local"
    data_root = tmp_path / "data"
    local_root.mkdir()
    data_root.mkdir()
    db_path = local_root / "devcore.db"
    _setup_test_db(db_path, "proj_alpha")

    manifest = tmp_path / ".devcore" / "project.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({"name": "proj_alpha"}), encoding="utf-8")

    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(local_root))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(data_root))
    monkeypatch.setenv("DEVCORE_SQLITE_DB_PATH", str(db_path))

    return {
        "tmp_path": tmp_path,
        "local_root": local_root,
        "data_root": data_root,
        "db_path": db_path,
    }


def test_python_services_remain_directly_callable(test_env):
    """Python domain services must remain callable directly in tests and migration tools."""
    db_path = test_env["db_path"]
    with closing(sqlite3.connect(str(db_path))) as conn:
        conn.row_factory = sqlite3.Row
        service = TaskService(conn)
        board = service.get_board("proj_alpha")
        assert len(board["tasks"]) == 3
        # Direct mutation without API
        task = service.next_task("proj_alpha")
        assert task is not None
        assert task["id"] == "T-01"
        assert task["status"] == "in_progress"


def test_client_mode_forbids_direct_db_access(test_env, monkeypatch):
    """When DEVCORE_CLIENT_MODE=1, direct client DB access is refused."""
    from services.task_service import open_task_service, open_existing_task_service

    monkeypatch.setenv("DEVCORE_CLIENT_MODE", "1")
    monkeypatch.delenv("DEVCORE_API_URL", raising=False)

    with pytest.raises(PermissionError, match="Direct client access to the database is forbidden in client mode"):
        open_task_service()

    with pytest.raises(PermissionError, match="Direct client access to the database is forbidden in client mode"):
        open_existing_task_service(read_only=True)

    # CLI also refuses when in client mode without API URL
    result = subprocess.run(
        [sys.executable, "-m", "devcore_engine.cli", "task", "board", "--project", "proj_alpha"],
        env={**os.environ, "DEVCORE_CLIENT_MODE": "1", "PYTHONPATH": str(Path(__file__).resolve().parents[1])},
        capture_output=True,
        text=True,
        cwd=str(test_env["tmp_path"]),
    )
    assert result.returncode == 2
    assert "Direct database access is forbidden in client mode" in result.stderr


def test_api_mutations_and_facades(test_env):
    """API Gateway correctly serves mutation endpoints and legacy facades with conflict detection."""
    db_path = test_env["db_path"]
    repo = SqliteTaskRepository(db_path)
    app = create_app(task_repository=repo)
    client = TestClient(app)

    # 1. Activate next task
    res_next = client.post("/api/v1/tasks/next", json={"project": "proj_alpha"})
    assert res_next.status_code == 200
    task_next = res_next.json()["task"]
    assert task_next["id"] == "T-01"
    assert task_next["version"] == 2  # Transition to in_progress increments version

    # 2. Complete task with stale version -> 409
    res_stale = client.post("/api/done", json={"project": "proj_alpha", "id": "T-01", "expected_version": 1})
    assert res_stale.status_code == 409
    assert res_stale.json()["code"] == "stale_task_version"
    assert res_stale.json()["detail"]["code"] == "stale_task_version"

    # 3. Complete task with valid version -> 200
    res_done = client.post("/api/done", json={"project": "proj_alpha", "id": "T-01", "expected_version": 2})
    assert res_done.status_code == 200
    assert res_done.json()["status"] == "success"

    # 4. Pause and resume T-02
    client.post("/api/v1/tasks/next", json={"project": "proj_alpha"})  # Activates T-02 (v=2)
    res_pause = client.post("/api/pause", json={"project": "proj_alpha", "id": "T-02", "expected_version": 2})
    assert res_pause.status_code == 200

    res_resume = client.post("/api/resume", json={"project": "proj_alpha", "id": "T-02", "expected_version": 3})
    assert res_resume.status_code == 200

    # 5. Delete T-03
    res_del = client.request(
        "DELETE",
        "/api/delete",
        content=json.dumps({"project": "proj_alpha", "id": "T-03", "expected_version": 1}),
        headers={"Content-Type": "application/json"},
    )
    assert res_del.status_code == 200


def test_operation_equivalence_http_cli_mcp(test_env, monkeypatch):
    """An equivalent operation via HTTP, CLI, or MCP produces the same state and same error."""
    import socket
    import threading
    import uvicorn

    db_path = test_env["db_path"]
    repo = SqliteTaskRepository(db_path)
    app = create_app(task_repository=repo)

    # Start a live background uvicorn server on loopback
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen(5)
    port = sock.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"

    server = uvicorn.Server(uvicorn.Config(app, log_level="critical", access_log=False))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()

    try:
        deadline = time.monotonic() + 5
        while not server.started and time.monotonic() < deadline:
            time.sleep(0.02)
        assert server.started, "Uvicorn server failed to start"

        monkeypatch.setenv("DEVCORE_API_URL", origin)
        cli_env = {
            **os.environ,
            "DEVCORE_API_URL": origin,
            "PYTHONPATH": str(Path(__file__).resolve().parents[1]),
        }

        # --- A. CLI Operation routed via API ---
        # Next task via CLI
        res_cli_next = subprocess.run(
            [sys.executable, "-m", "devcore_engine.cli", "task", "next", "--project", "proj_alpha", "--json"],
            env=cli_env, capture_output=True, text=True, cwd=str(test_env["tmp_path"]),
        )
        assert res_cli_next.returncode == 0, res_cli_next.stderr
        task_info = json.loads(res_cli_next.stdout)
        assert task_info["id"] == "T-01"
        assert task_info["version"] == 2

        # Stale completion via CLI -> exit 2 with stale task version
        res_cli_stale = subprocess.run(
            [sys.executable, "-m", "devcore_engine.cli", "task", "complete", "T-01", "--project", "proj_alpha", "--expected-version", "1"],
            env=cli_env, capture_output=True, text=True, cwd=str(test_env["tmp_path"]),
        )
        assert res_cli_stale.returncode == 2
        assert "stale task version" in res_cli_stale.stderr

        # Successful completion via CLI
        res_cli_done = subprocess.run(
            [sys.executable, "-m", "devcore_engine.cli", "task", "complete", "T-01", "--project", "proj_alpha", "--expected-version", "2"],
            env=cli_env, capture_output=True, text=True, cwd=str(test_env["tmp_path"]),
        )
        assert res_cli_done.returncode == 0
        assert "Completed task: [T-01]" in res_cli_done.stdout

        # Verify DB state updated through the API
        with closing(sqlite3.connect(str(db_path))) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT status, version FROM tasks WHERE id='T-01'").fetchone()
            assert row["status"] == "done"
            assert row["version"] == 3

        # --- B. MCP Operation routed via API ---
        from services.task_service import get_active_task_status, complete_active_task

        # Advance T-02 via HTTP so it is active
        res_h_next = subprocess.run(
            [sys.executable, "-m", "devcore_engine.cli", "task", "next", "--project", "proj_alpha", "--json"],
            env=cli_env, capture_output=True, text=True, cwd=str(test_env["tmp_path"]),
        )
        assert res_h_next.returncode == 0

        # Check MCP status routed via API
        mcp_status = get_active_task_status("proj_alpha")
        assert mcp_status["success"] is True
        assert "Active task: T-02" in mcp_status["stdout"]

        # MCP stale completion -> produces error code stale_task_version
        mcp_stale = complete_active_task("proj_alpha", task_id="T-02", expected_version=1)
        assert mcp_stale["success"] is False
        assert mcp_stale["code"] == "stale_task_version"

        # MCP successful completion
        mcp_done = complete_active_task("proj_alpha", task_id="T-02", expected_version=2)
        assert mcp_done["success"] is True
        assert "marked as DONE" in mcp_done["stdout"]

        # Verify DB state
        with closing(sqlite3.connect(str(db_path))) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT status, version FROM tasks WHERE id='T-02'").fetchone()
            assert row["status"] == "done"
            assert row["version"] == 3

    finally:
        server.should_exit = True
        thread.join(timeout=3)
        sock.close()


def test_dc_cli_next_task_routes_via_api(test_env):
    """dc.py next task respects client mode and routes to active API instance."""
    import socket
    import threading
    import uvicorn

    dc_script = DEVCORE_DIR / "Scripts" / "dc.py"

    # 1. Client mode without API -> exit 2
    res_refused = subprocess.run(
        [sys.executable, str(dc_script), "next task", "--project", "proj_alpha"],
        env={**os.environ, "DEVCORE_CLIENT_MODE": "1", "PYTHONPATH": str(DEVCORE_DIR)},
        capture_output=True,
        text=True,
        cwd=str(test_env["tmp_path"]),
    )
    assert res_refused.returncode == 2
    assert "Direct database access is forbidden in client mode" in res_refused.stderr

    # 2. With live API server running -> routes via API and succeeds
    db_path = test_env["db_path"]
    repo = SqliteTaskRepository(db_path)
    app = create_app(task_repository=repo)

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen(5)
    origin = f"http://127.0.0.1:{sock.getsockname()[1]}"

    server = uvicorn.Server(uvicorn.Config(app, log_level="critical", access_log=False))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()

    try:
        deadline = time.monotonic() + 5
        while not server.started and time.monotonic() < deadline:
            time.sleep(0.02)
        assert server.started

        res_ok = subprocess.run(
            [sys.executable, str(dc_script), "next task", "--project", "proj_alpha"],
            env={**os.environ, "DEVCORE_API_URL": origin, "PYTHONPATH": str(DEVCORE_DIR)},
            capture_output=True,
            text=True,
            cwd=str(test_env["tmp_path"]),
        )
        assert res_ok.returncode == 0
        assert "Active task: [T-01]" in res_ok.stdout
    finally:
        server.should_exit = True
        thread.join(timeout=3)
        sock.close()


def test_mcp_stdio_subprocess_routes_via_api(test_env):
    """MCP server in a real stdio subprocess routes task tools to active API instance."""
    import asyncio
    import socket
    import threading
    import uvicorn
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    db_path = test_env["db_path"]
    repo = SqliteTaskRepository(db_path)
    app = create_app(task_repository=repo)

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen(5)
    origin = f"http://127.0.0.1:{sock.getsockname()[1]}"

    server = uvicorn.Server(uvicorn.Config(app, log_level="critical", access_log=False))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()

    async def run_mcp_client():
        server_script = DEVCORE_DIR / "MCP" / "devcore-scripts" / "server.py"
        params = StdioServerParameters(
            command=sys.executable,
            args=[str(server_script)],
            cwd=str(server_script.parent),
            env={
                **os.environ,
                "DEVCORE_LOCAL_ROOT": str(test_env["local_root"]),
                "DEVCORE_DATA_ROOT": str(test_env["data_root"]),
                "DEVCORE_API_URL": origin,
                "DEVCORE_MCP_AUTH_PROFILE": "legacy",
            },
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                init_res = await session.initialize()
                assert init_res.serverInfo.name == "devcore-scripts"
                tools_res = await session.list_tools()
                tool_names = {t.name for t in tools_res.tools}
                assert "devcore_task_status" in tool_names
                assert "devcore_task_done" in tool_names

                # Call tool devcore_task_status
                call_res = await session.call_tool("devcore_task_status", {"project": "proj_alpha"})
                assert not call_res.isError
                assert len(call_res.content) == 1
                text = call_res.content[0].text
                data = json.loads(text)
                assert data["success"] is True
                assert "Tasks progress:" in data["stdout"]

    try:
        deadline = time.monotonic() + 5
        while not server.started and time.monotonic() < deadline:
            time.sleep(0.02)
        assert server.started
        asyncio.run(run_mcp_client())
    finally:
        server.should_exit = True
        thread.join(timeout=3)
        sock.close()
