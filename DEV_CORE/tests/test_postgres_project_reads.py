"""Fail-closed contracts for the PostgreSQL project readers."""

import pytest

from devcore_engine.security.identity import AUDIT_READ, CONTEXT_READ, Principal, ProjectAccessDenied
from devcore_engine.services.postgres_project_reads import PostgresProjectReader
from devcore_engine.services.task_audit import InvalidAuditCursor


def test_project_reader_requires_local_database():
    with pytest.raises(ValueError):
        PostgresProjectReader("postgresql://app@203.0.113.9/fixture")


def test_project_reader_rejects_wrong_principal_before_database_access(monkeypatch):
    reader = PostgresProjectReader("postgresql://app@127.0.0.1/fixture")
    monkeypatch.setattr(reader, "_transaction", lambda project: (_ for _ in ()).throw(
        AssertionError("database must not be opened")))
    with pytest.raises(ProjectAccessDenied):
        reader.context(Principal("user", "credential", "alpha", AUDIT_READ))
    with pytest.raises(ProjectAccessDenied):
        reader.task_audit(Principal("user", "credential", "alpha", CONTEXT_READ))


def test_project_reader_rejects_invalid_cursor_before_database_access(monkeypatch):
    reader = PostgresProjectReader("postgresql://app@127.0.0.1/fixture")
    monkeypatch.setattr(reader, "_transaction", lambda project: (_ for _ in ()).throw(
        AssertionError("database must not be opened")))
    with pytest.raises(InvalidAuditCursor):
        reader.task_audit(Principal("user", "credential", "alpha", AUDIT_READ),
                          before_id="invalid")
