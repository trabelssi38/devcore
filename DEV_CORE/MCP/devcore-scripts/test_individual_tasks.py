"""Individual MCP tasks use API rights, conditional writes and authenticated audit."""

import asyncio
from contextlib import AsyncExitStack, closing
import json
import os
import sqlite3
import threading

import pytest

from test_individual_context import runtime, live_api, secret_file, session, fake_http, send
from devcore_engine.security.identity import issue_credential, revoke_credential, set_membership, READ, WRITE
from services.individual_tasks import IndividualApiClient


def payload(result):
    assert len(result.content) == 1 and result.structuredContent is None
    return json.loads(result.content[0].text)


@pytest.mark.skipif(os.name != "nt", reason="Real NTFS credentials")
def test_stdio_tasks_versions_acl_and_authenticated_audit(runtime, tmp_path):
    module, _, credentials, identity, local = runtime
    alice = secret_file(tmp_path / "alice.json", credentials["alice"][1])
    bob = secret_file(tmp_path / "bob.json", credentials["bob"][1])
    with closing(sqlite3.connect(local / "devcore.db")) as conn, conn:
        conn.execute("INSERT INTO tasks(id,project_id,title,status) VALUES ('T-02','alpha','Next alpha','todo')")

    async def exercise(origin):
        async with AsyncExitStack() as stack:
            alpha = await session(stack, tmp_path, "alpha", origin, alice, task_access="write")
            beta = await session(stack, tmp_path, "beta", origin, bob, task_access="write")
            assert {tool.name for tool in (await alpha.list_tools()).tools} == {
                "devcore_project_context", "devcore_task_status", "devcore_task_done"}
            # Task-only credentials don't gain context access.
            refused = await alpha.call_tool("devcore_project_context", {"project": "alpha"})
            assert refused.isError and payload(refused)["http_status"] == 403
            page = payload(await alpha.call_tool("devcore_task_status", {"project": "alpha", "limit": 1}))
            assert page["success"] and page["page_may_have_more"] and page["offset"] == 0
            assert len(page["tasks"]) == 1 and page["tasks"][0]["project"] == "alpha"
            second = payload(await alpha.call_tool("devcore_task_status", {"project": "alpha", "limit": 1, "offset": 1}))
            assert len(second["tasks"]) == 1 and second["tasks"][0]["id"] != page["tasks"][0]["id"]
            assert payload(await alpha.call_tool("devcore_task_status", {"project": "alpha", "offset": 2}))["tasks"] == []
            for args in ({"project": "beta"}, {"project": "alpha", "limit": 0},
                         {"project": "alpha", "offset": True}, {"project": "alpha", "token": "forged"}):
                denied = await alpha.call_tool("devcore_task_status", args)
                assert denied.isError and payload(denied)["code"] == "invalid_arguments"
            for args in ({"project": "alpha"}, {"project": "alpha", "task_id": "T-01"},
                         {"project": "alpha", "task_id": "T-01", "expected_version": True},
                         {"project": "alpha", "task_id": "T-01", "expected_version": 1, "actor": "mallory"}):
                denied = await alpha.call_tool("devcore_task_done", args)
                assert denied.isError and payload(denied)["code"] == "invalid_arguments"
            # Foreign valid credential against alpha reaches the API and is refused.
            alice.write_text(json.dumps({"token": credentials["bob"][1]}))
            denied = await alpha.call_tool("devcore_task_status", {"project": "alpha"})
            assert denied.isError and payload(denied)["http_status"] == 403
            alice.write_text(json.dumps({"token": credentials["reader"][1]}))
            assert not (await alpha.call_tool("devcore_task_status", {"project": "alpha"})).isError
            denied = await alpha.call_tool("devcore_task_done", {"project": "alpha", "task_id": "T-01", "expected_version": 1})
            assert denied.isError and payload(denied)["http_status"] == 403
            alice.write_text(json.dumps({"token": credentials["alice"][1]}))
            with closing(sqlite3.connect(local / "devcore.db")) as conn, conn:
                conn.execute("UPDATE tasks SET title='Changed elsewhere' WHERE project_id='alpha' AND id='T-01'")
            denied = await alpha.call_tool("devcore_task_done", {"project": "alpha", "task_id": "T-01", "expected_version": 1})
            assert denied.isError and payload(denied)["code"] == "stale_task_version"
            assert payload(denied)["http_status"] == 409
            with closing(sqlite3.connect(local / "devcore.db")) as conn:
                assert conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0] == 0
            a, b = await asyncio.gather(
                alpha.call_tool("devcore_task_done", {"project": "alpha", "task_id": "t-01", "expected_version": 2}),
                beta.call_tool("devcore_task_done", {"project": "beta", "task_id": "T-01", "expected_version": 1}))
            for result in (a, b):
                receipt = payload(result)
                assert not result.isError and receipt["acknowledged"] and receipt["refresh_required"]
                assert "version" not in receipt and "status" not in receipt
            observed = payload(await alpha.call_tool("devcore_task_status", {"project": "alpha"}))
            assert next(t for t in observed["tasks"] if t["id"] == "T-01")["version"] == 3
            repeated = await alpha.call_tool("devcore_task_done", {"project": "alpha", "task_id": "T-01", "expected_version": 2})
            assert repeated.isError and payload(repeated)["code"] == "stale_task_version"
            missing = await alpha.call_tool("devcore_task_done", {"project": "alpha", "task_id": "T-404", "expected_version": 1})
            assert missing.isError and payload(missing)["code"] == "task_not_found"
            set_membership(identity, "alice", "alpha", "reader")
            denied = await alpha.call_tool("devcore_task_done", {"project": "alpha", "task_id": "T-02", "expected_version": 1})
            assert denied.isError and payload(denied)["http_status"] == 403
            revoke_credential(identity, credentials["alice"][0])
            denied = await alpha.call_tool("devcore_task_status", {"project": "alpha"})
            assert denied.isError and payload(denied)["http_status"] == 401
            assert not (await beta.call_tool("devcore_task_status", {"project": "beta"})).isError

    with live_api(module.app) as origin:
        asyncio.run(exercise(origin))
    with closing(sqlite3.connect(local / "devcore.db")) as conn:
        assert conn.execute("SELECT status,version FROM tasks WHERE project_id='alpha' AND id='T-01'").fetchone() == ("done", 3)
        assert conn.execute("SELECT status,version FROM tasks WHERE project_id='beta' AND id='T-01'").fetchone() == ("done", 2)
        assert conn.execute("SELECT status,version FROM tasks WHERE project_id='alpha' AND id='T-02'").fetchone() == ("todo", 1)
        rows = conn.execute("SELECT project_id,actor,action,entity_id,details FROM audit_log ORDER BY project_id").fetchall()
        assert [(r[0], r[1], r[2], r[3]) for r in rows] == [
            ("alpha", "alice", "task.complete", "T-01"), ("beta", "bob", "task.complete", "T-01")]
        assert {json.loads(r[4])["after"]["version"] for r in rows} == {2, 3}
        assert len({json.loads(r[4])["trace_id"] for r in rows}) == 2
    for project in ("alpha", "beta"):
        root = tmp_path / ("client-" + project)
        assert {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()} == {"local/devcore.db"}
        assert (root / "local/devcore.db").read_bytes() == b"NO CLIENT DATABASE ACCESS"


