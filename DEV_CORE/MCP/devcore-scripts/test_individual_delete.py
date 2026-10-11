"""Explicit individual deletion stays scoped, conditional, audited and non-retrying."""

import asyncio
from contextlib import AsyncExitStack, closing
import json
import os
import sqlite3
import threading

import pytest

from test_individual_context import runtime, live_api, secret_file, session, fake_http, send
from test_individual_cli import call
from test_individual_tasks import payload
from devcore_engine.clients.individual_tasks import IndividualApiClient
from devcore_engine.security.identity import READ, WRITE, issue_credential, revoke_credential, set_membership


DELETE = "devcore_task_delete"
ARGS = {"project": "alpha", "task_id": "T-01", "expected_version": 1}


@pytest.mark.parametrize("access,enabled", [("disabled", True), ("read", True), ("write", False)])
def test_delete_exposure_is_separate_and_closed_before_credentials(tmp_path, monkeypatch, access, enabled):
    client = IndividualApiClient("http://127.0.0.1:1", tmp_path / "unused.json", "alpha",
                                 task_access=access, delete_enabled=enabled)
    def forbidden():
        raise AssertionError("Disabled deletion read a credential")
    monkeypatch.setattr(client, "_authorization", forbidden)
    assert DELETE not in {tool["name"] for tool in client.tools}
    assert client.call(DELETE, ARGS)["code"] == "individual_tool_unavailable"


@pytest.mark.parametrize("value", ["", "yes", "true", "2", " 1"])
def test_unknown_delete_flag_refuses_configuration(tmp_path, monkeypatch, value):
    monkeypatch.setenv("DEVCORE_MCP_API_URL", "http://127.0.0.1:1")
    monkeypatch.setenv("DEVCORE_MCP_PROJECT", "alpha")
    monkeypatch.setenv("DEVCORE_MCP_CREDENTIAL_FILE", str(tmp_path / "unused.json"))
    monkeypatch.setenv("DEVCORE_MCP_TASK_DELETE", value)
    with pytest.raises(ValueError):
        IndividualApiClient.from_environment()


@pytest.mark.parametrize("args", [{}, {"project": "beta"}, {**ARGS, "actor": "mallory"},
                                     {**ARGS, "expected_version": True}, {**ARGS, "task_id": "../task"}])
def test_invalid_delete_arguments_do_not_read_credentials(tmp_path, monkeypatch, args):
    client = IndividualApiClient("http://127.0.0.1:1", tmp_path / "unused.json", "alpha",
                                 task_access="write", delete_enabled=True)
    def forbidden():
        raise AssertionError("Invalid deletion read a credential")
    monkeypatch.setattr(client, "_authorization", forbidden)
    assert client.call(DELETE, args)["code"] == "invalid_arguments"


@pytest.mark.skipif(os.name != "nt", reason="Real NTFS credentials")
def test_real_stdio_delete_requires_opt_in_scope_version_and_records_author(runtime, tmp_path):
    module, _, credentials, identity, local = runtime
    alice = secret_file(tmp_path / "alice.json", credentials["alice"][1])
    async def exercise(origin):
        async with AsyncExitStack() as stack:
            default = await session(stack, tmp_path / "default", "alpha", origin, alice, task_access="write")
            assert DELETE not in {t.name for t in (await default.list_tools()).tools}
            assert payload(await default.call_tool(DELETE, ARGS))["code"] == "individual_tool_unavailable"
            client = await session(stack, tmp_path / "enabled", "alpha", origin, alice, task_access="write", delete_enabled=True)
            assert DELETE in {t.name for t in (await client.list_tools()).tools}
            for name in ("reader", "bob"):
                alice.write_text(json.dumps({"token": credentials[name][1]}))
                refused = await client.call_tool(DELETE, ARGS)
                assert refused.isError and payload(refused)["http_status"] == 403
            alice.write_text(json.dumps({"token": credentials["alice"][1]}))
            with closing(sqlite3.connect(local / "devcore.db")) as conn, conn:
                conn.execute("UPDATE tasks SET title='Changed elsewhere' WHERE project_id='alpha'")
            refused = await client.call_tool(DELETE, ARGS)
            assert refused.isError and payload(refused)["code"] == "stale_task_version"
            receipt = payload(await client.call_tool(DELETE, {**ARGS, "expected_version": 2}))
            assert receipt["acknowledged"] and receipt["refresh_required"] and "version" not in receipt
            assert payload(await client.call_tool("devcore_task_status", {"project": "alpha"}))["tasks"] == []
            refused = await client.call_tool(DELETE, {**ARGS, "expected_version": 2})
            assert refused.isError and payload(refused)["code"] == "task_not_found"
            revoke_credential(identity, credentials["alice"][0])
            assert payload(await client.call_tool(DELETE, ARGS))["http_status"] == 401
    with live_api(module.app) as origin:
        asyncio.run(exercise(origin))
    with closing(sqlite3.connect(local / "devcore.db")) as conn:
        assert conn.execute("SELECT status,version FROM tasks WHERE project_id='alpha'").fetchone() == ("deleted", 3)
        assert conn.execute("SELECT status,version FROM tasks WHERE project_id='beta'").fetchone() == ("in_progress", 1)
        actor, action, details = conn.execute("SELECT actor,action,details FROM audit_log").fetchone()
        assert (actor, action) == ("alice", "task.delete")
        assert json.loads(details)["after"]["version"] == 3 and credentials["alice"][1] not in details
        assert conn.execute("SELECT COUNT(*) FROM bus_events WHERE event_type='TaskDeleted'").fetchone()[0] == 1


