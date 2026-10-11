import json
import sqlite3
import asyncio
import threading
import time
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient


API_ROOT = Path(__file__).resolve().parent
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))


def write_task_board(data_root: Path, project: str = "devcore") -> None:
    board_dir = data_root / "Memory" / project
    board_dir.mkdir(parents=True)
    (board_dir / "tasks.json").write_text(
        json.dumps(
            {
                "project": project,
                "current_task": "T-157",
                "tasks": [
                    {
                        "id": "T-157",
                        "title": "Ports",
                        "status": "active",
                        "mode": "coding",
                        "steps_done": 0,
                        "steps_total": 1,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_file_task_repository_reads_existing_board(tmp_path):
    from devcore_api.ports import FileTaskRepository

    write_task_board(tmp_path)
    repository = FileTaskRepository(data_root=tmp_path)

    tasks = repository.list_tasks(project="devcore")

    assert len(tasks) == 1
    assert tasks[0].id == "T-157"
    assert tasks[0].project == "devcore"


def test_api_tasks_endpoint_uses_task_repository_port(tmp_path):
    from devcore_api import create_app
    from devcore_api.ports import FileTaskRepository

    write_task_board(tmp_path)
    app = create_app(task_repository=FileTaskRepository(data_root=tmp_path))
    client = TestClient(app)

    response = client.get("/api/v1/tasks?project=devcore")

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == 1
    assert payload["project"] == "devcore"
    assert payload["tasks"][0]["id"] == "T-157"


def test_api_tasks_endpoint_reports_missing_board_as_stable_error(tmp_path):
    from devcore_api import create_app
    from devcore_api.ports import FileTaskRepository

    app = create_app(task_repository=FileTaskRepository(data_root=tmp_path))
    client = TestClient(app)

    response = client.get("/api/v1/tasks?project=missing")

    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "task_board_not_found"
    assert payload["trace_id"]


def test_api_tasks_endpoint_requires_project(tmp_path):
    from devcore_api import create_app
    from devcore_api.ports import FileTaskRepository

    client = TestClient(create_app(task_repository=FileTaskRepository(data_root=tmp_path)))
    response = client.get("/api/v1/tasks")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_sqlite_repository_scopes_project_and_normalizes_history(tmp_path):
    from devcore_api.ports import SqliteTaskRepository

    path = tmp_path / "devcore.db"
    conn = sqlite3.connect(path)
    conn.execute("""CREATE TABLE tasks (
        id TEXT, project_id TEXT, title TEXT, status TEXT, mode TEXT,
        steps_done INTEGER, steps_total INTEGER, created_at TEXT,
        PRIMARY KEY(id, project_id))""")
    conn.executemany("INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?)", [
        ("T-01", "alpha", "A", "in_progress", "coding", 0, 2, "2026-01-01"),
        ("T-01", "beta", "B", "todo", "coding", 0, 1, "2026-01-01"),
        ("T-GIT-ABC123", "alpha", "Commit", "done", "git", 1, 1, "2026-01-02"),
    ])
    conn.commit()
    conn.close()

    repo = SqliteTaskRepository(path)
    alpha = repo.list_tasks("alpha")
    assert [(row.id, row.status, row.mode) for row in alpha] == [
        ("T-01", "active", "coding"),
        ("T-GIT-ABC123", "done", "git"),
    ]
    assert [row.title for row in repo.list_tasks("beta")] == ["B"]
    from devcore_api import create_app
    client = TestClient(create_app(task_repository=repo))
    payload = client.get("/api/v1/tasks?project=alpha").json()
    assert [task["id"] for task in payload["tasks"]] == ["T-01", "T-GIT-ABC123"]
    assert payload["tasks"][0]["status"] == "active"
    assert payload["tasks"][0]["version"] is None


def test_sqlite_repository_returns_versions_without_changing_schema(tmp_path):
    from devcore_api.ports import SqliteTaskRepository
    path = tmp_path / "versioned #tasks.db"
    conn = sqlite3.connect(path)
    conn.execute("""CREATE TABLE tasks(id TEXT, project_id TEXT, title TEXT, status TEXT,
        mode TEXT, steps_done INTEGER, steps_total INTEGER, created_at TEXT, version INTEGER)""")
    conn.execute("INSERT INTO tasks VALUES ('T-01','alpha','Versioned','todo','coding',0,1,'2026-01-01',7)")
    conn.commit()
    before = conn.execute("SELECT sql FROM sqlite_master ORDER BY name").fetchall()
    conn.close()
    assert SqliteTaskRepository(path).list_tasks("alpha")[0].version == 7
    with sqlite3.connect(path) as check:
        assert check.execute("SELECT sql FROM sqlite_master ORDER BY name").fetchall() == before


def test_explicit_json_export_preserves_sql_version_for_dual_read(tmp_path):
    from devcore_engine.db import init_db
    from devcore_engine.services.tasks import TaskService
    from devcore_api.ports import FileTaskRepository, SqliteTaskRepository, DualReadTaskRepository
    database = tmp_path / "devcore.db"
    conn = init_db(database)
    conn.execute("INSERT INTO projects(id,name,root_path) VALUES ('alpha','alpha','.')")
    conn.execute("INSERT INTO tasks(id,project_id,title,mode) VALUES ('T-01','alpha','Versioned','coding')")
    conn.execute("UPDATE tasks SET title='Updated' WHERE project_id='alpha'")
    conn.commit()
    export_root = tmp_path / "export"
    TaskService(conn).export_legacy_json("alpha", export_root)
    warnings = []
    dual = DualReadTaskRepository(legacy_repository=FileTaskRepository(export_root),
                                 sql_repository=SqliteTaskRepository(database), mode="dual",
                                 on_mismatch=warnings.append)
    assert dual.list_tasks("alpha")[0].version == 2
    assert warnings == []
    conn.execute("UPDATE tasks SET title='Newer update' WHERE project_id='alpha'")
    conn.commit()
    conn.close()
    assert dual.list_tasks("alpha")[0].version == 2
    assert warnings == ["task_read_mismatch: project=alpha legacy=1 sql=1"]


def test_file_repository_accepts_git_task_and_rejects_wrong_board_project(tmp_path):
    from devcore_api.ports import FileTaskRepository

    board_dir = tmp_path / "Memory" / "alpha"
    board_dir.mkdir(parents=True)
    path = board_dir / "tasks.json"
    data = {
        "project": "alpha",
        "tasks": [{"id": "T-GIT-ABC123", "title": "Commit", "status": "done",
                   "mode": "git", "steps_done": 1, "steps_total": 1}],
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    repo = FileTaskRepository(tmp_path)
    assert repo.list_tasks("alpha")[0].id == "T-GIT-ABC123"
    data["project"] = "beta"
    path.write_text(json.dumps(data), encoding="utf-8")
    import pytest
    with pytest.raises(ValueError):
        repo.list_tasks("alpha")


def test_file_repository_rejects_unscoped_or_foreign_task_board(tmp_path):
    from devcore_api import create_app
    from devcore_api.ports import FileTaskRepository, TaskBoardInvalid
    import pytest

    board_dir = tmp_path / "Memory" / "alpha"
    board_dir.mkdir(parents=True)
    path = board_dir / "tasks.json"
    task = {"id": "T-01", "title": "Alpha", "status": "todo", "mode": "coding"}
    repo = FileTaskRepository(tmp_path)
    client = TestClient(create_app(task_repository=repo))

    for board in (
        {"tasks": [task]},
        {"project": "alpha", "tasks": [{**task, "project": "beta"}]},
        {"project": "alpha", "tasks": {}},
    ):
        path.write_text(json.dumps(board), encoding="utf-8")
        with pytest.raises(TaskBoardInvalid):
            repo.list_tasks("alpha")
        response = client.get("/api/v1/tasks?project=alpha")
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "invalid_task_board"

    path.write_text("{broken", encoding="utf-8")
    assert client.get("/api/v1/tasks?project=alpha").json()["error"]["code"] == "invalid_task_board"

    path.write_text(json.dumps({"project": "alpha", "tasks": [task]}), encoding="utf-8")
    assert [row.id for row in repo.list_tasks("alpha")] == ["T-01"]


def test_sql_read_mode_needs_an_explicit_database_path(monkeypatch):
    import pytest
    from devcore_api.ports import configured_task_repository

    monkeypatch.setenv("DEVCORE_TASK_READ_MODE", "sql")
    monkeypatch.delenv("DEVCORE_SQLITE_DB_PATH", raising=False)
    with pytest.raises(ValueError, match="DEVCORE_SQLITE_DB_PATH"):
        configured_task_repository()


def test_slow_task_read_does_not_block_health_endpoint():
    from devcore_api import create_app

    started = threading.Event()
    release = threading.Event()

    class SlowRepository:
        def list_tasks(self, project: str):
            started.set()
            release.wait(2)
            return []

    async def exercise():
        app = create_app(task_repository=SlowRepository())
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            task_request = asyncio.create_task(client.get("/api/v1/tasks?project=alpha"))
            assert await asyncio.to_thread(started.wait, 1)
            start = time.monotonic()
            try:
                health = await asyncio.wait_for(client.get("/api/v1/health"), timeout=0.5)
                assert health.status_code == 200
                assert time.monotonic() - start < 0.5
            finally:
                release.set()
            assert (await task_request).status_code == 200

    asyncio.run(exercise())


def test_unit_of_work_in_memory_and_sqlite(tmp_path):
    from devcore_api.ports import InMemoryUnitOfWork, SqliteUnitOfWork, UnitOfWork

    # InMemoryUnitOfWork satisfies UnitOfWork protocol
    uow_mem = InMemoryUnitOfWork()
    assert isinstance(uow_mem, UnitOfWork)
    with uow_mem as u:
        u.commit()
    assert uow_mem.committed is True
    assert uow_mem.rolled_back is False

    # Exception triggers rollback
    uow_mem_err = InMemoryUnitOfWork()
    try:
        with uow_mem_err as u:
            raise RuntimeError("forced failure")
    except RuntimeError:
        pass
    assert uow_mem_err.committed is False
    assert uow_mem_err.rolled_back is True

    # SqliteUnitOfWork satisfies UnitOfWork protocol
    db_file = tmp_path / "uow_test.db"
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE test_items (id TEXT PRIMARY KEY, value TEXT)")
    conn.commit()

    uow_sql = SqliteUnitOfWork(conn)
    assert isinstance(uow_sql, UnitOfWork)
    with uow_sql as u:
        conn.execute("INSERT INTO test_items VALUES ('1', 'committed')")
        u.commit()

    assert conn.execute("SELECT value FROM test_items WHERE id='1'").fetchone()[0] == "committed"

    # Rollback on exception
    try:
        with uow_sql as u:
            conn.execute("INSERT INTO test_items VALUES ('2', 'will rollback')")
            raise ValueError("abort transaction")
    except ValueError:
        pass

    assert conn.execute("SELECT value FROM test_items WHERE id='2'").fetchone() is None
    conn.close()


def test_typed_ports_protocol_conformance():
    from devcore_api.contracts import (
        KnowledgeItemContract,
        ModelRequestContract,
        ModelResponseContract,
        RunContract,
        RunnerResultContract,
        UserContract,
        WorkspaceMembershipContract,
    )
    from devcore_api.ports import (
        IdentityProvider,
        KnowledgeProvider,
        ModelGateway,
        Runner,
        WorkflowEngine,
    )

    class DummyIdentityProvider:
        def get_user(self, user_id: str) -> UserContract | None:
            return UserContract(id="usr_01", email="test@test.local", display_name="Test")

        def validate_token(self, token: str) -> UserContract | None:
            return None

        def get_membership(self, workspace_id: str, user_id: str) -> WorkspaceMembershipContract | None:
            return None

    assert isinstance(DummyIdentityProvider(), IdentityProvider)

    class DummyWorkflowEngine:
        def start_run(self, task_id: str, context: object | None = None) -> RunContract:
            return RunContract(id="run-10", task_id="T-01", status="queued")

        def get_run(self, run_id: str) -> RunContract | None:
            return None

        def cancel_run(self, run_id: str) -> RunContract:
            return RunContract(id="run-10", task_id="T-01", status="cancelled")

    assert isinstance(DummyWorkflowEngine(), WorkflowEngine)

    class DummyRunner:
        def execute(self, command: str, run_id: str, timeout_seconds: float | None = None) -> RunnerResultContract:
            return RunnerResultContract(run_id=run_id, exit_code=0, stdout="done", stderr="", duration_seconds=0.1)

    assert isinstance(DummyRunner(), Runner)

    class DummyModelGateway:
        def generate(self, request: ModelRequestContract | str, model: str | None = None) -> ModelResponseContract:
            prompt = request.prompt if isinstance(request, ModelRequestContract) else str(request)
            return ModelResponseContract(text=f"Response to: {prompt}", model=model or "default")

        def embed(self, texts: list[str]) -> list[list[float]]:
            return [[0.1, 0.2] for _ in texts]

    assert isinstance(DummyModelGateway(), ModelGateway)

    class DummyKnowledgeProvider:
        def search(self, query: str, project: str, limit: int = 10) -> list[KnowledgeItemContract]:
            return [KnowledgeItemContract(id="k-1", project=project, title="Info", content="Result content", score=0.95)]

        def get_context(self, project: str, budget_bytes: int = 12000) -> str:
            return f"Context for {project}"

    assert isinstance(DummyKnowledgeProvider(), KnowledgeProvider)


def test_file_task_repository_export_and_import_compatibility_board(tmp_path):
    from devcore_api.contracts import TaskContract
    from devcore_api.ports import FileTaskRepository

    repo = FileTaskRepository(data_root=tmp_path)
    tasks = [
        TaskContract(
            id="T-01",
            title="Initial task",
            status="active",
            mode="coding",
            steps_done=1,
            steps_total=3,
            project="test_proj",
            version=5,
        ),
        TaskContract(
            id="T-02",
            title="Second task",
            status="todo",
            mode="reasoning",
            steps_done=0,
            steps_total=1,
            project="test_proj",
            version=1,
        ),
    ]

    board_path = repo.export_compatibility_board("test_proj", tasks)
    assert board_path.is_file()
    assert board_path == repo.board_path("test_proj")

    # Verify JSON content on disk
    raw = json.loads(board_path.read_text(encoding="utf-8"))
    assert raw["project"] == "test_proj"
    assert raw["current_task"] == "T-01"
    assert len(raw["tasks"]) == 2
    assert raw["tasks"][0]["version"] == 5

    # Re-import via import_compatibility_board and list_tasks
    imported = repo.import_compatibility_board("test_proj")
    assert len(imported) == 2
    assert imported[0].id == "T-01"
    assert imported[0].version == 5
    assert imported[1].mode == "reasoning"

    listed = repo.list_tasks("test_proj")
    assert len(listed) == 2
    assert listed[0].id == "T-01"


def test_compare_task_fields_detects_field_and_version_differences():
    from devcore_api.contracts import TaskContract
    from devcore_api.ports import compare_task_fields

    t1 = TaskContract(id="T-01", title="A", status="active", mode="coding", steps_done=1, steps_total=2, project="alpha", version=2)
    t2 = TaskContract(id="T-02", title="B", status="todo", mode="coding", steps_done=0, steps_total=1, project="alpha", version=1)

    # Identical
    report = compare_task_fields([t1, t2], [t1, t2])
    assert report["is_match"] is True
    assert report["field_mismatches"] == []
    assert report["version_mismatches"] == []

    # Field difference (title and steps_done)
    t1_mod = t1.model_copy(update={"title": "A modified", "steps_done": 2})
    report_fields = compare_task_fields([t1, t2], [t1_mod, t2])
    assert report_fields["is_match"] is False
    assert len(report_fields["field_mismatches"]) == 1
    assert report_fields["field_mismatches"][0]["id"] == "T-01"
    assert "title" in report_fields["field_mismatches"][0]["differences"]
    assert "steps_done" in report_fields["field_mismatches"][0]["differences"]

    # Version difference
    t1_ver = t1.model_copy(update={"version": 7})
    report_ver = compare_task_fields([t1], [t1_ver])
    assert report_ver["is_match"] is False
    assert len(report_ver["version_mismatches"]) == 1
    assert report_ver["version_mismatches"][0] == {"id": "T-01", "legacy_version": 2, "sql_version": 7}

    # Missing in sql / missing in legacy
    report_missing = compare_task_fields([t1], [t2])
    assert report_missing["is_match"] is False
    assert report_missing["missing_in_sql"] == ["T-01"]
    assert report_missing["missing_in_legacy"] == ["T-02"]


def test_dual_read_task_repository_compare_tasks_and_callback():
    from devcore_api.contracts import TaskContract
    from devcore_api.ports import DualReadTaskRepository

    class MemRepo:
        def __init__(self, tasks):
            self.tasks = tasks

        def list_tasks(self, project: str):
            return self.tasks

    t_leg = TaskContract(id="T-01", title="Alpha", status="active", mode="coding", steps_done=0, steps_total=1, project="p", version=1)
    t_sql = TaskContract(id="T-01", title="Alpha SQL", status="active", mode="coding", steps_done=0, steps_total=1, project="p", version=2)

    legacy_repo = MemRepo([t_leg])
    sql_repo = MemRepo([t_sql])

    reports = []
    dual = DualReadTaskRepository(
        legacy_repository=legacy_repo,
        sql_repository=sql_repo,
        mode="dual",
        on_mismatch_report=reports.append,
    )

    comparison = dual.compare_tasks("p")
    assert comparison["is_match"] is False
    assert dual.last_comparison is comparison

    # When list_tasks runs in dual mode, on_mismatch_report is triggered
    dual.list_tasks("p")
    assert len(reports) == 1
    assert reports[0]["field_mismatches"][0]["differences"]["title"]["legacy"] == "Alpha"
    assert reports[0]["version_mismatches"][0]["sql_version"] == 2
