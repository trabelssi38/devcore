from concurrent.futures import ThreadPoolExecutor
import importlib.util
from pathlib import Path
import sqlite3
import threading
import time
from types import SimpleNamespace
import warnings

import pytest
from fastapi.testclient import TestClient

from test_dashboard_individual_access import runtime
from test_dashboard_browser_sessions import ORIGIN
from devcore_engine.security import passwords
from devcore_engine.security.identity import READ, CONTEXT_READ, disable_user, issue_credential
from devcore_engine.security.browser_sessions import upgrade_session_store

PASSWORD = "Une phrase de recette uniquement"


@pytest.fixture
def password_runtime(runtime):
    module, _, credentials, identity, local = runtime
    upgrade_session_store(identity)
    passwords.upgrade_password_store(identity)
    for user in credentials:
        passwords.set_password(identity, user, PASSWORD)
    return module, identity, local


def login(client, user="alice", project="alpha", password=PASSWORD):
    return client.post("/api/auth/session", json={"user_id": user, "password": password, "project": project},
                       headers={"Origin": ORIGIN})


@pytest.mark.parametrize("method,path", [("POST", "/api/done"), ("DELETE", "/api/delete")])
def test_password_clients_keep_isolation_roles_csrf_and_reset_revocation(password_runtime, method, path):
    module, identity, local = password_runtime
    alice, bob, reader = [TestClient(module.app, base_url=ORIGIN) for _ in range(3)]
    a, b, r = login(alice), login(bob, "bob", "beta"), login(reader, "reader")
    assert a.status_code == b.status_code == r.status_code == 200
    assert a.json()["actions"] == ["task.read", "task.mutate", CONTEXT_READ]
    assert r.json()["actions"] == [READ, CONTEXT_READ]
    assert PASSWORD not in a.text
    assert "httponly" in a.headers["set-cookie"].lower()
    assert a.headers["cache-control"] == "no-store"
    assert alice.get("/api/dashboard/tasks", params={"project": "beta"}).status_code == 403
    assert bob.get("/api/dashboard/tasks", params={"project": "alpha"}).status_code == 403
    body = {"project": "alpha", "id": "T-01", "expected_version": 1}
    assert reader.request(method, path, json=body, headers={"Origin": ORIGIN, "X-CSRF-Token": r.json()["csrf_token"]}).status_code == 403
    assert alice.request(method, path, json=body, headers={"Origin": ORIGIN}).status_code == 403
    assert alice.request(method, path, json=body, headers={"Origin": ORIGIN, "X-CSRF-Token": a.json()["csrf_token"]}).status_code == 200
    passwords.set_password(identity, "alice", "Une nouvelle phrase de recette")
    assert alice.get("/api/auth/session").status_code == 401
    assert bob.get("/api/dashboard/tasks", params={"project": "beta"}).status_code == 200
    with sqlite3.connect(local / "devcore.db") as conn:
        assert conn.execute("SELECT status,version FROM tasks WHERE project_id='beta'").fetchone() == ("in_progress", 1)


def test_bad_unknown_and_disabled_credentials_share_generic_error_and_project_is_server_checked(password_runtime):
    module, identity, _ = password_runtime
    client = TestClient(module.app, base_url=ORIGIN)
    failures = [login(client, password="wrong"), login(client, user="unknown")]
    disable_user(identity, "bob")
    failures.append(login(client, "bob", "beta"))
    assert all(response.status_code == 401 for response in failures)
    assert all(response.json() == {"detail": "Invalid credentials or session"} for response in failures)
    assert login(client, project="beta").status_code == 403
    assert client.get("/api/auth/session").status_code == 401


