"""Offline admission and idempotency contracts for project automation evidence."""

from contextlib import contextmanager
import subprocess

import pytest

from devcore_engine.security.identity import Principal, READ, WRITE, ProjectAccessDenied
from devcore_engine.services import postgres_automation_hooks as module


class Cursor:
    def __init__(self, answers):
        self.answers = list(answers)
        self.statements = []

    def execute(self, sql, params=()):
        self.statements.append((sql, params))

    def fetchone(self):
        return self.answers.pop(0)


def make_store(monkeypatch, answers):
    store = module.PostgresAutomationHooks("postgresql://app:unused@127.0.0.1/fixture")
    cursor = Cursor(answers)
    projects = []

    @contextmanager
    def transaction(project):
        projects.append(project)
        yield cursor

    monkeypatch.setattr(store, "_transaction", transaction)
    monkeypatch.setattr(module, "_registered_git_root", lambda root: root == "E:/repo")
    return store, cursor, projects


def principal(project="alpha", actor="majdi", action=WRITE):
    return Principal(actor, "credential", project, action)


def test_start_requires_authorized_project_and_git_root(monkeypatch):
    store, cursor, projects = make_store(monkeypatch, [])
    with pytest.raises(ProjectAccessDenied):
        store.start(principal("beta"), "alpha", "session_start", "codex", "session-1")
    assert projects == [] and cursor.statements == []

    store, cursor, projects = make_store(monkeypatch, [("E:/not-git",)])
    with pytest.raises(ProjectAccessDenied, match="Git project"):
        store.start(principal(), "alpha", "session_start", "codex", "session-1")
    assert projects == ["alpha"]
    assert not any("INSERT" in sql for sql, _ in cursor.statements)


def test_start_is_idempotent_and_conflict_cannot_be_claimed_by_other_actor(monkeypatch):
    store, cursor, projects = make_store(monkeypatch, [("E:/repo",), None,
                                                       ("hook-existing", "majdi", "session_start", "codex")])
    event_id, created = store.start(principal(), "alpha", "session_start", "codex", "session-1")
    assert (event_id, created) == ("hook-existing", False)
    assert projects == ["alpha"]
    assert any("ON CONFLICT (project_id,idempotency_key) DO NOTHING" in sql
               for sql, _ in cursor.statements)

    other, _, _ = make_store(monkeypatch, [("E:/repo",), None,
                                          ("hook-existing", "mohd", "session_start", "codex")])
    with pytest.raises(ProjectAccessDenied, match="different origin"):
        other.start(principal(), "alpha", "session_start", "codex", "session-1")

    fresh, _, _ = make_store(monkeypatch, [("E:/repo",), ("hook-new",)])
    assert fresh.start(principal(), "alpha", "session_start", "codex", "session-2") == ("hook-new", True)

    with pytest.raises(ValueError, match="idempotency"):
        fresh.start(principal(), "alpha", "session_start", "codex", "bad key")


def test_finish_is_terminal_cas_and_actor_scoped(monkeypatch):
    store, cursor, projects = make_store(monkeypatch, [({},), ("hook-1",)])
    assert store.finish(principal(), "alpha", "hook-1", "succeeded")
    assert projects == ["alpha"]
    sql, params = cursor.statements[-1]
    assert "status='running'" in sql and "actor=%s" in sql
    assert params[-1] == "majdi"
    oversized, _, _ = make_store(monkeypatch, [({"existing": "x" * 8190},)])
    with pytest.raises(ValueError, match="Bounded result"):
        oversized.finish(principal(), "alpha", "hook-1", "succeeded", result={"new": "y"})
    with pytest.raises(ProjectAccessDenied):
        store.finish(principal("beta"), "alpha", "hook-1", "failed")
    with pytest.raises(ValueError, match="error code"):
        store.finish(principal(), "alpha", "hook-1", "failed", "secret output follows")


def test_read_requires_read_principal_and_bounded_limit(monkeypatch):
    store, _, projects = make_store(monkeypatch, [])
    with pytest.raises(ProjectAccessDenied):
        store.recent(principal(action=WRITE), "alpha")
    with pytest.raises(ValueError, match="Limit"):
        store.recent(principal(action=READ), "alpha", limit=101)
    assert projects == []


def test_git_admission_uses_exact_registered_repository(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True, timeout=10)
    nested = repo / "nested"
    nested.mkdir()
    assert module._registered_git_root(str(repo))
    assert not module._registered_git_root(str(nested))
    assert not module._registered_git_root(str(tmp_path / "missing"))
