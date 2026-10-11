"""Individual context access never uses a client directory or global memory."""

import asyncio
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import threading

from fastapi.testclient import TestClient
import pytest

from test_dashboard_individual_access import runtime, headers
from devcore_engine.security.identity import (
    CONTEXT_READ, READ, disable_user, issue_credential, remove_membership,
    revoke_credential, set_membership,
)
from devcore_engine.security.browser_sessions import upgrade_session_store
from devcore_engine.services import registered_project_context as adapter

ORIGIN = "http://127.0.0.1:20129"
URL = "/api/project/context"


def write_context(directory, project):
    directory.mkdir(parents=True)
    card = directory / "card.md"
    card.write_text(f"# Projet {project}\nDécisions privées de {project}.\n", encoding="utf-8")
    def decision(identifier, status, required, replaces=(), tags=()):
        return {"id": identifier, "status": status, "required": required,
                "decision": f"Direction {project} {identifier}", "rationale": "Recette isolée",
                "validation": "Fixture", "sources": ["plan.md"],
                "tags": list(tags), "replaces": list(replaces)}
    manifest = {"schema_version": 1, "project": project, "reviewed_at": "2026-10-03",
                "card": card.name, "card_sha256": hashlib.sha256(card.read_bytes()).hexdigest(),
                "decisions": [decision("old", "superseded", False),
                              decision("local", "effective", True, replaces=["old"]),
                              decision("worker", "proposed", False, tags=["worker"])]}
    (directory / "context.json").write_text(json.dumps(manifest), encoding="utf-8")
    return manifest


@pytest.fixture
def context_runtime(runtime, tmp_path):
    module, client, credentials, identity, local = runtime
    repositories, tokens = {}, {}
    with closing(sqlite3.connect(local / "devcore.db")) as conn, conn:
        conn.execute("PRAGMA journal_mode=DELETE")
        for project, user in (("alpha", "alice"), ("beta", "bob")):
            root = tmp_path / (project + "-repository")
            write_context(root / "docs" / "project-context", project)
            repositories[project] = root
            conn.execute("UPDATE projects SET root_path=? WHERE id=?", (str(root), project))
            tokens[user] = issue_credential(identity, user, [project], [CONTEXT_READ])
    tokens["reader"] = issue_credential(identity, "reader", ["alpha"], [CONTEXT_READ])
    return module, client, credentials, identity, local, repositories, tokens


def test_explicit_capability_project_isolation_and_exact_body_budget(context_runtime):
    _, client, existing, identity, local, repositories, tokens = context_runtime
    original_db = (local / "devcore.db").read_bytes()
    original_cards = {p: p.read_bytes() for root in repositories.values() for p in root.rglob("*.md")}
    for user, project in (("alice", "alpha"), ("bob", "beta"), ("reader", "alpha")):
        response = client.get(URL, params={"project": project}, headers=headers(tokens, user))
        assert response.status_code == 200
        result = response.json()
        assert result["project"] == project and f"privées de {project}" in result["card"]
        assert result["measurement"]["used"] == len(response.content)
        assert len(response.content) <= result["measurement"]["budget"] == 12000
        assert response.content.endswith(b"\n")
        assert int(response.headers["content-length"]) == len(response.content)
        assert response.headers["cache-control"] == "no-store"
        assert result["measurement"]["model_tokens_measured"] is False
        assert [d["id"] for d in result["decisions"]] == ["local"]
        assert result["excluded_superseded"] == ["old"]
        assert result["omitted"] == [{"id": "worker", "reason": "not_relevant"}]
    assert client.get(URL, params={"project": "beta"}, headers=headers(tokens, "alice")).status_code == 403
    assert client.get(URL, params={"project": "alpha"}, headers=headers(existing, "alice")).status_code == 403
    set_membership(identity, "alice", "alpha", "owner")
    assert client.get(URL, params={"project": "alpha"}, headers=headers(existing, "alice")).status_code == 403
    assert client.get("/api/dashboard/tasks", params={"project": "alpha"}, headers=headers(tokens, "alice")).status_code == 403
    assert (local / "devcore.db").read_bytes() == original_db
    assert all(p.read_bytes() == data for p, data in original_cards.items())


def test_denial_happens_before_context_adapter_and_legacy_memory_stays_closed(context_runtime, monkeypatch):
    _, client, existing, _, _, _, tokens = context_runtime
    def forbidden(*args, **kwargs):
        raise AssertionError("Denied request accessed project metadata")
    monkeypatch.setattr(adapter, "load_registered_project_context", forbidden)
    assert client.get(URL, params={"project": "alpha"}).status_code == 401
    assert client.get(URL, params={"project": "beta"}, headers=headers(tokens, "alice")).status_code == 403
    assert client.get(URL, params={"project": "alpha"}, headers=headers(existing, "alice")).status_code == 403
    assert client.get(URL, headers=headers(tokens, "alice")).status_code == 400
    assert client.get(URL, params={"project": "../beta"}, headers=headers(tokens, "alice")).status_code == 400
    assert client.get("/api/memory/search", params={"project": "alpha"}, headers=headers(tokens, "alice")).status_code == 403


