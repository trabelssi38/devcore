"""Scoped, bounded task history on disposable stores; no active data fixtures."""

import asyncio
from contextlib import closing
import json
import sqlite3
import threading
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from test_dashboard_individual_access import runtime, headers
from test_dashboard_password_login import password_runtime, login
from devcore_engine.security.identity import (
    AUDIT_READ, READ, Principal, ProjectAccessDenied,
    issue_credential, revoke_credential, set_membership,
)
from devcore_engine.security.browser_sessions import upgrade_session_store
from devcore_engine.services import task_audit as adapter

URL = "/api/project/task-audit"
ORIGIN = "http://127.0.0.1:20129"


@pytest.fixture
def audit_runtime(runtime):
    module, client, old, identity, local = runtime
    tokens = {}
    for user, project in (("alice", "alpha"), ("bob", "beta")):
        set_membership(identity, user, project, "owner")
        tokens[user] = issue_credential(identity, user, [project], [AUDIT_READ])
        response = client.post("/api/done", headers=headers(old, user),
                               json={"project": project, "id": "T-01", "expected_version": 1})
        assert response.status_code == 200
    return module, client, old, identity, local, tokens


def insert_event(conn, project="alpha", *, actor="alice", task="T-01", action="task.complete", details=None):
    identifier = str(uuid4())
    value = details or {"schema_version": 1, "before": {"status": "todo", "version": 1},
                        "after": {"status": "done" if action == "task.complete" else "deleted", "version": 2}}
    conn.execute("INSERT INTO audit_log(id,project_id,task_id,actor,action,entity_type,entity_id,details) "
                 "VALUES (?,?,?,?,?,'task',?,?)", (identifier, project, task, actor, action, task,
                                                value if isinstance(value, str) else json.dumps(value)))
    return identifier


def test_audit_scope_is_separate_and_projection_keeps_only_author_and_versions(audit_runtime):
    _, client, old, _, local, tokens = audit_runtime
    before = (local / "devcore.db").read_bytes()
    for user, project in (("alice", "alpha"), ("bob", "beta")):
        result = client.get(URL, params={"project": project}, headers=headers(tokens, user))
        assert result.status_code == 200 and result.headers["cache-control"] == "no-store"
        assert result.content.endswith(b"\n") and len(result.content) <= adapter.MAX_AUDIT_BYTES
        page = result.json()
        assert page["project"] == project and page["supported_actions"] == list(adapter.QUALIFIED_ACTIONS)
        assert len(page["events"]) == 1 and not page["has_more"] and page["next_before_id"] is None
        event = page["events"][0]
        assert (event["project"], event["actor"], event["task_id"], event["action"]) == (project, user, "T-01", "task.complete")
        assert event["before"]["version"] == 1 and event["after"] == {"status": "done", "version": 2}
        assert set(event) == {"id", "project", "actor", "task_id", "action", "created_at", "before", "after"}
        assert "details" not in event and "session_id" not in event and "trace_id" not in event
        assert client.get(URL, params={"project": project}, headers=headers(old, user)).status_code == 403
        assert client.get("/api/dashboard/tasks", params={"project": project}, headers=headers(tokens, user)).status_code == 403
        assert client.get("/api/project/context", params={"project": project}, headers=headers(tokens, user)).status_code == 403
    assert client.get(URL, params={"project": "beta"}, headers=headers(tokens, "alice")).status_code == 403
    assert (local / "devcore.db").read_bytes() == before


def test_denied_requests_never_read_audit_store(audit_runtime, monkeypatch):
    _, client, old, _, _, tokens = audit_runtime
    def forbidden(*args, **kwargs):
        raise AssertionError("Denied request touched audit storage")
    monkeypatch.setattr(adapter, "read_task_audit", forbidden)
    for auth, project, status in (({}, "alpha", 401), (headers(old, "alice"), "alpha", 403),
                                  (headers(tokens, "alice"), "beta", 403), (headers(old, "reader"), "alpha", 403)):
        assert client.get(URL, params={"project": project}, headers=auth).status_code == status