@pytest.mark.skipif(os.name != "nt", reason="Real NTFS credentials")
@pytest.mark.parametrize("access,readonly", [("read", "0"), ("write", "1")])
def test_read_only_profile_refuses_writes_before_credentials(runtime, tmp_path, access, readonly):
    module, _, credentials, _, local = runtime
    alice = secret_file(tmp_path / "alice.json", credentials["alice"][1])
    async def exercise(origin):
        async with AsyncExitStack() as stack:
            client = await session(stack, tmp_path, "alpha", origin, alice, task_access=access, readonly=readonly)
            assert {tool.name for tool in (await client.list_tools()).tools} == {"devcore_project_context", "devcore_task_status"}
            alice.unlink()
            denied = await client.call_tool("devcore_task_done", {"project": "alpha", "task_id": "T-01", "expected_version": 1})
            assert denied.isError and payload(denied)["code"] == "individual_tool_unavailable"
    with live_api(module.app) as origin:
        asyncio.run(exercise(origin))
    with closing(sqlite3.connect(local / "devcore.db")) as conn:
        assert conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0] == 0


@pytest.mark.skipif(os.name != "nt", reason="Real NTFS credentials")
def test_concurrent_same_task_has_one_acknowledgement_and_one_conflict(runtime, tmp_path):
    module, _, credentials, identity, local = runtime
    set_membership(identity, "bob", "alpha", "contributor")
    _, bob_token = issue_credential(identity, "bob", ["alpha"], [READ, WRITE])
    alice = secret_file(tmp_path / "alice.json", credentials["alice"][1])
    bob = secret_file(tmp_path / "bob.json", bob_token)
    async def exercise(origin):
        async with AsyncExitStack() as stack:
            a = await session(stack, tmp_path / "first", "alpha", origin, alice, task_access="write")
            b = await session(stack, tmp_path / "second", "alpha", origin, bob, task_access="write")
            responses = await asyncio.gather(*[client.call_tool("devcore_task_done",
                {"project": "alpha", "task_id": "T-01", "expected_version": 1}) for client in (a, b)])
            assert sum(not response.isError for response in responses) == 1
            conflict = next(response for response in responses if response.isError)
            assert payload(conflict)["code"] == "stale_task_version"
    with live_api(module.app) as origin:
        asyncio.run(exercise(origin))
    with closing(sqlite3.connect(local / "devcore.db")) as conn:
        assert conn.execute("SELECT status,version FROM tasks WHERE project_id='alpha'").fetchone() == ("done", 2)
        assert conn.execute("SELECT status,version FROM tasks WHERE project_id='beta'").fetchone() == ("in_progress", 1)
        assert conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM bus_events WHERE event_type='TaskCompleted'").fetchone()[0] == 1


