"""Resume and isolation contracts for PostgreSQL project change cursors."""

from contextlib import contextmanager

import pytest

from devcore_engine.services.postgres_project_events import (
    PostgresProjectEventReader, validate_event_cursor,
)


class Cursor:
    def __init__(self, answers):
        self.answers = list(answers)
        self.queries = []

    def execute(self, sql, params=()):
        self.queries.append((sql, params))

    def fetchone(self):
        return self.answers.pop(0)

    def fetchall(self):
        return self.answers.pop(0)


def test_event_cursor_rejects_path_and_control_characters():
    for value in ("../beta", "alpha\n\ndata: leak", "a/b"):
        with pytest.raises(ValueError):
            validate_event_cursor(value)


def test_foreign_cursor_only_requests_a_project_resync(monkeypatch):
    reader = PostgresProjectEventReader("postgresql://app@127.0.0.1/fixture")
    cursor = Cursor([None, ("local-latest",)])
    projects = []

    @contextmanager
    def transaction(project):
        projects.append(project)
        yield cursor

    monkeypatch.setattr(reader, "_transaction", transaction)
    ids, next_cursor, resync = reader.changes("alpha", "foreign-event")
    assert (ids, next_cursor, resync) == ([], "local-latest", True)
    assert projects == ["alpha"]
    assert all(params[0] == "alpha" for _, params in cursor.queries)