def test_deleted_task_keeps_qualified_history_and_cursor_task_filter(audit_runtime):
    _, client, old, _, _, tokens = audit_runtime
    deleted = client.request("DELETE", "/api/delete", headers=headers(old, "alice"),
                            json={"project": "alpha", "id": "T-01", "expected_version": 2})
    assert deleted.status_code == 200
    auth = headers(tokens, "alice")
    response = client.get(URL, params={"project": "alpha", "task_id": "T-01", "limit": 1}, headers=auth)
    assert response.status_code == 200
    page = response.json()
    event = page["events"][0]
    assert event["action"] == "task.delete" and event["actor"] == "alice"
    assert event["before"] == {"status": "done", "version": 2}
    assert event["after"] == {"status": "deleted", "version": 3}
    following = client.get(URL, params={"project": "alpha", "task_id": "T-01", "before_id": page["next_before_id"]}, headers=auth)
    assert following.status_code == 200 and following.json()["events"][0]["action"] == "task.complete"
    assert client.get(URL, params={"project": "alpha", "task_id": "T-other", "before_id": page["next_before_id"]}, headers=auth).status_code == 400


@pytest.mark.parametrize("change,status", [("revoke", 401), ("contributor", 403), ("reader", 403)])
def test_audit_rechecks_current_credentials_and_owner_role(audit_runtime, change, status):
    _, client, _, identity, _, tokens = audit_runtime
    auth = headers(tokens, "alice")
    if change == "revoke":
        revoke_credential(identity, tokens["alice"][0])
    else:
        set_membership(identity, "alice", "alpha", change)
    assert client.get(URL, params={"project": "alpha"}, headers=auth).status_code == status
    assert client.get(URL, params={"project": "beta"}, headers=headers(tokens, "bob")).status_code == 200


@pytest.mark.parametrize("role", ["reader", "contributor"])
def test_non_owner_cannot_issue_audit_scope(audit_runtime, role):
    _, _, _, identity, _, _ = audit_runtime
    set_membership(identity, "alice", "alpha", role)
    with pytest.raises(ValueError):
        issue_credential(identity, "alice", ["alpha"], [AUDIT_READ])


def test_cursor_pages_are_scoped_filtered_and_do_not_duplicate_after_append(audit_runtime):
    _, client, _, _, local, tokens = audit_runtime
    with closing(sqlite3.connect(local / "devcore.db")) as conn, conn:
        ids = [insert_event(conn) for _ in range(4)]
        foreign = insert_event(conn, "beta", actor="bob")
    auth = headers(tokens, "alice")
    first = client.get(URL, params={"project": "alpha", "limit": 2, "task_id": "T-01"}, headers=auth).json()
    assert [e["id"] for e in first["events"]] == ids[-2:][::-1]
    assert first["has_more"] and first["next_before_id"] == ids[-2]
    with closing(sqlite3.connect(local / "devcore.db")) as conn, conn:
        inserted_later = insert_event(conn)
    second = client.get(URL, params={"project": "alpha", "limit": 2, "task_id": "T-01", "before_id": first["next_before_id"]}, headers=auth).json()
    assert [e["id"] for e in second["events"]] == ids[:2][::-1] and inserted_later not in str(second)
    assert set(e["id"] for e in first["events"]).isdisjoint(e["id"] for e in second["events"])
    missing = client.get(URL, params={"project": "alpha", "before_id": str(uuid4())}, headers=auth)
    denied = client.get(URL, params={"project": "alpha", "before_id": foreign}, headers=auth)
    assert denied.status_code == missing.status_code == 400 and denied.json() == missing.json()
    assert client.get(URL, params={"project": "alpha", "task_id": "T-other"}, headers=auth).json()["events"] == []


@pytest.mark.parametrize("arguments", [{"limit": "0"}, {"limit": "101"}, {"limit": "true"},
    {"limit": "1.5"}, {"before_id": "private-invalid-cursor"}, {"task_id": "../task"}, {"actor": "forged"}])
def test_invalid_audit_arguments_are_generic(audit_runtime, arguments):
    _, client, _, _, _, tokens = audit_runtime
    response = client.get(URL, params={"project": "alpha", **arguments}, headers=headers(tokens, "alice"))
    assert response.status_code == 400 and response.json()["detail"]["code"] == "invalid_audit_arguments"
    assert all(str(value) not in response.text for value in arguments.values())


