import importlib.util
import asyncio
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading

import pytest
from fastapi.testclient import TestClient

from devcore_engine.db import init_db
from devcore_engine.security.identity import (
    READ, WRITE, add_user, initialize_store, issue_credential, revoke_credential, set_membership,
)


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    local, shared = tmp_path / "local", tmp_path / "shared"
    local.mkdir()
    shared.mkdir()
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(local))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(shared))
    monkeypatch.setenv("DEVCORE_DASHBOARD_AUTH_PROFILE", "individual")
    identity = local / "Security" / "identity.db"
    monkeypatch.setenv("DEVCORE_IDENTITY_STORE", str(identity))
    initialize_store(identity)
    credentials = {}
    for user, project, role in (("alice", "alpha", "contributor"), ("bob", "beta", "contributor"), ("reader", "alpha", "reader")):
        add_user(identity, user)
        set_membership(identity, user, project, role)
        credentials[user] = issue_credential(identity, user, [project], [READ] if role == "reader" else [READ, WRITE])
    conn = init_db(local / "devcore.db")
    for project in ("alpha", "beta"):
        conn.execute("INSERT INTO projects(id,name,root_path) VALUES (?,?,'.')", (project, project))
        conn.execute("INSERT INTO tasks(id,project_id,title,status) VALUES ('T-01',?,?,'in_progress')", (project, project))
    conn.commit()
    conn.close()
    spec = importlib.util.spec_from_file_location("dashboard_individual_under_test", Path(__file__).with_name("dashboard_api.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, TestClient(module.app), credentials, identity, local


def headers(credentials, user):
    return {"Authorization": "Bearer " + credentials[user][1]}


@pytest.mark.parametrize("method,path,expected_status", [("POST", "/api/done", "done"), ("DELETE", "/api/delete", "deleted")])
def test_individual_requests_enforce_projects_roles_versions_and_revocation(runtime, method, path, expected_status):
    module, client, credentials, identity, local = runtime
    assert client.get("/api/dashboard/tasks", params={"project": "alpha"}).status_code == 401
    assert client.get("/api/dashboard/tasks", params={"project": "beta"}, headers=headers(credentials, "alice")).status_code == 403
    observed = client.get("/api/dashboard/tasks", params={"project": "alpha"}, headers=headers(credentials, "alice"))
    assert observed.status_code == 200
    assert observed.json()[0]["title"] == "alpha"
    body = {"project": "alpha", "id": "T-01", "expected_version": 1}
    assert client.request(method, path, json=body, headers=headers(credentials, "reader")).status_code == 403
    assert client.request(method, path, json=body, headers=headers(credentials, "bob")).status_code == 403
    assert client.request(method, path, json={"project": "alpha", "id": "T-01"}, headers=headers(credentials, "alice")).status_code == 400
    with sqlite3.connect(local / "devcore.db") as writer:
        writer.execute("UPDATE tasks SET title='Concurrent edit' WHERE project_id='alpha'")
    stale = client.request(method, path, json=body, headers=headers(credentials, "alice"))
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "stale_task_version"
    body["expected_version"] = 2
    accepted = client.request(method, path, json=body, headers=headers(credentials, "alice"))
    assert accepted.status_code == 200
    with sqlite3.connect(local / "devcore.db") as check:
        assert check.execute("SELECT status,version FROM tasks WHERE project_id='alpha'").fetchone() == (expected_status, 3)
        assert check.execute("SELECT status,version FROM tasks WHERE project_id='beta'").fetchone() == ("in_progress", 1)
    revoke_credential(identity, credentials["alice"][0])
    assert client.get("/api/dashboard/tasks", params={"project": "alpha"}, headers=headers(credentials, "alice")).status_code == 401
    assert client.get("/api/dashboard/tasks", params={"project": "beta"}, headers=headers(credentials, "bob")).status_code == 200


@pytest.mark.parametrize("path", ["/", "/index.html", "/index_terminal.html", "/api/dashboard", "/api/dashboard/stream", "/api/memory/search", "/api/settings", "/api/refresh"])
def test_global_routes_are_closed_in_individual_profile(runtime, path):
    module, client, credentials, _, _ = runtime
    response = client.get(path, headers=headers(credentials, "alice"))
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "individual_route_unavailable"
    assert module.inject_auth_fetch("<head></head>") == "<head></head>"
    assert not (Path(module.DATA_ROOT) / "Security").exists()


def test_every_unqualified_http_route_fails_closed_in_individual_profile(runtime):
    """New/global routes must stay denied until an individual ACL is qualified."""
    module, client, credentials, _, _ = runtime
    admitted = {
        ("GET", "/api/status"),
        ("GET", "/api/auth/session"), ("POST", "/api/auth/session"),
        ("DELETE", "/api/auth/session"),
        ("GET", "/project"), ("GET", "/project.js"),
        ("GET", "/api/dashboard/tasks"),
        ("GET", "/api/project/context"), ("GET", "/api/project/task-audit"),
        ("POST", "/api/done"), ("DELETE", "/api/delete"),
        ("POST", "/api/pause"), ("POST", "/api/resume"),
    }
    discovered = set()
    for route in module.app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if not path or not methods:
            continue
        # Parameterized routes are denied before FastAPI parses their arguments.
        path = path.replace("{", "fixture-").replace("}", "")
        discovered.update((method, path) for method in methods)
    unqualified = discovered - admitted
    assert unqualified, "Route inventory unexpectedly stopped exercising the guard"
    for method, path in sorted(unqualified):
        response = client.request(method, path, headers=headers(credentials, "alice"))
        assert response.status_code == 403, (method, path, response.status_code, response.text[:300])
        if method != "HEAD":
            assert response.json()["detail"]["code"] == "individual_route_unavailable"


def test_individual_profile_refuses_browser_origin_and_missing_store(runtime):
    module, client, credentials, identity, _ = runtime
    auth = {**headers(credentials, "alice"), "Origin": "http://127.0.0.1:20129"}
    assert client.get("/api/dashboard/tasks", params={"project": "alpha"}, headers=auth).status_code == 403
    identity.unlink()
    response = client.get("/api/dashboard/tasks", params={"project": "alpha"}, headers=headers(credentials, "alice"))
    assert response.status_code == 503
    assert not identity.exists()
    assert client.get("/api/status").status_code == 200


def test_individual_profile_does_not_accept_shared_token_or_generate_one_on_start(runtime, monkeypatch):
    module, client, _, _, _ = runtime
    token = module.ensure_api_token()  # Deliberately provision the old token on a fixture.
    assert client.get("/api/dashboard/tasks", params={"project": "alpha"}, headers={"Authorization": "Bearer " + token}).status_code == 401
    def shared_bootstrap():
        raise AssertionError("Individual startup must not generate shared secrets")
    monkeypatch.setattr(module, "ensure_api_token", shared_bootstrap)
    monkeypatch.setattr(module, "ensure_csrf_token", shared_bootstrap)
    import service_runtime
    monkeypatch.setattr(service_runtime, "run_managed", lambda *_, **__: None)
    monkeypatch.setattr(sys, "argv", ["dashboard_api.py"])
    module.main()


def test_identity_lookup_does_not_block_status_endpoint(runtime, monkeypatch):
    from httpx import ASGITransport, AsyncClient
    from devcore_engine.security.identity import SqliteIdentityProvider
    module, _, credentials, _, _ = runtime
    entered, release = threading.Event(), threading.Event()
    original = SqliteIdentityProvider.authorize
    def delayed(self, *args, **kwargs):
        entered.set()
        if not release.wait(5):
            raise AssertionError("Identity test was not released")
        return original(self, *args, **kwargs)
    monkeypatch.setattr(SqliteIdentityProvider, "authorize", delayed)
    async def exercise():
        async with AsyncClient(transport=ASGITransport(app=module.app), base_url="http://fixture") as client:
            pending = asyncio.create_task(client.get("/api/dashboard/tasks", params={"project": "alpha"}, headers=headers(credentials, "alice")))
            try:
                assert await asyncio.to_thread(entered.wait, 2)
                response = await asyncio.wait_for(client.get("/api/status"), 0.5)
                assert response.status_code == 200
            finally:
                release.set()
                response = await pending
            assert response.status_code == 200
    asyncio.run(exercise())


def test_individual_profile_bounds_declared_and_streamed_bodies(runtime, monkeypatch):
    _, client, credentials, _, _ = runtime
    monkeypatch.setenv("DEVCORE_MAX_REQUEST_BODY_BYTES", "64")
    auth = headers(credentials, "alice")
    assert client.post("/api/done", content=b"x" * 65, headers=auth).status_code == 413
    def chunks():
        for _ in range(4):
            yield b"x" * 32
    assert client.post("/api/done", content=chunks(), headers=auth).status_code == 413


def test_legacy_http_mutations_still_require_bearer_and_csrf(runtime, monkeypatch):
    module, client, _, _, local = runtime
    monkeypatch.setattr(module, "DASHBOARD_AUTH_PROFILE", "legacy")
    token, csrf = module.ensure_api_token(), module.ensure_csrf_token()
    body = {"project": "alpha", "id": "T-01", "expected_version": 1}
    assert client.post("/api/done", json=body).status_code == 401
    auth = {"Authorization": "Bearer " + token}
    assert client.post("/api/done", json=body, headers=auth).status_code == 403
    assert client.post("/api/done", json=body, headers={**auth, "X-CSRF-Token": "invalid"}).status_code == 403
    assert client.post("/api/done", json=body, headers={**auth, "X-CSRF-Token": csrf}).status_code == 200
    with sqlite3.connect(local / "devcore.db") as conn:
        assert conn.execute("SELECT status FROM tasks WHERE project_id='beta'").fetchone()[0] == "in_progress"


def test_local_provisioning_cli_keeps_secret_out_of_stdout_and_never_overwrites(tmp_path):
    script = Path(__file__).with_name("manage_local_identity.py")
    store, output = tmp_path / "identity.db", tmp_path / "token.json"
    def command(*args):
        return subprocess.run([sys.executable, str(script), "--store", str(store), *args], capture_output=True, text=True, timeout=15)
    assert command("init").returncode == 0
    assert command("add-user", "--user", "alice").returncode == 0
    assert command("grant", "--user", "alice", "--project", "alpha", "--role", "reader").returncode == 0
    arguments = ("issue-token", "--user", "alice", "--project", "alpha", "--action", READ, "--output", str(output))
    issued = command(*arguments)
    assert issued.returncode == 0
    token = json.loads(output.read_text())["token"]
    assert token not in issued.stdout + issued.stderr
    before = output.read_bytes()
    assert command(*arguments).returncode == 2
    assert output.read_bytes() == before
    with sqlite3.connect(store) as conn:
        assert conn.execute("SELECT COUNT(*) FROM identity_credentials").fetchone()[0] == 1
