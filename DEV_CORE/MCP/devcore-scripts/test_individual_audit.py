"""CLI and real MCP audit admission through a temporary HTTP API."""

import asyncio
from contextlib import AsyncExitStack
import copy
import json
import os
import threading
from uuid import uuid4

import pytest

from test_individual_context import runtime, live_api, secret_file, session, fake_http, send
from test_individual_cli import call as cli_call
from test_individual_tasks import payload
from devcore_engine.clients.individual_tasks import IndividualApiClient
from devcore_engine.clients.individual_audit import TASK_AUDIT_TOOL, MAX_AUDIT_RESPONSE_BYTES
from devcore_engine.security.identity import AUDIT_READ, issue_credential, revoke_credential, set_membership
from test_dashboard_individual_access import headers

TOOL = TASK_AUDIT_TOOL["name"]
ARGS = {"project": "alpha"}


@pytest.fixture
def audit_runtime(runtime):
    module, client, old, identity, local = runtime
    tokens = {}
    for user, project in (("alice", "alpha"), ("bob", "beta")):
        set_membership(identity, user, project, "owner")
        tokens[user] = issue_credential(identity, user, [project], [AUDIT_READ])
        assert client.post("/api/done", headers=headers(old, user),
            json={"project": project, "id": "T-01", "expected_version": 1}).status_code == 200
    assert client.request("DELETE", "/api/delete", headers=headers(old, "alice"),
        json={"project": "alpha", "id": "T-01", "expected_version": 2}).status_code == 200
    return module, client, old, identity, local, tokens


def page():
    return {"success": True, "project": "alpha", "events": [{"id": str(uuid4()), "project": "alpha",
        "task_id": "T-01", "actor": "alice", "action": "task.complete", "created_at": "2026-10-03 12:00:00",
        "before": {"status": "todo", "version": 1}, "after": {"status": "done", "version": 2}}],
        "supported_actions": ["task.complete", "task.delete", "task.pause", "task.resume"], "has_more": False, "next_before_id": None}


@pytest.mark.parametrize("access", ["disabled", "read", "write"])
def test_audit_exposure_is_explicit_and_disabled_before_secret(tmp_path, monkeypatch, access):
    client = IndividualApiClient("http://127.0.0.1:1", tmp_path / "missing.json", "alpha", task_access=access)
    monkeypatch.setattr(client, "_authorization", lambda: pytest.fail("Disabled audit read credentials"))
    assert TOOL not in {t["name"] for t in client.tools}
    assert client.call(TOOL, ARGS)["code"] == "individual_tool_unavailable"
    client.audit_enabled = True
    assert TOOL in {t["name"] for t in client.tools}


@pytest.mark.parametrize("value", ["true", "yes", "", "2"])
def test_invalid_audit_flag_refuses_startup(tmp_path, monkeypatch, value):
    monkeypatch.setenv("DEVCORE_MCP_API_URL", "http://127.0.0.1:1")
    monkeypatch.setenv("DEVCORE_MCP_CREDENTIAL_FILE", str(tmp_path / "missing.json"))
    monkeypatch.setenv("DEVCORE_MCP_PROJECT", "alpha")
    monkeypatch.setenv("DEVCORE_MCP_TASK_AUDIT", value)
    with pytest.raises(ValueError, match="TASK_AUDIT"):
        IndividualApiClient.from_environment()


@pytest.mark.parametrize("arguments", [{}, {"project": "beta"}, {**ARGS, "limit": True},
    {**ARGS, "limit": 0}, {**ARGS, "limit": 101}, {**ARGS, "task_id": None},
    {**ARGS, "task_id": "../task"}, {**ARGS, "before_id": None}, {**ARGS, "before_id": "invalid"},
    {**ARGS, "actor": "forged"}, {**ARGS, "offset": 0}])
def test_invalid_arguments_never_touch_credentials(tmp_path, monkeypatch, arguments):
    client = IndividualApiClient("http://127.0.0.1:1", tmp_path / "missing.json", "alpha", audit_enabled=True)
    monkeypatch.setattr(client, "_authorization", lambda: pytest.fail("Invalid arguments read credentials"))
    assert client.call(TOOL, arguments)["code"] == "invalid_arguments"


@pytest.mark.parametrize("damage", ["foreign", "foreign_event", "duplicate", "oversize", "limit", "actor",
    "status", "version_bool", "transition", "uuid", "timestamp", "filter", "coverage", "cursor",
    "cursor_empty", "cursor_terminal", "missing_cursor", "duplicate_json", "sensitive_extra"])
