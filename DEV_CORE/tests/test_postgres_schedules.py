"""Safety rules for PostgreSQL schedules before any command is queued."""

import pytest
import sys

from devcore_engine.runs.postgres_schedules import DAILY_SCRIPT, PostgresScheduleDispatcher
from devcore_engine.runs.executor import build_isolated_environment


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


def test_daily_metrics_uses_only_managed_command_and_database_secret_is_not_inherited():
    metadata = {"execution_ready": True, "job_kind": "daily_metrics",
                "command": [sys.executable, str(DAILY_SCRIPT)], "timeout_seconds": 30}
    command, timeout, zone = PostgresScheduleDispatcher._qualified_command(
        "0 9 * * *", "Europe/Paris", metadata)
    assert command == metadata["command"] and timeout == 30 and zone.key == "Europe/Paris"
    with pytest.raises(ValueError, match="managed argv"):
        PostgresScheduleDispatcher._qualified_command(
            "0 9 * * *", "Europe/Paris", {**metadata, "command": ["python", "other.py"]})
    child = build_isolated_environment(base_env={"DEVCORE_DATABASE_URL": "postgresql://secret",
                                                 "DEVCORE_LOCAL_ROOT": "E:/fixture"})
    assert "DEVCORE_DATABASE_URL" not in child and child["DEVCORE_LOCAL_ROOT"] == "E:/fixture"
