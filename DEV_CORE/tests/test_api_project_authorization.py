"""Comprehensive qualification test suite for Lot L4:
Server-side project authorization, principal admission, role matrix,
audit log author attribution without secrets, and browser sessions on API Gateway.

Strictly follows:
- Temporary isolated roots (DEVCORE_LOCAL_ROOT, DEVCORE_DATA_ROOT).
- Zero production data, Dropbox, or live index fixtures.
- Pure Python 3.13 verification.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

DEVCORE_DIR = Path(__file__).resolve().parents[1]
if str(DEVCORE_DIR / "API") not in sys.path:
    sys.path.insert(0, str(DEVCORE_DIR / "API"))
if str(DEVCORE_DIR) not in sys.path:
    sys.path.insert(0, str(DEVCORE_DIR))

from devcore_api import create_app
from devcore_api.ports import SqliteTaskRepository
from devcore_engine.db import init_db
from devcore_engine.security.identity import (
    AUDIT_READ,
    CONTEXT_READ,
    READ,
    WRITE,
    add_user,
    initialize_store,
    issue_credential,
    revoke_credential,
    set_membership,
)
from devcore_engine.security.browser_sessions import upgrade_session_store
from devcore_engine.persistence.rls import build_application_role_grants, build_rls_ddl


@pytest.fixture
def auth_env(tmp_path, monkeypatch):
    """Setup an isolated environment with two projects, identity store, and sqlite db."""
    local_root = tmp_path / "local"
    data_root = tmp_path / "data"
    local_root.mkdir()
    data_root.mkdir()
    security_dir = local_root / "Security"
    security_dir.mkdir()

    identity_db = security_dir / "identity.db"
    initialize_store(identity_db)
    upgrade_session_store(identity_db)

    # Provision users and roles
    # Alice: owner of alpha (read, write, audit_read, context_read)
    add_user(identity_db, "alice")
    set_membership(identity_db, "alice", "alpha", "owner")
    alice_cred_id, alice_token = issue_credential(
        identity_db, "alice", ["alpha"], [READ, WRITE, AUDIT_READ, CONTEXT_READ]
    )

    # Bob: contributor in beta only (read, write, context_read)
    add_user(identity_db, "bob")
    set_membership(identity_db, "bob", "beta", "contributor")
    bob_cred_id, bob_token = issue_credential(
        identity_db, "bob", ["beta"], [READ, WRITE, CONTEXT_READ]
    )

    # Charlie: reader in alpha only (read, context_read)
    add_user(identity_db, "charlie")
    set_membership(identity_db, "charlie", "alpha", "reader")
    charlie_cred_id, charlie_token = issue_credential(
        identity_db, "charlie", ["alpha"], [READ, CONTEXT_READ]
    )

    # Provision domain task database
    db_path = local_root / "devcore.db"
    conn = init_db(db_path)
    for p in ("alpha", "beta"):
        conn.execute("INSERT OR IGNORE INTO projects(id, name, root_path) VALUES (?, ?, '.')", (p, p))
    # Tasks with versioning
    conn.execute(
        "INSERT INTO tasks(id, project_id, title, status, version) VALUES ('T-01', 'alpha', 'Task in alpha', 'in_progress', 1)"
    )
    conn.execute(
        "INSERT INTO tasks(id, project_id, title, status, version) VALUES ('T-02', 'beta', 'Task in beta', 'in_progress', 1)"
    )
    conn.commit()
    conn.close()

    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(local_root))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(data_root))
    monkeypatch.setenv("DEVCORE_SQLITE_DB_PATH", str(db_path))
    monkeypatch.setenv("DEVCORE_IDENTITY_STORE", str(identity_db))
    monkeypatch.setenv("DEVCORE_REQUIRE_AUTH", "1")

    repo = SqliteTaskRepository(db_path=db_path)
    app = create_app(task_repository=repo, require_auth=True)
    origin = "http://127.0.0.1:20131"
    client = TestClient(app, base_url=origin)

    return {
        "client": client,
        "app": app,
        "identity_db": identity_db,
        "db_path": db_path,
        "local_root": local_root,
        "credentials": {
            "alice": {"id": alice_cred_id, "token": alice_token},
            "bob": {"id": bob_cred_id, "token": bob_token},
            "charlie": {"id": charlie_cred_id, "token": charlie_token},
        },
    }


def test_public_routes_remain_open_without_auth(auth_env):
    """Health, contracts, and routes catalogs do not require project authentication."""
    client = auth_env["client"]
    assert client.get("/api/v1/health").status_code == 200
    assert client.get("/api/v1/contracts").status_code == 200
    assert client.get("/api/v1/routes").status_code == 200


def test_missing_credentials_rejected_with_401(auth_env):
    """Unauthenticated calls to project resources are rejected with 401."""
    client = auth_env["client"]
    resp = client.get("/api/v1/tasks", params={"project": "alpha"})
    assert resp.status_code == 401
    assert resp.headers.get("WWW-Authenticate") == "Bearer"
    assert resp.json()["code"] == "individual_credential_required"

    # POST mutation without credentials
    post_resp = client.post("/api/v1/tasks/done", json={"project": "alpha", "id": "T-01", "expected_version": 1})
    assert post_resp.status_code == 401
    assert post_resp.headers.get("WWW-Authenticate") == "Bearer"


def test_cross_project_access_denied_with_403(auth_env):
    """A user cannot access or mutate tasks in a project they do not belong to (Item 475)."""
    client = auth_env["client"]
    alice_header = {"Authorization": f"Bearer {auth_env['credentials']['alice']['token']}"}

    # Alice has access to alpha
    resp_alpha = client.get("/api/v1/tasks", params={"project": "alpha"}, headers=alice_header)
    assert resp_alpha.status_code == 200
    assert len(resp_alpha.json()["tasks"]) == 1

    # Alice attempts to access beta -> 403 Forbidden
    resp_beta = client.get("/api/v1/tasks", params={"project": "beta"}, headers=alice_header)
    assert resp_beta.status_code == 403
    assert resp_beta.json()["code"] == "project_access_denied"

    # Alice attempts to mutate task in beta -> 403 Forbidden
    mutate_beta = client.post(
        "/api/v1/tasks/done",
        json={"project": "beta", "id": "T-02", "expected_version": 1},
        headers=alice_header,
    )
    assert mutate_beta.status_code == 403
    assert mutate_beta.json()["code"] == "project_access_denied"

    # Bob has access to beta
    bob_header = {"Authorization": f"Bearer {auth_env['credentials']['bob']['token']}"}
    bob_beta = client.get("/api/v1/tasks", params={"project": "beta"}, headers=bob_header)
    assert bob_beta.status_code == 200
    assert len(bob_beta.json()["tasks"]) == 1

    # Bob attempts to access alpha -> 403 Forbidden
    bob_alpha = client.get("/api/v1/tasks", params={"project": "alpha"}, headers=bob_header)
    assert bob_alpha.status_code == 403


def test_gemini_route_requires_project_mutation_access(auth_env, monkeypatch):
    """A project-scoped Gemini call cannot bypass identity or role checks."""
    monkeypatch.delenv("DEVCORE_DATABASE_URL", raising=False)
    monkeypatch.delenv("DEVCORE_TASK_READ_MODE", raising=False)
    client = auth_env["client"]
    route = "/api/v1/llm/gemini"
    prompt = {"project": "alpha", "prompt": "Reply with OK."}
    assert client.post(route, json=prompt).status_code == 401
    reader = {"Authorization": f"Bearer {auth_env['credentials']['charlie']['token']}"}
    assert client.post(route, json=prompt, headers=reader).status_code == 403
    owner = {"Authorization": f"Bearer {auth_env['credentials']['alice']['token']}"}
    assert client.post(route, json={"project": "beta", "prompt": "Reply with OK."},
                       headers=owner).status_code == 403
    assert client.post(route, json=prompt, headers=owner).status_code == 503


def test_role_matrix_enforcement(auth_env):
    """Readers can query tasks but cannot mutate them."""
    client = auth_env["client"]
    charlie_header = {"Authorization": f"Bearer {auth_env['credentials']['charlie']['token']}"}

    # Charlie is a reader in alpha: task.read is allowed
    read_resp = client.get("/api/v1/tasks", params={"project": "alpha"}, headers=charlie_header)
    assert read_resp.status_code == 200

    # Charlie attempts mutation: task.mutate is forbidden for reader -> 403
    mutate_resp = client.post(
        "/api/v1/tasks/done",
        json={"project": "alpha", "id": "T-01", "expected_version": 1},
        headers=charlie_header,
    )
    assert mutate_resp.status_code == 403
    assert mutate_resp.json()["code"] == "project_access_denied"


def test_mutation_audit_author_attribution_without_secrets(auth_env):
    """Mutations record authenticated author in audit_log without logging secrets (Item 479)."""
    client = auth_env["client"]
    db_path = auth_env["db_path"]
    alice_header = {"Authorization": f"Bearer {auth_env['credentials']['alice']['token']}"}

    # Alice pauses T-01
    pause_resp = client.post(
        "/api/v1/tasks/pause",
        json={"project": "alpha", "id": "T-01", "expected_version": 1},
        headers=alice_header,
    )
    assert pause_resp.status_code == 200
    assert pause_resp.headers.get("Cache-Control") == "no-store"

    # Inspect database directly
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        # Check task version bumped to 2
        task_row = conn.execute("SELECT status, version FROM tasks WHERE id = 'T-01'").fetchone()
        assert task_row["status"] == "paused"
        assert task_row["version"] == 2

        # Check audit_log
        audit_row = conn.execute(
            "SELECT * FROM audit_log WHERE project_id = 'alpha' AND task_id = 'T-01' ORDER BY created_at DESC"
        ).fetchone()
        assert audit_row is not None
        assert audit_row["actor"] == "alice"  # Authenticated caller
        assert audit_row["action"] == "task.pause"

        details = json.loads(audit_row["details"])
        assert details["schema_version"] == 1
        assert details["before"]["status"] == "in_progress"
        assert details["before"]["version"] == 1
        assert details["after"]["status"] == "paused"
        assert details["after"]["version"] == 2

        # Verify no token or secret is present anywhere in details
        details_str = json.dumps(details)
        assert auth_env["credentials"]["alice"]["token"] not in details_str
        assert "password" not in details_str


def test_optimistic_locking_conflict(auth_env):
    """Mutations with stale expected_version return 409 Conflict."""
    client = auth_env["client"]
    alice_header = {"Authorization": f"Bearer {auth_env['credentials']['alice']['token']}"}

    # Version in DB is 1; Alice sends expected_version 999
    conflict_resp = client.post(
        "/api/v1/tasks/done",
        json={"project": "alpha", "id": "T-01", "expected_version": 999},
        headers=alice_header,
    )
    assert conflict_resp.status_code == 409
    assert conflict_resp.json()["code"] == "stale_task_version"


def test_revocation_immediately_blocks_access(auth_env):
    """Revoking a credential immediately returns 401 on next request."""
    client = auth_env["client"]
    identity_db = auth_env["identity_db"]
    alice_cred = auth_env["credentials"]["alice"]
    alice_header = {"Authorization": f"Bearer {alice_cred['token']}"}

    # Works before revocation
    assert client.get("/api/v1/tasks", params={"project": "alpha"}, headers=alice_header).status_code == 200

    # Revoke
    revoke_credential(identity_db, alice_cred["id"])

    # Blocked immediately
    revoked_resp = client.get("/api/v1/tasks", params={"project": "alpha"}, headers=alice_header)
    assert revoked_resp.status_code == 401
    assert revoked_resp.json()["code"] == "invalid_individual_credential"


def test_browser_session_creation_cookie_and_csrf(auth_env):
    """Browser session lifecycle with HttpOnly cookie, origin check, and CSRF token (Item 477)."""
    client = auth_env["client"]
    alice_token = auth_env["credentials"]["alice"]["token"]

    # 1. Login via Bearer token to get browser session
    login_resp = client.post(
        "/api/v1/auth/session",
        json={"project": "alpha"},
        headers={"Authorization": f"Bearer {alice_token}", "Origin": "http://127.0.0.1:20131"},
    )
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert login_data["user_id"] == "alice"
    assert login_data["project"] == "alpha"
    assert "csrf_token" in login_data
    csrf_token = login_data["csrf_token"]
    assert "devcore_session" in login_resp.cookies
    session_cookie = login_resp.cookies["devcore_session"]

    # 2. Access task list using session cookie
    cookie_header = {"Cookie": f"devcore_session={session_cookie}"}
    read_resp = client.get("/api/v1/tasks", params={"project": "alpha"}, headers=cookie_header)
    assert read_resp.status_code == 200

    # 3. Mutation using session cookie without CSRF token -> 403 Forbidden
    mutate_no_csrf = client.post(
        "/api/v1/tasks/done",
        json={"project": "alpha", "id": "T-01", "expected_version": 1},
        headers={**cookie_header, "Origin": "http://127.0.0.1:20131"},
    )
    assert mutate_no_csrf.status_code == 403

    # 4. Mutation using session cookie with valid CSRF token -> 200 OK
    mutate_with_csrf = client.post(
        "/api/v1/tasks/done",
        json={"project": "alpha", "id": "T-01", "expected_version": 1},
        headers={
            **cookie_header,
            "Origin": "http://127.0.0.1:20131",
            "X-CSRF-Token": csrf_token,
        },
    )
    assert mutate_with_csrf.status_code == 200

    # 5. Logout deletes cookie
    logout_resp = client.delete(
        "/api/v1/auth/session",
        headers={
            **cookie_header,
            "Origin": "http://127.0.0.1:20131",
            "X-CSRF-Token": csrf_token,
        },
    )
    assert logout_resp.status_code == 200


def test_rls_application_role_grants_ddl_item_478():
    """Verify application role DDL satisfies Item 478 constraints."""
    grants = build_application_role_grants("devcore_app")
    full_ddl = "\n".join(grants)
    assert "NOBYPASSRLS" in full_ddl
    assert "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO devcore_app" in full_ddl
    assert "NOSUPERUSER" in full_ddl


def test_project_parameter_divergence_rejected(auth_env):
    """P0 isolation: query project and body project mismatch MUST be rejected with 400 project_mismatch."""
    alice_token = auth_env["credentials"]["alice"]["token"]
    client = auth_env["client"]

    # 1. Runs submission: query=alpha vs body=beta -> 400 project_mismatch
    resp_run = client.post(
        "/api/v1/runs?project=alpha",
        json={"project_id": "beta", "title": "Sneak run into beta", "command": ["echo", "test"]},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert resp_run.status_code == 400
    assert resp_run.json()["detail"]["code"] == "project_mismatch"

    # 2. Task completion: query=alpha vs body=beta -> 400 project_mismatch
    resp_task_done = client.post(
        "/api/v1/tasks/done?project=alpha",
        json={"project": "beta", "id": "T-02", "expected_version": 1},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert resp_task_done.status_code == 400
    assert resp_task_done.json()["error"]["code"] == "project_mismatch"

    # 3. Task pause: query=alpha vs body=beta -> 400 project_mismatch
    resp_task_pause = client.post(
        "/api/v1/tasks/pause?project=alpha",
        json={"project": "beta", "id": "T-02", "expected_version": 1},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert resp_task_pause.status_code == 400
    assert resp_task_pause.json()["error"]["code"] == "project_mismatch"

    # 4. Token for alpha only attempting to mutate beta without query divergence -> 403 Forbidden
    resp_direct_beta = client.post(
        "/api/v1/runs",
        json={"project_id": "beta", "title": "Run in beta", "command": ["echo", "test"]},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert resp_direct_beta.status_code == 403


def test_run_step_execution_endpoint(auth_env):
    """P1 execution: verify POST /api/v1/runs/step executes queued runs."""
    alice_token = auth_env["credentials"]["alice"]["token"]
    client = auth_env["client"]

    # Submit run for alpha
    submit_resp = client.post(
        "/api/v1/runs?project=alpha",
        json={"project_id": "alpha", "title": "Quick step run", "command": [sys.executable, "-c", "print('stepped')"]},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert submit_resp.status_code == 202
    run_id = submit_resp.json()["run_id"]

    # Trigger step endpoint
    step_resp = client.post("/api/v1/runs/step?project=alpha", headers={"Authorization": f"Bearer {alice_token}"})
    assert step_resp.status_code == 200
    step_data = step_resp.json()
    assert step_data is not None
    assert step_data["run_id"] == run_id
    assert step_data["status"] == "succeeded"


def test_run_step_cross_project_isolation(auth_env):
    """P0 isolation: stepping alpha MUST NEVER execute or return a beta run."""
    alice_token = auth_env["credentials"]["alice"]["token"]
    bob_token = auth_env["credentials"]["bob"]["token"]
    client = auth_env["client"]

    # Bob submits a run for beta
    submit_beta = client.post(
        "/api/v1/runs?project=beta",
        json={"project_id": "beta", "title": "Beta sensitive run", "command": [sys.executable, "-c", "print('beta ran')"]},
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert submit_beta.status_code == 202
    beta_run_id = submit_beta.json()["run_id"]

    # Alice (authorized only for alpha) calls /runs/step?project=alpha
    step_alpha = client.post(
        "/api/v1/runs/step?project=alpha",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert step_alpha.status_code == 200
    assert step_alpha.json() is None  # No alpha runs queued!

    # Verify that beta run was NOT touched and remains queued
    beta_get = client.get(
        f"/api/v1/runs/{beta_run_id}?project=beta",
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert beta_get.status_code == 200
    assert beta_get.json()["status"] == "queued"

    # Alice attempts to call /runs/step?project=beta -> 403 Forbidden
    step_unauth = client.post(
        "/api/v1/runs/step?project=beta",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert step_unauth.status_code == 403

    # Finally Bob steps beta -> succeeds
    step_bob = client.post(
        "/api/v1/runs/step?project=beta",
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert step_bob.status_code == 200
    assert step_bob.json()["run_id"] == beta_run_id
    assert step_bob.json()["status"] == "succeeded"


def test_postgres_browser_cookie_uses_postgres_identity_without_sqlite_fallback(auth_env, monkeypatch):
    """The team gateway must authorize a PostgreSQL cookie on every scoped route."""
    import importlib
    from devcore_engine.security.browser_sessions import BrowserSession
    from devcore_engine.security.identity import Principal, ProjectAccessDenied

    api_module = importlib.import_module("devcore_api.app")
    postgres_sessions = importlib.import_module("devcore_engine.security.postgres_browser_sessions")
    sqlite_sessions = importlib.import_module("devcore_engine.security.browser_sessions")
    dsn = "postgresql://unused/isolated_fixture"
    monkeypatch.setenv("DEVCORE_IDENTITY_READ_MODE", "postgres")
    monkeypatch.setenv("DEVCORE_DATABASE_URL", dsn)
    monkeypatch.setattr(api_module, "resolve_identity_store_path", lambda: None)

    calls = []

    def authorize(source, secret, project, action, origin, *, csrf=None, mutate=False):
        calls.append((source, secret, project, action, origin, csrf, mutate))
        if project != "alpha" or (mutate and csrf != "csrf-ok"):
            raise ProjectAccessDenied("Project action denied")
        return BrowserSession(Principal("alice", "pg-session", project, action),
                              "pg-session", project, time.time() + 60, (READ, WRITE))

    def sqlite_fallback(*args, **kwargs):
        raise AssertionError("SQLite session adapter must not be used in PostgreSQL mode")

    monkeypatch.setattr(postgres_sessions, "authorize_session", authorize)
    monkeypatch.setattr(sqlite_sessions, "authorize_session", sqlite_fallback)
    client = auth_env["client"]
    client.cookies.set("devcore_session", "fixture-cookie")

    assert client.get("/api/v1/tasks", params={"project": "alpha"}).status_code == 200
    assert client.get("/api/v1/tasks", params={"project": "beta"}).status_code == 403
    blocked = client.post("/api/v1/tasks/pause", json={"project": "alpha", "id": "T-01", "expected_version": 1},
                          headers={"Origin": "http://127.0.0.1:20131", "X-CSRF-Token": "wrong"})
    assert blocked.status_code == 403
    allowed = client.post("/api/v1/tasks/pause", json={"project": "alpha", "id": "T-01", "expected_version": 1},
                          headers={"Origin": "http://127.0.0.1:20131", "X-CSRF-Token": "csrf-ok"})
    assert allowed.status_code == 200
    assert all(call[0:2] == (dsn, "fixture-cookie") for call in calls)
    assert calls[-1][3:] == (WRITE, "http://127.0.0.1:20131", "csrf-ok", True)