def test_invalid_response_is_rejected_before_restitution(tmp_path, monkeypatch, damage):
    value, arguments = page(), ARGS.copy()
    event = value["events"][0]
    if damage == "foreign": value["project"] = "beta"
    elif damage == "foreign_event": event["project"] = "beta"
    elif damage == "duplicate": value["events"].append(copy.deepcopy(event))
    elif damage == "oversize": value["secret"] = "PRIVATE" * 12000
    elif damage == "limit": arguments["limit"] = 1; value["events"].append({**event, "id": str(uuid4())})
    elif damage == "actor": event["actor"] = "PRIVATE\nACTOR"
    elif damage == "status": event["before"]["status"] = []
    elif damage == "version_bool": event["after"]["version"] = True
    elif damage == "transition": event["after"]["version"] = 3
    elif damage == "uuid": event["id"] = "private-invalid-id"
    elif damage == "timestamp": event["created_at"] = "2026-99-03 12:00:00"
    elif damage == "filter": arguments["task_id"] = "T-other"
    elif damage == "coverage": value["supported_actions"].append("legacy.private")
    elif damage == "cursor": value.update(has_more=True, next_before_id=str(uuid4()))
    elif damage == "cursor_empty": value.update(events=[], has_more=True, next_before_id=str(uuid4()))
    elif damage == "cursor_terminal": value["next_before_id"] = event["id"]
    elif damage == "missing_cursor": del value["next_before_id"]
    elif damage == "sensitive_extra":
        value["details"] = event["session_id"] = event["before"]["secret"] = "PRIVATE SECRET"
    raw = json.dumps(value).encode()
    if damage == "duplicate_json": raw = b'{"success":false,' + raw[1:]
    with fake_http(lambda handler: send(handler, raw)) as origin:
        client = IndividualApiClient(origin, tmp_path / "missing.json", "alpha", audit_enabled=True)
        monkeypatch.setattr(client, "_authorization", lambda: "Bearer synthetic-test-only")
        result = client.call(TOOL, arguments)
    if damage == "sensitive_extra":
        assert result["success"] and set(result["events"][0]) == set(page()["events"][0])
    else:
        assert result["code"] == "audit_api_unavailable" and "events" not in result
    assert "PRIVATE" not in json.dumps(result)


@pytest.mark.parametrize("status,code", [(400, "invalid_arguments"), (401, "individual_credential_rejected"),
    (403, "project_access_denied"), (503, "audit_unavailable"), (302, "audit_api_unavailable")])
def test_transport_refusal_is_generic_without_retry_or_redirect(tmp_path, monkeypatch, status, code):
    received = []
    def respond(handler):
        received.append((handler.command, handler.path))
        send(handler, b'{"detail":"PRIVATE REMOTE DETAILS"}', status=status, Location="/redirect")
    with fake_http(respond) as origin:
        client = IndividualApiClient(origin, tmp_path / "missing.json", "alpha", audit_enabled=True)
        monkeypatch.setattr(client, "_authorization", lambda: "Bearer synthetic-test-only")
        result = client.call(TOOL, {**ARGS, "task_id": "T-01", "before_id": str(uuid4()), "limit": 2})
    assert len(received) == 1 and received[0][0] == "GET" and received[0][1].startswith("/api/project/task-audit?")
    assert result["code"] == code and result["http_status"] == status and "PRIVATE" not in json.dumps(result)


@pytest.mark.skipif(os.name != "nt", reason="Real NTFS credentials")
def test_real_stdio_audit_isolated_readonly_paginated_and_revocable(audit_runtime, tmp_path):
    module, _, old, identity, local, tokens = audit_runtime
    alice = secret_file(tmp_path / "alice.json", tokens["alice"][1])
    bob = secret_file(tmp_path / "bob.json", tokens["bob"][1])
    before = (local / "devcore.db").read_bytes()
    async def exercise(origin):
        async with AsyncExitStack() as stack:
            default = await session(stack, tmp_path / "default", "alpha", origin, alice)
            assert TOOL not in {t.name for t in (await default.list_tools()).tools}
            assert payload(await default.call_tool(TOOL, ARGS))["code"] == "individual_tool_unavailable"
            a = await session(stack, tmp_path / "enabled", "alpha", origin, alice, audit_enabled=True,
                              task_access="write", readonly="1", delete_enabled=True)
            b = await session(stack, tmp_path / "enabled", "beta", origin, bob, audit_enabled=True, readonly="1")
            assert {t.name for t in (await a.list_tools()).tools} == {"devcore_project_context", "devcore_task_status", TOOL}
            assert payload(await a.call_tool("devcore_task_delete", {**ARGS, "task_id": "T-01", "expected_version": 3}))["code"] == "individual_tool_unavailable"
            first = await a.call_tool(TOOL, {**ARGS, "limit": 1, "task_id": "T-01"})
            assert not first.isError and len(first.content) == 1 and first.structuredContent is None
            wire = first.content[0].text.encode("utf-8")
            assert wire.endswith(b"\n") and len(wire) <= MAX_AUDIT_RESPONSE_BYTES
            page1 = payload(first)
            assert page1["events"][0]["after"] == {"status": "deleted", "version": 3}
            following = payload(await a.call_tool(TOOL, {**ARGS, "task_id": "T-01", "before_id": page1["next_before_id"]}))
            assert following["events"][0]["after"] == {"status": "done", "version": 2} and not following["has_more"]
            assert payload(await a.call_tool(TOOL, {"project": "beta"}))["code"] == "invalid_arguments"
            for credential in (tokens["bob"][1], old["alice"][1], old["reader"][1]):
                alice.write_text(json.dumps({"token": credential}))
                denied = await a.call_tool(TOOL, ARGS)
                assert denied.isError and payload(denied)["http_status"] == 403
            alice.write_text(json.dumps({"token": tokens["alice"][1]}))
            set_membership(identity, "alice", "alpha", "contributor")
            assert payload(await a.call_tool(TOOL, ARGS))["http_status"] == 403
            set_membership(identity, "alice", "alpha", "owner")
            revoke_credential(identity, tokens["alice"][0])
            assert payload(await a.call_tool(TOOL, ARGS))["http_status"] == 401
            replacement = issue_credential(identity, "alice", ["alpha"], [AUDIT_READ])
            alice.write_text(json.dumps({"token": replacement[1]}))
            assert not (await a.call_tool(TOOL, ARGS)).isError
            assert payload(await b.call_tool(TOOL, {"project": "beta"}))["events"][0]["actor"] == "bob"
            alice.unlink()
            assert payload(await a.call_tool(TOOL, ARGS))["code"] == "individual_credential_unavailable"
    with live_api(module.app) as origin:
        asyncio.run(exercise(origin))
    assert (local / "devcore.db").read_bytes() == before