@pytest.mark.parametrize("change,status", [("revoke", 401), ("disable", 401), ("remove", 403)])
def test_context_authorization_rechecks_current_identity(context_runtime, change, status):
    _, client, _, identity, _, _, tokens = context_runtime
    auth = headers(tokens, "alice")
    assert client.get(URL, params={"project": "alpha"}, headers=auth).status_code == 200
    if change == "revoke":
        revoke_credential(identity, tokens["alice"][0])
    elif change == "disable":
        disable_user(identity, "alice")
    else:
        remove_membership(identity, "alice", "alpha")
    assert client.get(URL, params={"project": "alpha"}, headers=auth).status_code == status


def test_query_budget_errors_and_freshness_have_no_partial_fallback(context_runtime, monkeypatch):
    module, client, _, _, _, repositories, tokens = context_runtime
    params, auth = {"project": "alpha", "query": "worker"}, headers(tokens, "alice")
    complete = client.get(URL, params=params, headers=auth)
    assert complete.status_code == 200
    assert complete.json()["decisions"][-1]["status"] == "proposed"
    small = client.get(URL, params={**params, "budget_bytes": 256}, headers=auth)
    assert small.status_code == 413 and "no partial context" in small.text
    assert "privées" not in small.text and "card" not in small.json()
    for invalid in (255, 65537, 12001, "bad"):
        assert client.get(URL, params={**params, "budget_bytes": invalid}, headers=auth).status_code == 422
    assert client.get(URL, params={**params, "query": "x" * 4097}, headers=auth).status_code == 422
    monkeypatch.setattr(module, "HTTP_CONTEXT_MAX_BYTES", 4000)
    default = client.get(URL, params={"project": "alpha"}, headers=auth)
    assert default.status_code == 200 and default.json()["measurement"]["budget"] == 4000
    assert client.get(URL, params={**params, "budget_bytes": 4001}, headers=auth).status_code == 422
    directory = repositories["alpha"] / "docs" / "project-context"
    (directory / "card.md").write_text("Changed private alpha card", encoding="utf-8")
    path = directory / "context.json"
    manifest = json.loads(path.read_text())
    manifest["reviewed_at"] = "2000-01-01"
    path.write_text(json.dumps(manifest))
    result = client.get(URL, params={"project": "alpha"}, headers=auth).json()
    assert result["warnings"] == ["card_changed_since_review", "context_review_expired"]


@pytest.mark.parametrize("damage", ["missing", "mismatch", "invalid", "escape"])
def test_invalid_context_fails_without_paths_or_foreign_content(context_runtime, damage):
    _, client, _, _, _, repositories, tokens = context_runtime
    directory = repositories["alpha"] / "docs" / "project-context"
    path = directory / "context.json"
    manifest = json.loads(path.read_text())
    if damage == "missing":
        path.unlink()
    elif damage == "mismatch":
        manifest["project"] = "beta"
        (directory / "card.md").write_text("SECRET BETA CONTEXT")
        path.write_text(json.dumps(manifest))
    elif damage == "invalid":
        path.write_text("not JSON")
    else:
        manifest["card"] = "../outside.md"
        path.write_text(json.dumps(manifest))
    response = client.get(URL, params={"project": "alpha"}, headers=headers(tokens, "alice"))
    assert response.status_code == 503
    assert response.json() == {"detail": "Registered project context unavailable"}
    assert str(directory) not in response.text and "BETA" not in response.text


@pytest.mark.parametrize("root", ["relative", "missing", "unregistered"])
def test_only_existing_absolute_registered_roots_are_admitted(context_runtime, root):
    _, client, _, _, local, repositories, tokens = context_runtime
    with closing(sqlite3.connect(local / "devcore.db")) as conn, conn:
        if root == "unregistered":
            conn.execute("DELETE FROM tasks WHERE project_id='alpha'")
            conn.execute("DELETE FROM projects WHERE id='alpha'")
        else:
            selected = "." if root == "relative" else str(repositories["alpha"] / "missing")
            conn.execute("UPDATE projects SET root_path=? WHERE id='alpha'", (selected,))
    response = client.get(URL, params={"project": "alpha", "directory": str(repositories["beta"])},
                          headers=headers(tokens, "alice"))
    assert response.status_code == 503 and "beta" not in response.text


def test_missing_database_is_not_created(context_runtime):
    _, client, _, _, local, _, tokens = context_runtime
    path = local / "devcore.db"
    path.unlink()
    assert client.get(URL, params={"project": "alpha"}, headers=headers(tokens, "alice")).status_code == 503
    assert not path.exists()