@pytest.mark.skipif(os.name != "nt", reason="Real NTFS credentials")
def test_old_task_schema_can_be_read_but_is_not_migrated_for_completion(runtime, tmp_path):
    module, _, credentials, _, local = runtime
    database = local / "devcore.db"
    with closing(sqlite3.connect(database)) as conn, conn:
        conn.execute("PRAGMA journal_mode=DELETE")
        conn.execute("DROP TRIGGER tasks_increment_version")
        conn.execute("ALTER TABLE tasks DROP COLUMN version")
    before = database.read_bytes()
    alice = secret_file(tmp_path / "alice.json", credentials["alice"][1])
    async def exercise(origin):
        async with AsyncExitStack() as stack:
            client = await session(stack, tmp_path, "alpha", origin, alice, task_access="write")
            result = await client.call_tool("devcore_task_status", {"project": "alpha"})
            assert not result.isError and payload(result)["tasks"][0]["version"] is None
            denied = await client.call_tool("devcore_task_done", {"project": "alpha", "task_id": "T-01", "expected_version": 1})
            assert denied.isError and payload(denied)["code"] == "task_version_unavailable"
    with live_api(module.app) as origin:
        asyncio.run(exercise(origin))
    assert database.read_bytes() == before


@pytest.mark.parametrize("args", [{"project": "beta"}, {}, {"project": "alpha", "task_id": "../task", "expected_version": 1},
    {"project": "alpha", "task_id": "T-01", "expected_version": 0},
    {"project": "alpha", "task_id": "T-01", "expected_version": 2**63},
    {"project": "alpha", "task_id": "T-01", "expected_version": 1, "user_id": "mallory"}])
def test_invalid_task_arguments_never_read_credentials(tmp_path, monkeypatch, args):
    client = IndividualApiClient("http://127.0.0.1:1", tmp_path / "unused.json", "alpha", task_access="write")
    def forbidden():
        raise AssertionError("Invalid arguments read a secret")
    monkeypatch.setattr(client, "_authorization", forbidden)
    assert client.call("devcore_task_done", args)["code"] == "invalid_arguments"