@pytest.mark.skipif(os.name != "nt", reason="Real NTFS credentials and PowerShell")
@pytest.mark.parametrize("entry", ["source", "engine", "legacy", "powershell"])
def test_cli_audit_entrypoints_share_admission_and_cursor(audit_runtime, tmp_path, entry):
    module, _, old, identity, local, tokens = audit_runtime
    secret = secret_file(tmp_path / "alice.json", tokens["alice"][1])
    before = (local / "devcore.db").read_bytes()
    with live_api(module.app) as origin:
        response, first = cli_call(tmp_path, origin, secret, "alpha", "audit", "--limit", "1", entry=entry,
                                   isolated=entry == "source")
        assert response.returncode == 0 and first["events"][0]["actor"] == "alice"
        assert first["has_more"] and len(response.stdout) <= MAX_AUDIT_RESPONSE_BYTES
        response, second = cli_call(tmp_path, origin, secret, "alpha", "audit", "--before-id", first["next_before_id"], entry=entry)
        assert response.returncode == 0 and second["events"][0]["action"] == "task.complete"
        response, error = cli_call(tmp_path, origin, secret, "alpha", "audit", "--before-id", str(uuid4()), entry=entry)
        assert response.returncode == 2 and error["code"] == "invalid_arguments" and "events" not in error
        secret.write_text(json.dumps({"token": old["alice"][1]}))
        response, error = cli_call(tmp_path, origin, secret, "alpha", "audit", entry=entry)
        assert response.returncode == 1 and error["http_status"] == 403
    assert (local / "devcore.db").read_bytes() == before


@pytest.mark.skipif(os.name != "nt", reason="Real MCP subprocesses and NTFS credentials")
def test_slow_audit_keeps_other_mcp_client_and_ping_responsive(audit_runtime, tmp_path, monkeypatch):
    from devcore_engine.services import task_audit
    module, _, _, _, _, tokens = audit_runtime
    entered, release = threading.Event(), threading.Event()
    original = task_audit.read_task_audit
    def slow(path, principal, **kwargs):
        if principal.project_id == "alpha":
            entered.set()
            if not release.wait(10):
                raise AssertionError("Audit gate timed out")
        return original(path, principal, **kwargs)
    monkeypatch.setattr(task_audit, "read_task_audit", slow)
    alice, bob = [secret_file(tmp_path / (user + ".json"), tokens[user][1]) for user in ("alice", "bob")]
    async def exercise(origin):
        async with AsyncExitStack() as stack:
            a = await session(stack, tmp_path, "alpha", origin, alice, audit_enabled=True)
            b = await session(stack, tmp_path, "beta", origin, bob, audit_enabled=True)
            pending = asyncio.create_task(a.call_tool(TOOL, ARGS))
            try:
                assert await asyncio.to_thread(entered.wait, 3)
                assert not (await asyncio.wait_for(b.call_tool(TOOL, {"project": "beta"}), 3)).isError
                await asyncio.wait_for(a.send_ping(), 3)
                assert not pending.done()
            finally:
                release.set()
                assert not (await pending).isError
    with live_api(module.app) as origin:
        asyncio.run(exercise(origin))


@pytest.mark.parametrize("action,source,target", [("task.pause", "in_progress", "paused"), ("task.resume", "paused", "in_progress")])
def test_client_audit_accepts_transitions_and_refuses_forged_sources(action, source, target):
    from devcore_engine.clients.individual_audit import audit_page
    value = page(); event = value["events"][0]
    event.update(action=action, before={"status": source, "version": 1}, after={"status": target, "version": 2})
    assert audit_page(json.dumps(value), "alpha", 20)["events"][0]["action"] == action
    event["before"]["status"] = "todo"
    with pytest.raises(ValueError, match="Invalid audit transition"):
        audit_page(json.dumps(value), "alpha", 20)
