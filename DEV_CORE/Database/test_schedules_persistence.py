import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.dialects import postgresql


DATABASE_ROOT = Path(__file__).resolve().parent
API_ROOT = DATABASE_ROOT.parent / "API"
for path in [DATABASE_ROOT, API_ROOT]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


class FakeResult:
    def __init__(self, rows=None):
        self._rows = rows or []

    def mappings(self):
        return self

    def all(self):
        return self._rows


class FakeSession:
    def __init__(self):
        self.statements = []

    def execute(self, statement):
        self.statements.append(statement)
        return FakeResult()


def test_schedule_tables_are_declared_in_sqlalchemy_metadata() -> None:
    from devcore_db.models import metadata

    assert "schedules" in metadata.tables
    assert "schedule_history" in metadata.tables
    assert metadata.tables["schedules"].c.project_id.foreign_keys
    assert metadata.tables["schedule_history"].c.schedule_id.foreign_keys
    assert metadata.tables["schedule_history"].c.run_id.foreign_keys
    assert metadata.tables["schedules"].c.metadata.type.__class__.__name__ == "JSONB"
    assert metadata.tables["schedule_history"].c.details.type.__class__.__name__ == "JSONB"


def test_schedule_repository_creates_persistent_schedule_and_history() -> None:
    from devcore_db.repositories import SqlScheduleRepository

    session = FakeSession()
    repository = SqlScheduleRepository(session)
    next_run_at = datetime(2026, 7, 13, 15, 0, tzinfo=timezone.utc)

    repository.create_schedule(
        schedule_id="sch_daily_launch",
        project_id="devcore",
        name="Daily launch",
        cron="0 10 * * *",
        timezone_name="Africa/Lagos",
        next_run_at=next_run_at,
    )
    repository.record_history(
        history_id="schh_1",
        schedule_id="sch_daily_launch",
        event_type="created",
        status="succeeded",
        details={"source": "api"},
    )

    assert session.statements[0].is_insert
    assert session.statements[0].table.name == "schedules"
    assert session.statements[1].is_insert
    assert session.statements[1].table.name == "schedule_history"


def test_schedule_repository_lists_active_due_schedules() -> None:
    from devcore_db.repositories import SqlScheduleRepository

    session = FakeSession()

    SqlScheduleRepository(session).list_due_schedules(now=datetime(2026, 7, 13, 15, 0, tzinfo=timezone.utc))

    statement = session.statements[0]
    sql = str(statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    assert statement.is_select
    assert "schedules" in sql
    assert "next_run_at" in sql
    assert "active" in sql