def test_bearer_exchange_still_works_on_v3_but_mixed_methods_are_refused(password_runtime):
    module, identity, _ = password_runtime
    client = TestClient(module.app, base_url=ORIGIN)
    _, token = issue_credential(identity, "alice", ["alpha"], [READ])
    headers = {"Origin": ORIGIN, "Authorization": "Bearer " + token}
    response = client.post("/api/auth/session", json={"project": "alpha"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["actions"] == [READ]
    mixed = client.post("/api/auth/session", json={"project": "alpha", "user_id": "alice", "password": PASSWORD}, headers=headers)
    assert mixed.status_code == 400


def test_password_exchange_needs_explicit_upgrade_trusted_origin_and_bounded_body(runtime, monkeypatch):
    module, _, _, identity, _ = runtime
    upgrade_session_store(identity)
    client = TestClient(module.app, base_url=ORIGIN)
    assert login(client).status_code == 503
    assert client.post("/api/auth/session", json={"user_id": "alice", "password": PASSWORD, "project": "alpha"}).status_code == 403
    assert client.post("/api/auth/session", json={"user_id": "alice", "password": PASSWORD, "project": "alpha"}, headers={"Origin": "https://evil.test"}).status_code == 403
    monkeypatch.setenv("DEVCORE_MAX_REQUEST_BODY_BYTES", "64")
    assert client.post("/api/auth/session", content=b"x" * 65, headers={"Origin": ORIGIN}).status_code == 413
    with sqlite3.connect(identity) as conn:
        assert conn.execute("SELECT version FROM identity_schema").fetchone()[0] == 2


def test_two_inflight_password_verifications_bound_capacity_and_leave_status_responsive(password_runtime, monkeypatch):
    module, _, _ = password_runtime
    entered, release = threading.Barrier(3), threading.Event()
    original = passwords.verify_password
    def slow_verify(encoded, password):
        entered.wait(timeout=10)
        if not release.wait(timeout=10):
            raise AssertionError("Verification gate timed out")
        return original(encoded, password)
    monkeypatch.setattr(passwords, "verify_password", slow_verify)
    clients = [TestClient(module.app, base_url=ORIGIN) for _ in range(3)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending = [pool.submit(login, clients[0]), pool.submit(login, clients[1], "bob", "beta")]
        try:
            entered.wait(timeout=10)
            started = time.monotonic()
            status = clients[2].get("/api/status")
            assert status.status_code == 200
            assert time.monotonic() - started < .5
            saturated = login(clients[2], "reader")
            assert saturated.status_code == 429
            assert saturated.headers["retry-after"] == "1"
        finally:
            release.set()
        assert [future.result(timeout=10).status_code for future in pending] == [200, 200]


def test_local_recovery_cli_masks_input_reports_no_secret_and_refuses_echo_fallback(password_runtime, monkeypatch, capsys):
    _, identity, _ = password_runtime
    spec = importlib.util.spec_from_file_location("local_identity_cli_password_test", Path(__file__).with_name("manage_local_identity.py"))
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    monkeypatch.setattr(cli.sys, "stdin", SimpleNamespace(isatty=lambda: True))
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt: "Une phrase issue du terminal")
    cli.main(["--store", str(identity), "reset-password", "--user", "alice"])
    assert "success" in capsys.readouterr().out
    session, _ = passwords.create_password_session(identity, "alice", "Une phrase issue du terminal", "alpha", ORIGIN)
    assert session.principal.user_id == "alice"
    with sqlite3.connect(identity) as conn:
        before = conn.execute("SELECT password_hash FROM identity_passwords WHERE user_id='alice'").fetchone()[0]
    def fallback(prompt):
        warnings.warn("Input would be echoed", cli.getpass.GetPassWarning)
    monkeypatch.setattr(cli.getpass, "getpass", fallback)
    with pytest.raises(cli.getpass.GetPassWarning):
        cli.main(["--store", str(identity), "reset-password", "--user", "alice"])
    monkeypatch.setattr(cli.sys, "stdin", SimpleNamespace(isatty=lambda: False))
    with pytest.raises(ValueError):
        cli.main(["--store", str(identity), "reset-password", "--user", "alice"])
    with sqlite3.connect(identity) as conn:
        assert conn.execute("SELECT password_hash FROM identity_passwords WHERE user_id='alice'").fetchone()[0] == before
    assert "Une phrase issue du terminal" not in capsys.readouterr().out
