"""Conditional pause/resume through real API, CLI and MCP, with explicit exposure."""
import asyncio
from contextlib import AsyncExitStack
import json
import os
import sqlite3
import pytest
from test_individual_context import runtime, live_api, secret_file, session
from test_individual_cli import call
from test_individual_tasks import payload
from devcore_engine.clients.individual_tasks import IndividualApiClient
from devcore_engine.clients.individual_audit import audit_page
from devcore_engine.security.identity import revoke_credential

ARGS = {"project": "alpha", "task_id": "T-01", "expected_version": 1}

@pytest.mark.parametrize("access,enabled", [("disabled", True), ("read", True), ("write", False)])
@pytest.mark.parametrize("operation", ["pause", "resume"])
def test_exposure_closed_before_credentials(tmp_path, monkeypatch, access, enabled, operation):
    client = IndividualApiClient("http://127.0.0.1:1", tmp_path/"missing.json", "alpha",
                                 task_access=access, transitions_enabled=enabled)
    monkeypatch.setattr(client, "_authorization", lambda: pytest.fail("Disabled tool read credentials"))
    assert client.call("devcore_task_"+operation, ARGS)["code"] == "individual_tool_unavailable"

@pytest.mark.parametrize("value", ["", "true", "2"])
def test_invalid_activation_refuses_configuration(tmp_path, monkeypatch, value):
    monkeypatch.setenv("DEVCORE_MCP_API_URL", "http://127.0.0.1:1")
    monkeypatch.setenv("DEVCORE_MCP_PROJECT", "alpha")
    monkeypatch.setenv("DEVCORE_MCP_CREDENTIAL_FILE", str(tmp_path/"missing.json"))
    monkeypatch.setenv("DEVCORE_MCP_TASK_TRANSITIONS", value)
    with pytest.raises(ValueError):
        IndividualApiClient.from_environment()

@pytest.mark.parametrize("operation", ["pause", "resume"])
@pytest.mark.parametrize("change", [{"actor": "mallory"}, {"project": "beta"}, {"expected_version": True}])
def test_invalid_transition_arguments_never_read_credentials(tmp_path, monkeypatch, operation, change):
    client = IndividualApiClient("http://127.0.0.1:1", tmp_path/"missing.json", "alpha",
                                 task_access="write", transitions_enabled=True)
    monkeypatch.setattr(client, "_authorization", lambda: pytest.fail("Invalid args read credentials"))
    assert client.call("devcore_task_"+operation, {**ARGS, **change})["code"] == "invalid_arguments"

@pytest.mark.skipif(os.name != "nt", reason="Real NTFS credential files")
def test_cli_pause_stdio_resume_keep_versions_authors_and_revocation(runtime, tmp_path):
    module, _, credentials, identity, local = runtime
    secret = secret_file(tmp_path/"alice.json", credentials["alice"][1])
    (tmp_path/"cli").mkdir()
    async def exercise(origin):
        async with AsyncExitStack() as stack:
            disabled = await session(stack, tmp_path/"disabled", "alpha", origin, secret, task_access="write")
            assert "devcore_task_pause" not in {t.name for t in (await disabled.list_tools()).tools}
            readonly = await session(stack, tmp_path/"readonly", "alpha", origin, secret,
                                     task_access="write", readonly="1", transitions_enabled=True)
            assert "devcore_task_resume" not in {t.name for t in (await readonly.list_tools()).tools}
            mcp = await session(stack, tmp_path/"enabled", "alpha", origin, secret,
                                task_access="write", transitions_enabled=True)
            assert {"devcore_task_pause", "devcore_task_resume"} <= {t.name for t in (await mcp.list_tools()).tools}
            # CLI uses isolated Python without MCP/FastAPI; its local DB is a forbidden fixture.
            result, ack = await asyncio.to_thread(call, tmp_path/"cli", origin, secret, "alpha",
                                                 "pause", "--task-id", "T-01", "--expected-version", "1")
            assert result.returncode == 0 and ack["acknowledged"] and ack["refresh_required"] and "version" not in ack
            refused = payload(await mcp.call_tool("devcore_task_resume", ARGS))
            assert refused["code"] == "stale_task_version"
            ack = payload(await mcp.call_tool("devcore_task_resume", {**ARGS, "expected_version": 2}))
            assert ack["acknowledged"] and ack["refresh_required"] and "version" not in ack
            assert payload(await mcp.call_tool("devcore_task_resume", {**ARGS, "expected_version": 2}))["code"] == "stale_task_version"
            for user in ("reader", "bob"):
                secret.write_text(json.dumps({"token": credentials[user][1]}))
                assert payload(await mcp.call_tool("devcore_task_pause", {**ARGS, "expected_version": 3}))["http_status"] == 403
            secret.write_text(json.dumps({"token": credentials["alice"][1]}))
            revoke_credential(identity, credentials["alice"][0])
            assert payload(await mcp.call_tool("devcore_task_pause", {**ARGS, "expected_version": 3}))["http_status"] == 401
    with live_api(module.app) as origin:
        asyncio.run(exercise(origin))
    with sqlite3.connect(local/"devcore.db") as conn:
        assert conn.execute("SELECT status,version FROM tasks WHERE project_id='alpha'").fetchone() == ("in_progress", 3)
        assert conn.execute("SELECT status,version FROM tasks WHERE project_id='beta'").fetchone() == ("in_progress", 1)
        assert conn.execute("SELECT actor,action FROM audit_log ORDER BY rowid").fetchall() == [("alice", "task.pause"), ("alice", "task.resume")]
