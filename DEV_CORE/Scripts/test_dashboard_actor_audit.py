"""Authors come from admitted HTTP identities, not request JSON or headers."""

from concurrent.futures import ThreadPoolExecutor
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from test_dashboard_individual_access import runtime, headers
from test_dashboard_browser_sessions import ORIGIN, login
from devcore_engine.security.browser_sessions import COOKIE, upgrade_session_store


@pytest.mark.parametrize("method,path,action", [
    ("POST", "/api/done", "task.complete"), ("DELETE", "/api/delete", "task.delete"),
])
def test_simultaneous_projects_keep_their_authenticated_authors(runtime, method, path, action):
    module, client, credentials, _, local = runtime
    def mutate(user, project):
        with TestClient(module.app) as isolated:
            return isolated.request(method, path, headers={**headers(credentials, user), "X-User-Id": "mallory"},
                json={"project": project, "id": "t-01", "expected_version": 1,
                      "actor": "mallory", "user_id": "mallory", "trace_id": "forged-trace",
                      "password": "fixture-private-password", "token": "fixture-private-token"})
    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(mutate, "alice", "alpha")
        b = pool.submit(mutate, "bob", "beta")
        assert a.result().status_code == b.result().status_code == 200
    with sqlite3.connect(local / "devcore.db") as conn:
        rows = conn.execute("SELECT project_id,actor,action,entity_id,details FROM audit_log ORDER BY project_id").fetchall()
        assert [(r[0], r[1], r[2], r[3]) for r in rows] == [
            ("alpha", "alice", action, "T-01"), ("beta", "bob", action, "T-01"),
        ]
        assert len({json.loads(r[4])["trace_id"] for r in rows}) == 2
        serialized = str(rows)
        for forbidden in ("mallory", "forged-trace", "fixture-private-password", "fixture-private-token",
                          credentials["alice"][1], credentials["bob"][1]):
            assert forbidden not in serialized
    assert client.request(method, path, headers=headers(credentials, "alice"),
        json={"project": "alpha", "id": "T-01", "expected_version": 1}).status_code in (404, 409)
    with sqlite3.connect(local / "devcore.db") as conn:
        assert conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0] == 2


def test_cookie_history_records_session_id_without_cookie_or_csrf(runtime):
    module, _, credentials, identity, local = runtime
    upgrade_session_store(identity)
    with TestClient(module.app, base_url=ORIGIN) as client:
        session = login(client, credentials, "alice")
        cookie = client.cookies.get(COOKIE)
        csrf = session.json()["csrf_token"]
        response = client.post("/api/done", json={"project": "alpha", "id": "T-01", "expected_version": 1},
                               headers={"Origin": ORIGIN, "X-CSRF-Token": csrf})
        assert response.status_code == 200
    with sqlite3.connect(identity) as conn:
        session_id = conn.execute("SELECT id FROM identity_browser_sessions").fetchone()[0]
    with sqlite3.connect(local / "devcore.db") as conn:
        actor, details = conn.execute("SELECT actor,details FROM audit_log").fetchone()
        assert actor == "alice"
        assert json.loads(details)["session_id"] == session_id
        assert cookie not in details and csrf not in details and credentials["alice"][1] not in details


@pytest.mark.parametrize("method,path", [("POST", "/api/done"), ("DELETE", "/api/delete")])
def test_missing_audit_store_refuses_individual_mutation_and_rolls_back(runtime, method, path):
    _, client, credentials, _, local = runtime
    with sqlite3.connect(local / "devcore.db") as conn:
        conn.execute("DROP TABLE audit_log")
    response = client.request(method, path, headers=headers(credentials, "alice"),
                              json={"project": "alpha", "id": "T-01", "expected_version": 1})
    assert response.status_code == 500
    with sqlite3.connect(local / "devcore.db") as conn:
        assert conn.execute("SELECT status,version FROM tasks WHERE project_id='alpha'").fetchone() == ("in_progress", 1)


def test_denied_project_and_reader_do_not_produce_success_history(runtime):
    _, client, credentials, _, local = runtime
    body = {"project": "beta", "id": "T-01", "expected_version": 1}
    assert client.post("/api/done", json=body, headers=headers(credentials, "alice")).status_code == 403
    body["project"] = "alpha"
    assert client.post("/api/done", json=body, headers=headers(credentials, "reader")).status_code == 403
    with sqlite3.connect(local / "devcore.db") as conn:
        assert conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0] == 0
