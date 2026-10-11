"""Individual transitions on disposable stores with real admission middleware."""

import json
import sqlite3
import pytest
from fastapi.testclient import TestClient
from test_dashboard_individual_access import runtime, headers
from test_dashboard_browser_sessions import ORIGIN, login
from devcore_engine.security.browser_sessions import COOKIE, upgrade_session_store
from devcore_engine.security.identity import revoke_credential


@pytest.fixture(params=[("pause", "in_progress", "paused"), ("resume", "paused", "in_progress")])
def transition(runtime, request):
    module, client, credentials, identity, local = runtime
    operation, before, after = request.param
    with sqlite3.connect(local / "devcore.db") as conn:
        if before == "paused":
            conn.execute("UPDATE tasks SET status='paused' WHERE project_id='alpha'")
        version = conn.execute("SELECT version FROM tasks WHERE project_id='alpha'").fetchone()[0]
    return module, client, credentials, identity, local, operation, before, after, version


def body_for(t):
    return {"project": "alpha", "id": "t-01", "expected_version": t[-1]}


def test_individual_transition_scope_version_author_and_revocation(transition):
    module, client, credentials, identity, local, operation, before, after, version = transition
    url, body = "/api/" + operation, body_for(transition)
    assert client.post(url, json=body).status_code == 401
    for user in ("reader", "bob"):
        assert client.post(url, json=body, headers=headers(credentials, user)).status_code == 403
    auth = headers(credentials, "alice")
    assert client.post(url, json={**body, "expected_version": None}, headers=auth).status_code == 400
    assert client.post(url, json={**body, "expected_version": True}, headers=auth).status_code == 400
    assert client.post(url, json={**body, "id": "T-missing"}, headers=auth).status_code == 404
    stale = client.post(url, json={**body, "expected_version": version + 1}, headers=auth)
    assert stale.status_code == 409 and stale.json()["detail"]["code"] == "stale_task_version"
    response = client.post(url, headers={**auth, "X-User-Id": "mallory"},
        json={**body, "actor": "mallory", "user_id": "mallory", "trace_id": "forged",
              "token": "private-fixture-token"})
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    assert client.post(url, json=body, headers=auth).status_code == 409
    assert client.post(url, json={**body, "expected_version": version+1}, headers=auth).status_code == 409
    with sqlite3.connect(local / "devcore.db") as conn:
        assert conn.execute("SELECT status,version FROM tasks WHERE project_id='alpha'").fetchone() == (after, version+1)
        assert conn.execute("SELECT status,version FROM tasks WHERE project_id='beta'").fetchone() == ("in_progress", 1)
        rows = conn.execute("SELECT actor,action,details FROM audit_log").fetchall()
        assert len(rows) == 1 and rows[0][:2] == ("alice", "task."+operation)
        details = json.loads(rows[0][2])
        assert details["before"] == {"status": before, "version": version}
        assert details["after"] == {"status": after, "version": version+1}
        assert "mallory" not in str(rows) and "forged" not in str(rows) and "private-fixture-token" not in str(rows)
    revoke_credential(identity, credentials["alice"][0])
    assert client.post(url, json={**body, "expected_version": version+1}, headers=auth).status_code == 401
    assert client.get("/api/dashboard/tasks", params={"project": "beta"}, headers=headers(credentials, "bob")).status_code == 200


def test_cookie_transition_checks_csrf_and_records_only_session_id(transition):
    module, _, credentials, identity, local, operation, before, after, version = transition
    upgrade_session_store(identity)
    with TestClient(module.app, base_url=ORIGIN) as client:
        csrf = login(client, credentials, "alice").json()["csrf_token"]
        cookie = client.cookies.get(COOKIE)
        url, body = "/api/"+operation, body_for(transition)
        for h in ({"Origin": ORIGIN}, {"Origin": "http://evil.test", "X-CSRF-Token": csrf}):
            assert client.post(url, json=body, headers=h).status_code == 403
        with sqlite3.connect(local / "devcore.db") as conn:
            assert conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0] == 0
        assert client.post(url, json=body, headers={"Origin": ORIGIN, "X-CSRF-Token": csrf}).status_code == 200
    with sqlite3.connect(identity) as conn:
        session = conn.execute("SELECT id FROM identity_browser_sessions").fetchone()[0]
    with sqlite3.connect(local / "devcore.db") as conn:
        actor, text = conn.execute("SELECT actor,details FROM audit_log").fetchone()
        assert actor == "alice" and json.loads(text)["session_id"] == session
        assert cookie not in text and csrf not in text and credentials["alice"][1] not in text


@pytest.mark.parametrize("table", ["audit_log", "bus_events"])
def test_transition_storage_failure_rolls_back_without_leaking_details(transition, table):
    _, client, credentials, _, local, operation, before, after, version = transition
    with sqlite3.connect(local / "devcore.db") as conn:
        baseline = conn.execute("SELECT COUNT(*) FROM bus_events").fetchone()[0]
        conn.execute("CREATE TRIGGER reject_fixture BEFORE INSERT ON " + table +
                     " BEGIN SELECT RAISE(ABORT, 'PRIVATE STORAGE FAILURE'); END")
    result = client.post("/api/"+operation, json=body_for(transition), headers=headers(credentials, "alice"))
    assert result.status_code == 500 and result.json()["detail"]["code"] == "task_transition_unavailable"
    assert "PRIVATE" not in result.text and str(local) not in result.text
    with sqlite3.connect(local / "devcore.db") as conn:
        assert conn.execute("SELECT status,version FROM tasks WHERE project_id='alpha'").fetchone() == (before, version)
        assert conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM bus_events").fetchone()[0] == baseline


def test_transition_routes_refuse_legacy_profile(transition, monkeypatch):
    module, client, credentials, _, local, operation, *_ = transition
    monkeypatch.setattr(module, "DASHBOARD_AUTH_PROFILE", "legacy")
    monkeypatch.setattr(module, "check_auth", lambda request: True)
    monkeypatch.setattr(module, "check_csrf", lambda request, method: True)
    result = client.post("/api/"+operation, json=body_for(transition), headers=headers(credentials, "alice"))
    assert result.status_code == 403 and result.json()["detail"]["code"] == "individual_route_required"
    with sqlite3.connect(local / "devcore.db") as conn:
        assert conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0] == 0
