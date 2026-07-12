import sys
from pathlib import Path


DATABASE_ROOT = Path(__file__).resolve().parent
API_ROOT = DATABASE_ROOT.parent / "API"
for path in [DATABASE_ROOT, API_ROOT]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return self

    def all(self):
        return self._rows


class FakeSession:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.statements = []
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def execute(self, statement):
        self.statements.append(statement)
        return FakeResult(self.rows)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def test_sql_task_repository_lists_tasks_as_domain_contracts() -> None:
    from devcore_db.repositories import SqlTaskRepository

    session = FakeSession(
        rows=[
            {
                "id": "T-163",
                "title": "Repositories",
                "status": "active",
                "mode": "coding",
                "steps_done": 0,
                "steps_total": 1,
                "depends_on": None,
                "worktree": "main",
            }
        ]
    )

    tasks = SqlTaskRepository(session).list_tasks(project="devcore")

    assert tasks[0].id == "T-163"
    assert tasks[0].title == "Repositories"
    assert session.statements[0].is_select


def test_sql_task_repository_creates_task_statement() -> None:
    from devcore_db.repositories import SqlTaskRepository

    session = FakeSession()

    SqlTaskRepository(session).create_task(
        project_id="devcore",
        task_id="T-200",
        title="Create repository",
        mode="coding",
    )

    statement = session.statements[0]
    assert statement.is_insert
    assert statement.table.name == "tasks"


def test_unit_of_work_commits_and_closes_on_success() -> None:
    from devcore_db.repositories import UnitOfWork

    session = FakeSession()

    with UnitOfWork(lambda: session) as uow:
        assert uow.session is session

    assert session.committed is True
    assert session.rolled_back is False
    assert session.closed is True


def test_unit_of_work_rolls_back_and_closes_on_error() -> None:
    from devcore_db.repositories import UnitOfWork

    session = FakeSession()

    try:
        with UnitOfWork(lambda: session):
            raise RuntimeError("boom")
    except RuntimeError:
        pass

    assert session.committed is False
    assert session.rolled_back is True
    assert session.closed is True