@pytest.mark.skipif(os.name != "nt", reason="Real NTFS credentials")
@pytest.mark.parametrize("access,readonly", [("read", "0"), ("write", "1")])
def test_read_only_stdio_closes_delete_even_with_opt_in(runtime, tmp_path, access, readonly):
    module, _, credentials, _, _ = runtime
    private = secret_file(tmp_path / "alice.json", credentials["alice"][1])
    async def exercise(origin):
        async with AsyncExitStack() as stack:
            client = await session(stack, tmp_path, "alpha", origin, private, task_access=access,
                                   readonly=readonly, delete_enabled=True)
            assert DELETE not in {tool.name for tool in (await client.list_tools()).tools}
            private.unlink()
            assert payload(await client.call_tool(DELETE, ARGS))["code"] == "individual_tool_unavailable"
    with live_api(module.app) as origin:
        asyncio.run(exercise(origin))


@pytest.mark.skipif(os.name != "nt", reason="Real NTFS credentials")
def test_delete_racing_completion_has_one_commit_and_one_authenticated_audit(runtime, tmp_path):
    module, _, credentials, identity, local = runtime
    set_membership(identity, "bob", "alpha", "contributor")
    _, token = issue_credential(identity, "bob", ["alpha"], [READ, WRITE])
    alice, bob = secret_file(tmp_path / "alice.json", credentials["alice"][1]), secret_file(tmp_path / "bob.json", token)
    async def exercise(origin):
        a = IndividualApiClient(origin, alice, "alpha", task_access="write", delete_enabled=True)
        b = IndividualApiClient(origin, bob, "alpha", task_access="write")
        results = await asyncio.gather(asyncio.to_thread(a.call, DELETE, ARGS),
                                       asyncio.to_thread(b.call, "devcore_task_done", ARGS))
        assert sum(result.get("acknowledged") is True for result in results) == 1
        loser = next(result for result in results if result.get("success") is False)
        assert loser["code"] in {"stale_task_version", "task_not_found"}
    with live_api(module.app) as origin:
        asyncio.run(exercise(origin))
    with closing(sqlite3.connect(local / "devcore.db")) as conn:
        status, version = conn.execute("SELECT status,version FROM tasks WHERE project_id='alpha'").fetchone()
        assert version == 2 and status in {"done", "deleted"}
        assert conn.execute("SELECT actor,action FROM audit_log").fetchall() == [
            ("alice", "task.delete") if status == "deleted" else ("bob", "task.complete")]
        assert conn.execute("SELECT COUNT(*) FROM bus_events WHERE event_type IN ('TaskDeleted','TaskCompleted')").fetchone()[0] == 1
        assert conn.execute("SELECT status,version FROM tasks WHERE project_id='beta'").fetchone() == ("in_progress", 1)


@pytest.mark.skipif(os.name != "nt", reason="Real NTFS credentials")
def test_old_schema_delete_is_refused_without_migration(runtime, tmp_path):
    module, _, credentials, _, local = runtime
    database = local / "devcore.db"
    with closing(sqlite3.connect(database)) as conn, conn:
        conn.execute("PRAGMA journal_mode=DELETE")
        conn.execute("DROP TRIGGER tasks_increment_version")
        conn.execute("ALTER TABLE tasks DROP COLUMN version")
    before = database.read_bytes()
    private = secret_file(tmp_path / "alice.json", credentials["alice"][1])
    with live_api(module.app) as origin:
        client = IndividualApiClient(origin, private, "alpha", task_access="write", delete_enabled=True)
        result = client.call(DELETE, ARGS)
        assert result["code"] == "task_version_unavailable" and result["http_status"] == 409
    assert database.read_bytes() == before


