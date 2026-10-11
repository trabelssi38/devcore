"""Real stdio MCP against pinned snapshot HTTP, with disposable state only."""
import asyncio
from contextlib import AsyncExitStack, closing
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
import subprocess
import threading
import time

import pytest

from Scripts import launch_individual_mcp_candidate as launcher
from Scripts.build_individual_bundle import build, verify


@pytest.mark.parametrize("access,audit,delete", [("other", False, False), ("read", False, True), ("disabled", 1, False)])
def test_capability_refusal_precedes_snapshot_or_secret(tmp_path, access, audit, delete):
    with pytest.raises(ValueError):
        launcher.prepare(tmp_path / "absent", "0" * 64, "http://127.0.0.1:12345", tmp_path / "absent.json", "alpha", access, audit, delete)


@pytest.mark.parametrize("origin", ["http://example.com:12345", "http://127.0.0.1", "https://127.0.0.1:12345"])
def test_non_candidate_origin_refused_before_files(tmp_path, origin):
    with pytest.raises(ValueError):
        launcher.prepare(tmp_path, "0" * 64, origin, tmp_path / "secret.json", "alpha")


def test_missing_credential_exits_before_stdio_or_network(tmp_path):
    bundle = tmp_path / "bundle"
    build(Path(__file__).resolve().parents[1], bundle)
    pin = hashlib.sha256((bundle / "manifest.json").read_bytes()).hexdigest()
    local, data = tmp_path / "local", tmp_path / "data"
    result = subprocess.run([sys.executable, "-I", launcher.__file__, "--bundle", str(bundle),
        "--manifest-sha256", pin, "--api-url", "http://127.0.0.1:54321", "--project", "alpha",
        "--credential-file", str(tmp_path / "missing-secret.json")],
        env={**os.environ, "DEVCORE_LOCAL_ROOT": str(local), "DEVCORE_DATA_ROOT": str(data)},
        capture_output=True, timeout=15)
    assert result.returncode == 2 and not result.stdout
    assert json.loads(result.stderr)["code"] == "candidate_mcp_preflight_refused"
    assert not local.exists() and not data.exists()