@pytest.mark.parametrize("damage", ["invalid_json", "bad_version", "missing_table", "bad_actor"])
def test_malformed_qualified_audit_fails_without_partial_data_or_paths(audit_runtime, damage):
    _, client, _, _, local, tokens = audit_runtime
    with closing(sqlite3.connect(local / "devcore.db")) as conn, conn:
        if damage == "missing_table":
            conn.execute("DROP TABLE audit_log")
        else:
            row = {"schema_version": 1, "before": {"status": "todo", "version": 1},
                   "after": {"status": "done", "version": True}}
            insert_event(conn, actor="PRIVATE\nACTOR" if damage == "bad_actor" else "alice",
                         details="PRIVATE INVALID JSON" if damage == "invalid_json" else row if damage == "bad_version" else None)
    response = client.get(URL, params={"project": "alpha"}, headers=headers(tokens, "alice"))
    assert response.status_code == 503 and "events" not in response.json()
    assert "PRIVATE" not in response.text and str(local) not in response.text


def test_extra_sensitive_fields_are_discarded_and_foreign_malformed_rows_not_decoded(audit_runtime):
    _, client, _, _, local, tokens = audit_runtime
    with closing(sqlite3.connect(local / "devcore.db")) as conn, conn:
        insert_event(conn, "beta", actor="bob", details="FOREIGN PRIVATE INVALID JSON")
        insert_event(conn, details={"schema_version": 1, "private_token": "PRIVATE SECRET",
            "session_id": "PRIVATE SESSION", "trace_id": "PRIVATE TRACE", "title": "PRIVATE TITLE",
            "before": {"status": "todo", "version": 1, "secret": "PRIVATE FIELD"}, "after": {"status": "done", "version": 2}})
        insert_event(conn, action="legacy.unqualified", details="PRIVATE LEGACY DETAILS")
    response = client.get(URL, params={"project": "alpha"}, headers=headers(tokens, "alice"))
    assert response.status_code == 200 and len(response.json()["events"]) == 2 and "PRIVATE" not in response.text


def test_audit_response_limit_returns_a_followable_cursor(audit_runtime, monkeypatch):
    _, client, _, _, local, tokens = audit_runtime
    with closing(sqlite3.connect(local / "devcore.db")) as conn, conn:
        for _ in range(20):
            insert_event(conn)
    monkeypatch.setattr(adapter, "MAX_AUDIT_BYTES", 1100)
    response = client.get(URL, params={"project": "alpha", "limit": 100}, headers=headers(tokens, "alice"))
    assert response.status_code == 200 and len(response.content) <= 1100
    page = response.json()
    assert 0 < len(page["events"]) < 21 and page["has_more"] and page["next_before_id"] == page["events"][-1]["id"]
    following = client.get(URL, params={"project": "alpha", "before_id": page["next_before_id"]}, headers=headers(tokens, "alice"))
    assert following.status_code == 200 and set(e["id"] for e in page["events"]).isdisjoint(e["id"] for e in following.json()["events"])


def test_cookie_audit_requires_scope_and_follows_role_and_revocation(audit_runtime):
    module, _, old, identity, _, _ = audit_runtime
    upgrade_session_store(identity)
    _, token = issue_credential(identity, "alice", ["alpha"], [READ, AUDIT_READ])
    with TestClient(module.app, base_url=ORIGIN) as client:
        login = client.post("/api/auth/session", json={"project": "alpha"}, headers={"Authorization": "Bearer " + token, "Origin": ORIGIN})
        assert login.status_code == 200 and AUDIT_READ in login.json()["actions"]
        assert client.get(URL, params={"project": "alpha"}).status_code == 200
        assert client.get(URL, params={"project": "beta"}).status_code == 403
        assert client.get(URL, params={"project": "alpha"}, headers={"Origin": "http://evil.test"}).status_code == 403
        set_membership(identity, "alice", "alpha", "contributor")
        assert client.get(URL, params={"project": "alpha"}).status_code == 403
        assert AUDIT_READ not in client.get("/api/auth/session").json()["actions"]
    # A historical task credential gains no audit permission after a role upgrade.
    set_membership(identity, "alice", "alpha", "owner")
    with TestClient(module.app, base_url=ORIGIN) as client:
        client.post("/api/auth/session", json={"project": "alpha"}, headers={**headers(old, "alice"), "Origin": ORIGIN})
        assert client.get(URL, params={"project": "alpha"}).status_code == 403