def test_context_registration_reads_committed_wal_without_checkpointing(context_runtime, tmp_path):
    _, client, _, _, local, _, tokens = context_runtime
    root = tmp_path / "committed-wal-repository"
    directory = root / "docs" / "project-context"
    manifest = write_context(directory, "alpha")
    card = directory / "card.md"
    card.write_text("Unique committed WAL context for alpha", encoding="utf-8")
    manifest["card_sha256"] = hashlib.sha256(card.read_bytes()).hexdigest()
    (directory / "context.json").write_text(json.dumps(manifest))
    path = local / "devcore.db"
    with closing(sqlite3.connect(path)) as writer:
        assert writer.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
        writer.execute("UPDATE projects SET root_path=? WHERE id='alpha'", (str(root),))
        writer.commit()
        wal = Path(str(path) + "-wal")
        original_db, original_wal = path.read_bytes(), wal.read_bytes()
        assert len(original_wal) > 32
        response = client.get(URL, params={"project": "alpha"}, headers=headers(tokens, "alice"))
        assert response.status_code == 200
        assert response.json()["card"] == "Unique committed WAL context for alpha"
        assert response.json()["warnings"] == []
        assert path.read_bytes() == original_db and wal.read_bytes() == original_wal


def test_context_directory_junction_cannot_escape_registered_root(context_runtime):
    import subprocess
    _, client, _, _, _, repositories, tokens = context_runtime
    root = repositories["alpha"]
    (root / "docs").rename(root / "saved-docs")
    target = repositories["beta"] / "docs"
    if __import__("os").name == "nt":
        # Constant fixture paths passed as argv; no deletion of junction targets.
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(root / "docs"), str(target)], capture_output=True)
        assert result.returncode == 0, result.stderr
    else:
        (root / "docs").symlink_to(target, target_is_directory=True)
    response = client.get(URL, params={"project": "alpha"}, headers=headers(tokens, "alice"))
    assert response.status_code == 503 and "beta" not in response.text


def test_cookie_context_is_project_bound_origin_checked_and_revocable(context_runtime):
    from devcore_engine.security import passwords
    module, _, _, identity, _, _, _ = context_runtime
    upgrade_session_store(identity)
    passwords.upgrade_password_store(identity)
    password = "Recette uniquement pour le contexte"
    passwords.set_password(identity, "reader", password)
    client = TestClient(module.app, base_url=ORIGIN)
    login = client.post("/api/auth/session", json={"user_id": "reader", "password": password, "project": "alpha"},
                        headers={"Origin": ORIGIN})
    assert login.status_code == 200 and login.json()["actions"] == [READ, CONTEXT_READ]
    assert client.get(URL, params={"project": "alpha"}).status_code == 200
    assert client.get(URL, params={"project": "beta"}).status_code == 403
    assert client.get(URL, params={"project": "alpha"}, headers={"Origin": "https://evil.test"}).status_code == 403
    passwords.set_password(identity, "reader", "Nouvelle phrase de recette du contexte")
    assert client.get(URL, params={"project": "alpha"}).status_code == 401


def test_old_bearer_cookie_does_not_gain_context_access(context_runtime):
    module, _, existing, identity, _, _, tokens = context_runtime
    upgrade_session_store(identity)
    client = TestClient(module.app, base_url=ORIGIN)
    exchanged = client.post("/api/auth/session", json={"project": "alpha"},
                            headers={**headers(existing, "alice"), "Origin": ORIGIN})
    assert exchanged.status_code == 200 and CONTEXT_READ not in exchanged.json()["actions"]
    assert client.get(URL, params={"project": "alpha"}).status_code == 403
    assert client.get(URL, params={"project": "alpha"}, headers={**headers(tokens, "alice"), "Origin": ORIGIN}).status_code == 403


def test_legacy_profile_and_direct_service_cannot_bypass_admission(context_runtime, monkeypatch):
    module, client, _, _, local, _, tokens = context_runtime
    monkeypatch.setattr(module, "DASHBOARD_AUTH_PROFILE", "legacy")
    assert client.get(URL, params={"project": "alpha"}, headers=headers(tokens, "alice")).status_code == 403
    from devcore_engine.security.identity import Principal, ProjectAccessDenied
    for principal in (None, Principal("alice", "unused", "alpha", READ)):
        with pytest.raises(ProjectAccessDenied):
            adapter.load_registered_project_context(local / "missing.db", principal)
    assert not (local / "missing.db").exists()


def test_slow_context_read_does_not_block_other_projects_or_status(context_runtime, monkeypatch):
    from httpx import ASGITransport, AsyncClient
    module, _, _, _, _, _, tokens = context_runtime
    entered, release = threading.Event(), threading.Event()
    original = adapter.load_project_context
    def delayed(directory, project, **kwargs):
        if project == "alpha":
            entered.set()
            if not release.wait(5):
                raise AssertionError("Context reader was not released")
        return original(directory, project, **kwargs)
    monkeypatch.setattr(adapter, "load_project_context", delayed)
    async def exercise():
        async with AsyncClient(transport=ASGITransport(app=module.app), base_url="http://fixture") as client:
            pending = asyncio.create_task(client.get(URL, params={"project": "alpha"}, headers=headers(tokens, "alice")))
            try:
                assert await asyncio.to_thread(entered.wait, 2)
                assert (await asyncio.wait_for(client.get("/api/status"), 1)).status_code == 200
                other = await asyncio.wait_for(client.get(URL, params={"project": "beta"}, headers=headers(tokens, "bob")), 1)
                assert other.status_code == 200 and other.json()["project"] == "beta"
            finally:
                release.set()
                result = await pending
            assert result.status_code == 200
    asyncio.run(exercise())
