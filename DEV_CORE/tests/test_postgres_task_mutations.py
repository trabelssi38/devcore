"""Offline transaction contracts for PostgreSQL Gateway task writes."""

from contextlib import contextmanager

import pytest

from devcore_engine.context import RequestContext
from devcore_engine.services.postgres_task_mutations import PostgresTaskMutations
from devcore_engine.services.task_mutations import TaskMutationConflict


class ScriptedCursor:
    def __init__(self, answers):
        self.answers = list(answers)
        self.statements = []
        self.rowcount = 1

    def execute(self, sql, params=()):
        self.statements.append((sql, params))

    def fetchone(self):
        return self.answers.pop(0)

    def fetchall(self):
        return self.answers.pop(0)


def store_with_cursor(monkeypatch, answers):
    store = PostgresTaskMutations("postgresql://app:unused@127.0.0.1/fixture")
    cursor = ScriptedCursor(answers)
    projects = []

    @contextmanager
    def transaction(project):
        projects.append(project)
        yield cursor

    monkeypatch.setattr(store, "_transaction", transaction)
    return store, cursor, projects


def test_transition_writes_task_audit_and_event_in_one_project_transaction(monkeypatch):
    store, cursor, projects = store_with_cursor(
        monkeypatch, [[("uuid-1", "T-1", "in_progress", 4, None)]])
    ok, _ = store.transition("alpha", "T-1", "complete", 4,
                             RequestContext("alpha", user_id="majdi"))
    assert ok and projects == ["alpha"]
    sql = "\n".join(item[0] for item in cursor.statements)
    assert "pg_advisory_xact_lock" in sql
    assert "FOR UPDATE" in sql
    assert "UPDATE tasks" in sql
    assert "INSERT INTO audit_log" in sql
    assert "INSERT INTO events" in sql
    assert any("majdi" in params for _, params in cursor.statements)


def test_transition_refuses_unversioned_and_cross_project_writes(monkeypatch):
    store, _, projects = store_with_cursor(monkeypatch, [])
    with pytest.raises(TaskMutationConflict, match="principal"):
        store.transition("alpha", "T-1", "complete", 1,
                         RequestContext("beta", user_id="majdi"))
    with pytest.raises(TaskMutationConflict, match="version"):
        store.transition("alpha", "T-1", "complete", None,
                         RequestContext("alpha", user_id="majdi"))
    assert projects == []


def test_create_allocates_number_and_emits_audit_and_event(monkeypatch):
    store, cursor, projects = store_with_cursor(monkeypatch, [("alpha",), (486,), None])
    created = store.create("alpha", "  New task  ", "coding", 2, None,
                           RequestContext("alpha", user_id="majdi"))
    assert created["id"] == "T-487" and created["version"] == 1
    assert projects == ["alpha"]
    sql = "\n".join(item[0] for item in cursor.statements)
    assert "FOR UPDATE" in sql
    assert "INSERT INTO tasks" in sql
    assert "INSERT INTO audit_log" in sql
    assert "INSERT INTO events" in sql


def test_next_reuses_active_task_without_mutation(monkeypatch):
    store, cursor, _ = store_with_cursor(
        monkeypatch, [("uuid-1", "T-1", "Active", "coding", "in_progress", 0, 1, 2)])
    active = store.next_task("alpha", RequestContext("alpha", user_id="majdi"))
    assert active["id"] == "T-1" and active["version"] == 2
    assert not any("UPDATE tasks" in sql for sql, _ in cursor.statements)
