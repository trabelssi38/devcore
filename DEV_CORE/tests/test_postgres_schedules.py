"""Safety rules for PostgreSQL schedules before any command is queued."""

import pytest

from devcore_engine.runs.postgres_schedules import PostgresScheduleDispatcher


def test_active_schedule_requires_explicit_qualified_bounded_argv():
    validate = PostgresScheduleDispatcher._qualified_command
    with pytest.raises(RuntimeError, match="qualification"):
        validate("*/5 * * * *", "UTC", {"command": ["python"]})
    with pytest.raises(ValueError, match="argv"):
        validate("*/5 * * * *", "UTC", {"execution_ready": True,
                                         "command": ["python", "x" * 4097]})
    with pytest.raises(ValueError, match="cron"):
        validate("* * * * * *", "UTC", {"execution_ready": True,
                                        "command": ["python"]})
    command, timeout, zone = validate("*/5 * * * *", "UTC",
                                      {"execution_ready": True, "command": ["python"],
                                       "timeout_seconds": 30})
    assert command == ["python"] and timeout == 30 and zone.key == "UTC"


def test_schedule_store_requires_loopback_postgresql():
    with pytest.raises(ValueError, match="local PostgreSQL"):
        PostgresScheduleDispatcher("postgresql://app@203.0.113.10/prod")