def test_slow_audit_does_not_block_other_project_or_status(audit_runtime, monkeypatch):
    module, _, _, _, _, tokens = audit_runtime
    original = adapter.read_task_audit
    entered, release = threading.Event(), threading.Event()
    def slow(path, principal, **kwargs):
        if principal.project_id == "alpha":
            entered.set()
            release.wait(5)
        return original(path, principal, **kwargs)
    monkeypatch.setattr(adapter, "read_task_audit", slow)
    async def exercise():
        import httpx
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=module.app), base_url=ORIGIN) as client:
            waiting = asyncio.create_task(client.get(URL, params={"project": "alpha"}, headers=headers(tokens, "alice")))
            try:
                assert await asyncio.to_thread(entered.wait, 2)
                result = await asyncio.wait_for(client.get(URL, params={"project": "beta"}, headers=headers(tokens, "bob")), 2)
                assert result.status_code == 200 and not waiting.done()
                assert (await asyncio.wait_for(client.get("/api/status"), 2)).status_code == 200
            finally:
                release.set()
                assert (await waiting).status_code == 200
    asyncio.run(exercise())


def test_reader_never_creates_a_database_and_rejects_unadmitted_principal(tmp_path):
    missing = tmp_path / "missing.db"
    with pytest.raises(ProjectAccessDenied):
        adapter.read_task_audit(missing, Principal("alice", "id", "alpha", READ))
    with pytest.raises(adapter.TaskAuditUnavailable):
        adapter.read_task_audit(missing, Principal("alice", "id", "alpha", AUDIT_READ))
    assert not missing.exists()


def test_production_byte_bound_counts_multibyte_authors_and_cursor(tmp_path):
    path = tmp_path / "audit.db"
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("CREATE TABLE audit_log(id TEXT PRIMARY KEY, project_id TEXT, task_id TEXT, "
                     "actor TEXT, action TEXT, entity_type TEXT, entity_id TEXT, details TEXT, "
                     "created_at TEXT DEFAULT (datetime('now')))")
        for _ in range(100):
            insert_event(conn, actor="\U0001f642" * 128)
    principal = Principal("alice", "id", "alpha", AUDIT_READ)
    page = adapter.read_task_audit(path, principal, limit=100)
    wire = (json.dumps(page, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    assert len(wire) <= 65536 and 0 < len(page["events"]) < 100 and page["has_more"]
    following = adapter.read_task_audit(path, principal, before_id=page["next_before_id"], limit=100)
    assert len(page["events"]) + len(following["events"]) == 100
    assert not following["has_more"] and following["next_before_id"] is None
    assert set(e["id"] for e in page["events"]).isdisjoint(e["id"] for e in following["events"])
    with pytest.raises(adapter.TaskAuditUnavailable):
        adapter.read_task_audit(path, Principal("alice", "id", "p" * 65536, AUDIT_READ))


def test_password_session_grants_audit_only_to_current_project_owner(password_runtime):
    module, identity, _ = password_runtime
    set_membership(identity, "alice", "alpha", "owner")
    with TestClient(module.app, base_url=ORIGIN) as owner, TestClient(module.app, base_url=ORIGIN) as contributor:
        assert AUDIT_READ in login(owner).json()["actions"]
        assert owner.get(URL, params={"project": "alpha"}).status_code == 200
        assert AUDIT_READ not in login(contributor, "bob", "beta").json()["actions"]
        assert contributor.get(URL, params={"project": "beta"}).status_code == 403
        set_membership(identity, "alice", "alpha", "contributor")
        assert owner.get(URL, params={"project": "alpha"}).status_code == 403


def test_legacy_profile_does_not_admit_audit_with_shared_credentials(audit_runtime, monkeypatch):
    module, client, _, _, _, tokens = audit_runtime
    monkeypatch.setattr(module, "DASHBOARD_AUTH_PROFILE", "legacy")
    monkeypatch.setattr(module, "check_auth", lambda request: True)
    assert client.get(URL, params={"project": "alpha"}, headers=headers(tokens, "alice")).status_code == 403