@pytest.mark.skipif(os.name != "nt", reason="Native NTFS credentials and installed candidate wheel")
def test_real_mcp_snapshot_default_read_write_and_revocation(tmp_path, monkeypatch):
    import uvicorn
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client
    from devcore_engine.db import init_db
    from devcore_engine.security.private_store import initialize_private_store
    from devcore_engine.security.secret_files import protect_reserved_file
    from devcore_engine.security.identity import add_user, set_membership, issue_credential, revoke_credential, READ, WRITE, AUDIT_READ, CONTEXT_READ

    bundle, local, data = tmp_path / "bundle", tmp_path / "local", tmp_path / "data"
    build(Path(__file__).resolve().parents[1], bundle)
    local.mkdir(); data.mkdir()
    identity = local / "Security" / "identity.db"
    identity.parent.mkdir()
    initialize_private_store(identity)
    add_user(identity, "alice")
    set_membership(identity, "alice", "alpha", "owner")
    credential_id, secret = issue_credential(identity, "alice", ["alpha"], [READ, WRITE, AUDIT_READ, CONTEXT_READ])
    credential = tmp_path / "credential.json"
    credential.touch(); protect_reserved_file(credential)
    credential.write_text(json.dumps({"token": secret}), encoding="utf-8")
    repository = tmp_path / "alpha-repository"
    context = repository / "docs/project-context"
    context.mkdir(parents=True)
    card = context / "card.md"
    card.write_text("# Alpha\nObjectif et contraintes durables de la recette.\n", encoding="utf-8")
    def decision(identifier, status, required, replaces):
        return {"id": identifier, "status": status, "required": required,
                "decision": "Utiliser le profil individuel", "rationale": "Isolation",
                "validation": "Fixture", "sources": ["plan.md"], "tags": [], "replaces": replaces}
    (context / "context.json").write_text(json.dumps({"schema_version": 1, "project": "alpha",
        "reviewed_at": "2026-10-04", "card": "card.md", "card_sha256": hashlib.sha256(card.read_bytes()).hexdigest(),
        "decisions": [decision("old", "superseded", False, []), decision("local", "effective", True, ["old"])]}), encoding="utf-8")
    with closing(init_db(local / "devcore.db")) as connection:
        for project in ("alpha", "beta"):
            connection.execute("INSERT INTO projects(id,name,root_path) VALUES (?,?,'.')", (project, project))
            connection.execute("INSERT INTO tasks(id,project_id,title,status) VALUES ('T-01',?,?,'todo')", (project, project))
        connection.commit()
        connection.execute("UPDATE projects SET root_path=? WHERE id='alpha'", (str(repository),))
        connection.commit()
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(local))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(data))
    monkeypatch.setenv("DEVCORE_PLATFORM_ROOT", str(bundle))
    monkeypatch.setenv("DEVCORE_IDENTITY_STORE", str(identity))
    monkeypatch.setenv("DEVCORE_DASHBOARD_AUTH_PROFILE", "individual")
    monkeypatch.setattr(sys, "dont_write_bytecode", True)
    spec = importlib.util.spec_from_file_location("mcp_snapshot_http", bundle / "Scripts/dashboard_api.py")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    sock = socket.socket(); sock.bind(("127.0.0.1", 0)); sock.listen()
    origin = f"http://127.0.0.1:{sock.getsockname()[1]}"
    server = uvicorn.Server(uvicorn.Config(module.app, log_level="error"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    deadline = time.monotonic() + 15
    while not server.started:
        assert time.monotonic() < deadline, "temporary API startup timeout"
        time.sleep(0.05)
    pin = hashlib.sha256((bundle / "manifest.json").read_bytes()).hexdigest()
    mcp_local, mcp_data = tmp_path / "mcp-local", tmp_path / "mcp-data"
    mcp_local.mkdir(); mcp_data.mkdir()

    async def exercise():
        async with AsyncExitStack() as stack:
            async def session(extra):
                environment = {**os.environ, "DEVCORE_LOCAL_ROOT": str(mcp_local), "DEVCORE_DATA_ROOT": str(mcp_data),
                    "DEVCORE_MCP_AUTH_PROFILE": "legacy", "DEVCORE_MCP_TASK_ACCESS": "write",
                    "DEVCORE_MCP_TASK_DELETE": "1", "DEVCORE_MCP_TASK_AUDIT": "1", "DEVCORE_MCP_TASK_TRANSITIONS": "1"}
                params = StdioServerParameters(command=sys.executable, args=["-I", launcher.__file__,
                    "--bundle", str(bundle), "--manifest-sha256", pin, "--api-url", origin,
                    "--credential-file", str(credential), "--project", "alpha", *extra],
                    cwd=str(tmp_path), env=environment)
                read, write = await stack.enter_async_context(stdio_client(params))
                client = await stack.enter_async_context(ClientSession(read, write))
                await client.initialize()
                return client
            default = await session([])
            assert {tool.name for tool in (await default.list_tools()).tools} == {"devcore_project_context"}
            resumed = await default.call_tool("devcore_project_context", {"project": "alpha", "budget_bytes": 2000})
            assert not resumed.isError and len(resumed.content) == 1 and resumed.structuredContent is None
            raw = resumed.content[0].text.encode("utf-8")
            resumed_context = json.loads(raw)
            assert len(raw) <= 2000 and resumed_context["measurement"]["used"] == len(raw)
            assert "# Alpha" in resumed_context["card"] and resumed_context["excluded_superseded"] == ["old"]
            assert [d["id"] for d in resumed_context["decisions"]] == ["local"]
            reader = await session(["--tasks", "read", "--audit"])
            names = {tool.name for tool in (await reader.list_tools()).tools}
            assert names == {"devcore_project_context", "devcore_task_status", "devcore_task_audit"}
            await reader.send_ping()
            page = await reader.call_tool("devcore_task_status", {"project": "alpha"})
            assert not page.isError
            assert (await reader.call_tool("devcore_task_status", {"project": "beta"})).isError
            assert (await reader.call_tool("devcore_task_done", {"project": "alpha", "task_id": "T-01", "expected_version": 1})).isError
            writer = await session(["--tasks", "write", "--transitions"])
            assert {"devcore_task_pause", "devcore_task_resume"} <= {t.name for t in (await writer.list_tools()).tools}
            from devcore_engine.services.tasks import TaskService
            with closing(__import__("sqlite3").connect(local / "devcore.db")) as conn:
                conn.row_factory = __import__("sqlite3").Row
                TaskService(conn).next_task("alpha")
            for tool, version in [("devcore_task_pause", 2), ("devcore_task_resume", 3)]:
                result = await writer.call_tool(tool, {"project": "alpha", "task_id": "T-01", "expected_version": version})
                assert not result.isError and json.loads(result.content[0].text)["refresh_required"]

            assert "devcore_task_delete" not in {t.name for t in (await writer.list_tools()).tools}
            result = await writer.call_tool("devcore_task_done", {"project": "alpha", "task_id": "T-01", "expected_version": 4})
            assert not result.isError
            history = await reader.call_tool("devcore_task_audit", {"project": "alpha"})
            assert not history.isError and history.structuredContent is None and len(history.content) == 1
            event = json.loads(history.content[0].text)["events"][0]
            assert event["actor"] == "alice" and event["after"] == {"status": "done", "version": 5}
            assert [e["action"] for e in json.loads(history.content[0].text)["events"]] == ["task.complete", "task.resume", "task.pause"]
            revoke_credential(identity, credential_id)
            denied = await reader.call_tool("devcore_task_status", {"project": "alpha"})
            assert denied.isError and json.loads(denied.content[0].text)["http_status"] == 401
    try:
        asyncio.run(asyncio.wait_for(exercise(), 45))
    finally:
        server.should_exit = True; thread.join(timeout=10); sock.close()
        assert not thread.is_alive(), "temporary API did not stop"
    assert not list(mcp_local.iterdir()) and not list(mcp_data.iterdir())
    with closing(__import__("sqlite3").connect(local / "devcore.db")) as connection:
        assert connection.execute("SELECT status,version FROM tasks WHERE project_id='beta'").fetchone() == ("todo", 1)
    assert verify(bundle)


@pytest.mark.parametrize("access,value", [("read", True), ("disabled", True), ("write", 1)])
def test_transition_capability_refused_before_files(tmp_path, access, value):
    with pytest.raises(ValueError):
        launcher.prepare(tmp_path/"absent", "0"*64, "http://127.0.0.1:12345", tmp_path/"missing.json", "alpha", access=access, transitions=value)