@pytest.mark.parametrize("damage", ["foreign", "duplicate", "oversize", "invalid_version", "secret_field"])
def test_task_page_rejects_foreign_or_invalid_rows_and_discards_extra_fields(tmp_path, monkeypatch, damage):
    rows = [{"id": "T-01", "project": "alpha", "title": "Alpha", "status": "in_progress", "version": 1}]
    if damage == "foreign": rows.append({**rows[0], "id": "T-02", "project": "beta", "title": "FOREIGN SECRET"})
    if damage == "duplicate": rows.append(rows[0].copy())
    if damage == "oversize": rows[0]["title"] = "X" * 131073
    if damage == "invalid_version": rows[0]["version"] = True
    if damage == "secret_field": rows[0]["internal_path"] = "FOREIGN SECRET PATH"
    with fake_http(lambda handler: send(handler, json.dumps(rows).encode())) as origin:
        client = IndividualApiClient(origin, tmp_path / "unused.json", "alpha", task_access="read")
        monkeypatch.setattr(client, "_authorization", lambda: "Bearer synthetic-test-only")
        result = client.call("devcore_task_status", {"project": "alpha"})
    if damage == "secret_field":
        assert result["success"] and "internal_path" not in result["tasks"][0]
    else:
        assert result["code"] == "task_api_unavailable" and "tasks" not in result
    assert "FOREIGN SECRET" not in json.dumps(result)


@pytest.mark.parametrize("failure", ["disconnect", "bad_success", "server_error", "redirect"])
def test_uncertain_mutation_is_not_retried_or_reported_as_success(tmp_path, monkeypatch, failure):
    received = []
    def receive(handler):
        body = handler.rfile.read(int(handler.headers["Content-Length"]))
        received.append(json.loads(body))
        if failure == "disconnect":
            return
        send(handler, b'{"detail":"PRIVATE ERROR"}', status={"bad_success": 200, "server_error": 500, "redirect": 307}[failure],
             **({"Location": "/other"} if failure == "redirect" else {}))
    with fake_http(receive) as origin:
        client = IndividualApiClient(origin, tmp_path / "unused.json", "alpha", task_access="write")
        monkeypatch.setattr(client, "_authorization", lambda: "Bearer synthetic-test-only")
        result = client.call("devcore_task_done", {"project": "alpha", "task_id": "T-01", "expected_version": 1})
    assert received == [{"project": "alpha", "id": "T-01", "expected_version": 1}]
    assert result["code"] == "mutation_outcome_unknown" and result["refresh_required"]
    assert result["success"] is False and "PRIVATE ERROR" not in json.dumps(result)


@pytest.mark.skipif(os.name != "nt", reason="Real NTFS credentials")
def test_committed_mutation_with_lost_response_requires_read_not_retry(runtime, tmp_path, monkeypatch):
    module, _, credentials, _, local = runtime
    original = module.complete_task
    entered, release = threading.Event(), threading.Event()
    def committed_but_slow(*args, **kwargs):
        result = original(*args, **kwargs)
        entered.set()
        release.wait(5)
        return result
    monkeypatch.setattr(module, "complete_task", committed_but_slow)
    alice = secret_file(tmp_path / "alice.json", credentials["alice"][1])
    with live_api(module.app) as origin:
        client = IndividualApiClient(origin, alice, "alpha", task_access="write", timeout=1)
        try:
            result = client.call("devcore_task_done", {"project": "alpha", "task_id": "T-01", "expected_version": 1})
            assert entered.is_set() and result["code"] == "mutation_outcome_unknown"
            observed = client.call("devcore_task_status", {"project": "alpha"})
            assert observed["tasks"][0]["status"] == "done" and observed["tasks"][0]["version"] == 2
        finally:
            release.set()
    with closing(sqlite3.connect(local / "devcore.db")) as conn:
        assert conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM bus_events WHERE event_type='TaskCompleted'").fetchone()[0] == 1