@pytest.mark.skipif(os.name != "nt", reason="Real NTFS credentials")
@pytest.mark.parametrize("entry", ["source", "engine", "powershell"])
def test_cli_delete_observes_scopes_versions_and_never_selects_a_task(runtime, tmp_path, entry):
    module, _, credentials, _, local = runtime
    private = secret_file(tmp_path / "alice.json", credentials["alice"][1])
    with live_api(module.app) as origin:
        response, result = call(tmp_path, origin, private, "alpha", "delete", entry=entry)
        assert response.returncode == 2 and result["code"] == "invalid_arguments"
        response, result = call(tmp_path, origin, private, "beta", "delete", "--task-id", "T-01", "--expected-version", "1", entry=entry)
        assert response.returncode == 1 and result["http_status"] == 403
        response, receipt = call(tmp_path, origin, private, "alpha", "delete", "--task-id", "T-01", "--expected-version", "1", entry=entry)
        assert response.returncode == 0 and receipt["acknowledged"] and receipt["refresh_required"]
        assert "version" not in receipt
        response, page = call(tmp_path, origin, private, "alpha", "tasks", entry=entry)
        assert response.returncode == 0 and page["tasks"] == []
    with closing(sqlite3.connect(local / "devcore.db")) as conn:
        assert conn.execute("SELECT actor,action FROM audit_log").fetchall() == [("alice", "task.delete")]
        assert conn.execute("SELECT status,version FROM tasks WHERE project_id='beta'").fetchone() == ("in_progress", 1)


@pytest.mark.parametrize("failure", ["disconnect", "bad_success", "server_error", "redirect"])
def test_delete_transport_uses_delete_once_and_treats_uncertainty_explicitly(tmp_path, monkeypatch, failure):
    received = []
    def receive(handler):
        received.append((handler.command, handler.path, json.loads(handler.rfile.read(int(handler.headers["Content-Length"])))))
        if failure != "disconnect":
            send(handler, b'{"detail":"PRIVATE ERROR"}', status={"bad_success": 200, "server_error": 500, "redirect": 307}[failure],
                 **({"Location": "/other"} if failure == "redirect" else {}))
    with fake_http(receive) as origin:
        client = IndividualApiClient(origin, tmp_path / "unused.json", "alpha", task_access="write", delete_enabled=True)
        monkeypatch.setattr(client, "_authorization", lambda: "Bearer synthetic-test-only")
        result = client.call(DELETE, ARGS)
    assert received == [("DELETE", "/api/delete", {"project": "alpha", "id": "T-01", "expected_version": 1})]
    assert result["code"] == "mutation_outcome_unknown" and result["refresh_required"]
    assert result["success"] is False and "PRIVATE ERROR" not in json.dumps(result)


@pytest.mark.skipif(os.name != "nt", reason="Real NTFS credentials")
def test_delete_response_lost_after_commit_is_not_retried(runtime, tmp_path, monkeypatch):
    module, _, credentials, _, local = runtime
    original = module.delete_task
    release = threading.Event()
    def after_commit(*args, **kwargs):
        result = original(*args, **kwargs)
        release.wait(5)
        return result
    monkeypatch.setattr(module, "delete_task", after_commit)
    private = secret_file(tmp_path / "alice.json", credentials["alice"][1])
    with live_api(module.app) as origin:
        client = IndividualApiClient(origin, private, "alpha", task_access="write", delete_enabled=True, timeout=1)
        try:
            result = client.call(DELETE, ARGS)
            assert result["code"] == "mutation_outcome_unknown" and result["refresh_required"]
            assert client.call("devcore_task_status", {"project": "alpha"})["tasks"] == []
        finally:
            release.set()
    with closing(sqlite3.connect(local / "devcore.db")) as conn:
        assert conn.execute("SELECT status,version FROM tasks WHERE project_id='alpha'").fetchone() == ("deleted", 2)
        assert conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM bus_events WHERE event_type='TaskDeleted'").fetchone()[0] == 1


@pytest.mark.skipif(os.name != "nt", reason="Real NTFS credentials")
def test_dependency_and_audit_failure_leave_task_unchanged(runtime, tmp_path):
    module, _, credentials, _, local = runtime
    private = secret_file(tmp_path / "alice.json", credentials["alice"][1])
    with closing(sqlite3.connect(local / "devcore.db")) as conn, conn:
        conn.execute("INSERT INTO tasks(id,project_id,title,status,depends_on) VALUES ('T-02','alpha','Dependent','todo','T-01')")
    with live_api(module.app) as origin:
        client = IndividualApiClient(origin, private, "alpha", task_access="write", delete_enabled=True)
        result = client.call(DELETE, ARGS)
        assert result["http_status"] == 409 and result["code"] == "task_conflict"
        with closing(sqlite3.connect(local / "devcore.db")) as conn, conn:
            assert conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0] == 0
            conn.execute("DELETE FROM tasks WHERE project_id='alpha' AND id='T-02'")
            conn.execute("DROP TABLE audit_log")
        result = client.call(DELETE, ARGS)
        assert result["code"] == "mutation_outcome_unknown" and result["http_status"] == 500
    with closing(sqlite3.connect(local / "devcore.db")) as conn:
        assert conn.execute("SELECT status,version FROM tasks WHERE project_id='alpha'").fetchone() == ("in_progress", 1)
        assert conn.execute("SELECT COUNT(*) FROM bus_events WHERE event_type='TaskDeleted'").fetchone()[0] == 0
