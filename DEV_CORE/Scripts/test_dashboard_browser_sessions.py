import sqlite3

import pytest
from fastapi.testclient import TestClient

from test_dashboard_individual_access import runtime, headers
from devcore_engine.security.browser_sessions import COOKIE, upgrade_session_store
from devcore_engine.security.identity import READ, issue_credential, revoke_credential, set_membership

ORIGIN = "http://127.0.0.1:20129"


def login(client, credentials, user):
    project = "beta" if user == "bob" else "alpha"
    response = client.post("/api/auth/session", json={"project": project}, headers={**headers(credentials, user), "Origin": ORIGIN})
    assert response.status_code == 200, response.text
    return response


@pytest.mark.parametrize("method,path", [("POST", "/api/done"), ("DELETE", "/api/delete")])
def test_two_browser_cookie_clients_are_isolated_and_logout_is_effective(runtime, method, path):
    module, _, credentials, identity, local = runtime
    upgrade_session_store(identity)
    alice, bob = TestClient(module.app, base_url=ORIGIN), TestClient(module.app, base_url=ORIGIN)
    a, b = login(alice, credentials, "alice"), login(bob, credentials, "bob")
    assert "httponly" in a.headers["set-cookie"].lower()
    assert "samesite=strict" in a.headers["set-cookie"].lower()
    assert "domain=" not in a.headers["set-cookie"].lower()
    assert credentials["alice"][1] not in a.text
    assert a.headers["cache-control"] == "no-store"
    scoped = alice.get("/api/dashboard/tasks", params={"project": "alpha"})
    assert scoped.status_code == 200
    assert scoped.headers["cache-control"] == "no-store"
    assert alice.get("/api/dashboard/tasks", params={"project": "beta"}).status_code == 403
    assert bob.get("/api/dashboard/tasks", params={"project": "alpha"}).status_code == 403
    assert alice.get("/api/auth/session").json()["csrf_token"] == a.json()["csrf_token"]
    body = {"project": "alpha", "id": "T-01", "expected_version": 1}
    assert alice.request(method, path, json=body).status_code == 403
    assert alice.request(method, path, json=body, headers={"Origin": ORIGIN}).status_code == 403
    assert alice.request(method, path, json=body, headers={"Origin": ORIGIN, "X-CSRF-Token": b.json()["csrf_token"]}).status_code == 403
    valid = {"Origin": ORIGIN, "X-CSRF-Token": a.json()["csrf_token"]}
    assert alice.request(method, path, json=body, headers={**valid, "Origin": "http://evil.test"}).status_code == 403
    assert alice.request(method, path, json=body, headers=valid).status_code == 200
    old_cookie = alice.cookies.get(COOKIE)
    assert alice.delete("/api/auth/session", headers={"Origin": ORIGIN}).status_code == 403
    assert alice.delete("/api/auth/session", headers=valid).status_code == 200
    replay = TestClient(module.app, base_url=ORIGIN)
    replay.cookies.set(COOKIE, old_cookie)
    assert replay.get("/api/dashboard/tasks", params={"project": "alpha"}).status_code == 401
    assert bob.get("/api/dashboard/tasks", params={"project": "beta"}).status_code == 200
    with sqlite3.connect(local / "devcore.db") as check:
        assert check.execute("SELECT status,version FROM tasks WHERE project_id='beta'").fetchone() == ("in_progress", 1)


def test_browser_session_follows_source_role_revocation_and_rotation(runtime):
    module, _, credentials, identity, _ = runtime
    upgrade_session_store(identity)
    client = TestClient(module.app, base_url=ORIGIN)
    first = login(client, credentials, "alice")
    old_cookie = client.cookies.get(COOKIE)
    second = login(client, credentials, "alice")
    assert first.json()["csrf_token"] != second.json()["csrf_token"]
    replay = TestClient(module.app, base_url=ORIGIN)
    replay.cookies.set(COOKIE, old_cookie)
    assert replay.get("/api/dashboard/tasks", params={"project": "alpha"}).status_code == 401
    set_membership(identity, "alice", "alpha", "reader")
    assert client.get("/api/auth/session").json()["actions"] == [READ]
    assert client.post("/api/done", json={"project": "alpha", "id": "T-01", "expected_version": 1},
                       headers={"Origin": ORIGIN, "X-CSRF-Token": second.json()["csrf_token"]}).status_code == 403
    revoke_credential(identity, credentials["alice"][0])
    assert client.get("/api/dashboard/tasks", params={"project": "alpha"}).status_code == 401


