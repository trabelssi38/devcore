"""Schema4 administration coexists with project cookies without granting task bypasses."""

import sqlite3

import pytest
from fastapi.testclient import TestClient

from test_dashboard_password_login import password_runtime, login, PASSWORD
from test_dashboard_individual_access import runtime
from test_dashboard_browser_sessions import ORIGIN
from devcore_engine.security import administration as admin


@pytest.mark.parametrize("method,path", [("POST", "/api/done"), ("DELETE", "/api/delete")])
def test_admin_schema_keeps_password_sessions_scoped_and_audited(password_runtime, method, path):
    module, identity, local = password_runtime
    admin.upgrade_admin_store(identity)
    admin.bootstrap_admin(identity, "alice")
    _, token = admin.login_admin(identity, "alice", PASSWORD)
    with TestClient(module.app) as caller:
        assert caller.get("/api/dashboard/tasks", params={"project": "alpha"},
                          headers={"Authorization": "Bearer " + token}).status_code == 401
        assert caller.get("/api/project/context", params={"project": "alpha"},
                          headers={"Authorization": "Bearer " + token}).status_code == 401
    with TestClient(module.app, base_url=ORIGIN) as client:
        session = login(client)
        assert session.status_code == 200
        assert client.get("/api/dashboard/tasks", params={"project": "beta"}).status_code == 403
        response = client.request(method, path, json={"project": "alpha", "id": "T-01", "expected_version": 1},
                                  headers={"Origin": ORIGIN, "X-CSRF-Token": session.json()["csrf_token"]})
        assert response.status_code == 200
    with sqlite3.connect(local / "devcore.db") as conn:
        assert conn.execute("SELECT actor,project_id FROM audit_log").fetchall() == [("alice", "alpha")]
        assert conn.execute("SELECT status,version FROM tasks WHERE project_id='beta'").fetchone() == ("in_progress", 1)