def test_project_shell_is_public_without_private_data_or_shared_injection(runtime, monkeypatch):
    module, client, credentials, _, _ = runtime
    def shared_injection(*args):
        raise AssertionError("Individual shell must not bootstrap or inject shared credentials")
    monkeypatch.setattr(module, "ensure_api_token", shared_injection)
    monkeypatch.setattr(module, "inject_auth_fetch", shared_injection)
    for path, media_type in (("/project", "text/html"), ("/project.js", "text/javascript")):
        response = client.get(path)
        assert response.status_code == 200
        assert media_type in response.headers["content-type"]
        assert response.headers["cache-control"] == "no-store"
        assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
        assert response.headers["x-content-type-options"] == "nosniff"
        assert credentials["alice"][1] not in response.text
    assert client.get("/project.js/../template.html").status_code == 403
    monkeypatch.setattr(module, "DASHBOARD_AUTH_PROFILE", "legacy")
    assert client.get("/project").status_code == 403


def test_session_describes_only_current_membership_and_credential_rights(runtime):
    module, _, credentials, identity, _ = runtime
    upgrade_session_store(identity)
    client = TestClient(module.app, base_url=ORIGIN)
    assert login(client, credentials, "alice").json()["actions"] == ["task.read", "task.mutate"]
    set_membership(identity, "alice", "alpha", "reader")
    assert client.get("/api/auth/session").json()["actions"] == [READ]
    set_membership(identity, "alice", "alpha", "contributor")
    readonly = issue_credential(identity, "alice", ["alpha"], [READ])
    response = client.post("/api/auth/session", json={"project": "alpha"},
                           headers={"Authorization": "Bearer " + readonly[1], "Origin": ORIGIN})
    assert response.status_code == 200
    assert response.json()["actions"] == [READ]
    assert client.get("/api/auth/session").json()["actions"] == [READ]
    assert client.post("/api/done", json={"project": "alpha", "id": "T-01", "expected_version": 1},
                       headers={"Origin": ORIGIN, "X-CSRF-Token": response.json()["csrf_token"]}).status_code == 403


def test_session_exchange_requires_trusted_origin_explicit_upgrade_and_https_rules(runtime, monkeypatch):
    module, _, credentials, identity, _ = runtime
    client = TestClient(module.app, base_url=ORIGIN)
    auth = headers(credentials, "alice")
    assert client.post("/api/auth/session", json={"project": "alpha"}, headers=auth).status_code == 403
    assert client.post("/api/auth/session", json={"project": "alpha"}, headers={**auth, "Origin": "http://evil.test"}).status_code == 403
    assert client.post("/api/auth/session", json={"project": "alpha"}, headers={**auth, "Origin": ORIGIN}).status_code == 503
    with monkeypatch.context() as limits:
        limits.setenv("DEVCORE_MAX_REQUEST_BODY_BYTES", "64")
        assert client.post("/api/auth/session", content=b"x" * 65, headers={**auth, "Origin": ORIGIN}).status_code == 413
    upgrade_session_store(identity)
    assert client.post("/api/auth/session", json={"project": "alpha"}, headers={"Authorization": "Bearer invalid", "Origin": ORIGIN}).status_code == 401
    secure_origin = "https://localhost:20129"
    monkeypatch.setenv("DEVCORE_CORS_ALLOWED_ORIGINS", secure_origin + ",http://remote.test")
    secure = TestClient(module.app, base_url=secure_origin)
    response = secure.post("/api/auth/session", json={"project": "alpha"}, headers={**auth, "Origin": secure_origin})
    assert response.status_code == 200
    assert "secure" in response.headers["set-cookie"].lower()
    insecure = TestClient(module.app, base_url="http://remote.test")
    assert insecure.post("/api/auth/session", json={"project": "alpha"}, headers={**auth, "Origin": "http://remote.test"}).status_code == 403
