"""Test suite for Lot L3: PostgreSQL target persistence, schema migrations,
atomic numbering, optimistic concurrency, RLS isolation, and dry-run reconciliation.

Strictly follows:
- Temporary isolated roots (DEVCORE_LOCAL_ROOT, DEVCORE_DATA_ROOT).
- Zero production data, Dropbox, or live index fixtures.
- Pure Python 3.13 verification.
"""

from __future__ import annotations

import os
import sqlite3
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from devcore_engine.persistence.config import (
    DatabaseConfig,
    DatabaseRole,
    is_dropbox_path,
    validate_storage_path_outside_dropbox,
)
from devcore_engine.persistence.importer import (
    PostgresDryRunImporter,
    ReconciliationReport,
    classify_runtime_state_key,
    compute_task_digest,
)
from devcore_engine.persistence.models import (
    metadata,
    project_memberships,
    projects,
    sessions,
    tasks,
    users,
)
from devcore_engine.persistence.repositories import (
    SqlTaskRepository,
    SqlUnitOfWork,
    generate_task_uuid,
    parse_task_number,
)
from devcore_engine.persistence.rls import (
    ProjectContextManager,
    build_rls_ddl,
    get_project_context,
    register_pool_isolation_guards,
    reset_project_context,
    set_project_context,
)
from devcore_engine.services.task_mutations import TaskMutationConflict


# ============================================================================
# 1. Config & Dropbox Storage Protection (Item 445)
# ============================================================================

def test_database_config_bounds_pool_and_enforces_dropbox_isolation(tmp_path):
    # Enforces bounded pool sizes
    cfg = DatabaseConfig(pool_size=100, max_overflow=50, pool_timeout=999.0)
    assert cfg.pool_size == 20  # capped at 20
    assert cfg.max_overflow == 10  # capped at 10
    assert cfg.pool_timeout == 60.0  # capped at 60s

    kwargs = cfg.get_engine_kwargs()
    assert kwargs["pool_size"] == 20
    assert kwargs["pool_pre_ping"] is True

    # Role separation
    app_cfg = DatabaseConfig(role=DatabaseRole.APPLICATION)
    mig_cfg = DatabaseConfig(role=DatabaseRole.MIGRATION)
    assert "devcore_app" in app_cfg.active_url
    assert "devcore_migration" in mig_cfg.active_url

    # Decision D-004: strictly forbid storage in Dropbox
    dropbox_dir = tmp_path / "My_Dropbox_Folder" / "data"
    dropbox_dir.mkdir(parents=True)
    assert is_dropbox_path(dropbox_dir) is True

    with pytest.raises(ValueError, match="inside a Dropbox folder"):
        validate_storage_path_outside_dropbox(dropbox_dir)

    safe_dir = tmp_path / "safe_local_store"
    safe_dir.mkdir(parents=True)
    assert is_dropbox_path(safe_dir) is False
    assert validate_storage_path_outside_dropbox(safe_dir) == safe_dir.resolve()


# ============================================================================
# 2. Target Schema Contracts & Unique Constraints (Item 446 & 447)
# ============================================================================

def test_schema_declares_core_tables_and_unique_task_number_constraint():
    schema_sql_path = Path(__file__).resolve().parents[1] / "devcore_engine" / "persistence" / "schema.sql"
    assert schema_sql_path.exists()
    sql_text = schema_sql_path.read_text(encoding="utf-8").lower()

    # Core required tables in target schema
    expected_tables = [
        "organizations",
        "users",
        "sessions",
        "workspaces",
        "workspace_memberships",
        "workspace_quotas",
        "projects",
        "project_memberships",
        "tasks",
        "runs",
        "plugins",
        "events",
        "audit_log",
        "schedules",
        "schedule_history",
        "outbox_messages",
        "artifacts",
        "memory_entries",
        "budgets",
    ]
    for table_name in expected_tables:
        assert f"create table if not exists {table_name}" in sql_text
        assert table_name in metadata.tables

    # Check tasks schema constraints in DDL and SQLAlchemy metadata
    assert "task_uuid uuid primary key" in sql_text
    assert "task_number integer not null" in sql_text
    assert "constraint uq_tasks_project_task_number unique (project_id, task_number)" in sql_text
    assert "tasks_version_positive check (version >= 1)" in sql_text

    task_table = metadata.tables["tasks"]
    assert "task_uuid" in task_table.c
    assert "task_number" in task_table.c
    assert "version" in task_table.c
    assert "project_id" in task_table.c

    # Check sessions table
    assert "user_id text not null references users(id)" in sql_text
    assert "token_hash text not null unique" in sql_text

    # Check project memberships table
    assert "constraint project_memberships_role check" in sql_text
    assert "unique (project_id, user_id)" in sql_text

    # Check PostgreSQL dialect DDL compilation
    task_ddl = str(CreateTable(task_table).compile(dialect=postgresql.dialect()))
    assert "task_uuid UUID NOT NULL" in task_ddl
    assert "uq_tasks_project_task_number UNIQUE (project_id, task_number)" in task_ddl


# ============================================================================
# 3. Row-Level Security & Pooled Connection Isolation (Item 450)
# ============================================================================

def test_rls_ddl_and_transaction_pool_connection_isolation():
    rls_statements = build_rls_ddl()
    assert len(rls_statements) == 14  # 7 tables x 2 (ENABLE RLS + CREATE POLICY)

    for stmt in rls_statements:
        assert "ROW LEVEL SECURITY" in stmt or "CREATE POLICY" in stmt
        if "CREATE POLICY" in stmt:
            assert "app.current_project_id" in stmt

    # Test ProjectContextManager with a mock connection
    class MockConnection:
        def __init__(self):
            self.info = {}
            self.executed_statements = []

        def execute(self, statement, params=None):
            self.executed_statements.append((statement, params))
            return MagicMock()

    conn = MockConnection()

    # Enter project context
    with ProjectContextManager(conn, "proj_alpha"):
        assert get_project_context(conn) == "proj_alpha"
        assert conn.info.get("app.current_project_id") == "proj_alpha"

    # Exited project context: MUST be reset
    assert get_project_context(conn) is None
    assert "app.current_project_id" not in conn.info

    # Verify connection pool isolation: connection returned to pool clears context
    pool_engine = create_engine("sqlite:///:memory:")
    register_pool_isolation_guards(pool_engine)

    conn1 = pool_engine.connect()
    set_project_context(conn1, "proj_secret")
    assert get_project_context(conn1) == "proj_secret"
    conn1.close()  # Checked in to pool

    # Checkout from pool: MUST NOT retain previous project context
    conn2 = pool_engine.connect()
    assert get_project_context(conn2) is None
    conn2.close()


# ============================================================================
# 4. Atomic Task Numbering, UUID v5, and Repositories (Item 447 & 449)
# ============================================================================

def test_sql_task_repository_atomic_numbering_and_uuid_v5(tmp_path):
    # Setup test SQLite database using the SQLAlchemy schema
    db_file = tmp_path / "test_repo.db"
    engine = create_engine(f"sqlite:///{db_file}")

    # Create only needed tables for repository testing
    ddl_statements = [
        """CREATE TABLE projects (
            id TEXT PRIMARY KEY,
            workspace_id TEXT,
            name TEXT NOT NULL,
            root_path TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            metadata TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE tasks (
            task_uuid TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(id),
            task_number INTEGER NOT NULL,
            legacy_id TEXT,
            title TEXT NOT NULL,
            mode TEXT DEFAULT 'coding',
            status TEXT DEFAULT 'todo',
            version INTEGER DEFAULT 1,
            steps_done INTEGER DEFAULT 0,
            steps_total INTEGER DEFAULT 1,
            depends_on_uuid TEXT,
            worktree TEXT,
            metadata TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (project_id, task_number)
        )""",
        "INSERT INTO projects (id, name, root_path) VALUES ('alpha', 'Alpha', '/alpha')",
        "INSERT INTO projects (id, name, root_path) VALUES ('beta', 'Beta', '/beta')",
    ]
    with engine.begin() as conn:
        for stmt in ddl_statements:
            conn.exec_driver_sql(stmt)

    with engine.connect() as conn:
        repo = SqlTaskRepository(conn)

        # 1. Deterministic UUID v5 check
        u1 = generate_task_uuid("alpha", "T-01")
        u2 = generate_task_uuid("alpha", "T-01")
        u_other = generate_task_uuid("beta", "T-01")
        assert u1 == u2
        assert u1 != u_other

        # 2. Number parsing
        assert parse_task_number("T-01") == 1
        assert parse_task_number("task-42") == 42
        assert parse_task_number("99") == 99

        # 3. Atomic next number
        assert repo.get_next_task_number("alpha") == 1

        # 4. Create tasks with auto-increment
        t1 = repo.create_task(project_id="alpha", title="First Task")
        assert t1["task_number"] == 1
        assert t1["legacy_id"] == "T-01"
        assert t1["version"] == 1

        t2 = repo.create_task(project_id="alpha", title="Second Task")
        assert t2["task_number"] == 2
        assert t2["legacy_id"] == "T-02"

        # Separate project has its own numbering sequence starting at 1
        t_beta = repo.create_task(project_id="beta", title="Beta First")
        assert t_beta["task_number"] == 1

        # List tasks
        alpha_tasks = repo.list_tasks("alpha")
        assert len(alpha_tasks) == 2
        assert alpha_tasks[0]["task_number"] == 1
        assert alpha_tasks[1]["task_number"] == 2


# ============================================================================
# 5. Optimistic Concurrency Control (Item 449)
# ============================================================================

def test_sql_task_repository_optimistic_locking_and_stale_version_conflict(tmp_path):
    db_file = tmp_path / "test_concurrency.db"
    engine = create_engine(f"sqlite:///{db_file}")

    ddl_statements = [
        "CREATE TABLE projects (id TEXT PRIMARY KEY, name TEXT, root_path TEXT)",
        """CREATE TABLE tasks (
            task_uuid TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            task_number INTEGER NOT NULL,
            legacy_id TEXT,
            title TEXT NOT NULL,
            mode TEXT DEFAULT 'coding',
            status TEXT DEFAULT 'todo',
            version INTEGER DEFAULT 1,
            steps_done INTEGER DEFAULT 0,
            steps_total INTEGER DEFAULT 1,
            depends_on_uuid TEXT,
            worktree TEXT,
            metadata TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (project_id, task_number)
        )""",
        "INSERT INTO projects (id, name, root_path) VALUES ('alpha', 'Alpha', '/alpha')",
    ]
    with engine.begin() as conn:
        for stmt in ddl_statements:
            conn.exec_driver_sql(stmt)

    with engine.connect() as conn:
        repo = SqlTaskRepository(conn)

        created = repo.create_task(project_id="alpha", title="Concurrency Target", legacy_id="T-10")
        task_id = created["task_uuid"]

        # 1. Update with expected version 1 -> succeeds, bumps to version 2
        updated = repo.update_task(project_id="alpha", task_id=task_id, expected_version=1, status="in_progress")
        assert updated["version"] == 2

        # 2. Concurrent update sending stale expected version 1 -> MUST raise TaskMutationConflict
        with pytest.raises(TaskMutationConflict) as exc_info:
            repo.update_task(project_id="alpha", task_id=task_id, expected_version=1, status="done")
        assert exc_info.value.code == "stale_task_version"

        # 3. Update with correct version 2 -> succeeds, bumps to version 3
        updated2 = repo.update_task(project_id="alpha", task_id=task_id, expected_version=2, status="done")
        assert updated2["version"] == 3

        # 4. Unknown task raises KeyError
        with pytest.raises(KeyError, match="not found"):
            repo.update_task(project_id="alpha", task_id="nonexistent-id", expected_version=1, status="done")


# ============================================================================
# 6. Dry-Run Importer, Reconciliation & Verification Digests (Item 451 & 448)
# ============================================================================

def test_postgres_dry_run_importer_reconciliation_and_digests(tmp_path):
    importer = PostgresDryRunImporter(conflict_policy="reject_collision")

    # 1. Test JSON board dry-run
    clean_board = {
        "project": "devcore",
        "tasks": [
            {"id": "T-01", "title": "Task One", "status": "done", "mode": "coding", "version": 1},
            {"id": "T-02", "title": "Task Two", "status": "todo", "mode": "coding", "version": 1},
        ],
    }
    report = importer.dry_run_json_board(clean_board)
    assert report.status == "ready"
    assert report.source_tasks_count == 2
    assert report.staged_tasks_count == 2
    assert report.collisions_count == 0
    assert len(report.task_identity_mappings) == 2
    assert report.source_content_digest == report.staged_content_digest

    # Verify deterministic UUID v5 assigned in report
    assert report.task_identity_mappings["T-01"]["task_uuid"] == str(generate_task_uuid("devcore", "T-01"))
    assert report.task_identity_mappings["T-01"]["task_number"] == 1

    # 2. Test Collision Detection on Duplicate Task Numbers within same project
    colliding_board = {
        "project": "devcore",
        "tasks": [
            {"id": "T-01", "title": "First", "status": "done"},
            {"id": "T-1", "title": "Duplicate One", "status": "in_progress"},  # Both parse to task_number 1!
        ],
    }
    collision_report = importer.dry_run_json_board(colliding_board)
    assert collision_report.status == "collision_detected"
    assert collision_report.collisions_count == 1
    assert collision_report.task_identity_mappings["T-1"]["collision"] is True
    assert "Collision on project 'devcore': task_number 1" in collision_report.discrepancies[0]

    # 3. Test SQLite dry-run with runtime_state classification
    sqlite_file = tmp_path / "candidate_with_state.db"
    conn = sqlite3.connect(sqlite_file)
    conn.execute("""
        CREATE TABLE tasks (
            id TEXT, project_id TEXT, title TEXT, mode TEXT, status TEXT,
            steps_done INTEGER, steps_total INTEGER, version INTEGER
        );
    """)
    conn.execute("""
        CREATE TABLE runtime_state (key TEXT PRIMARY KEY, value TEXT);
    """)
    conn.execute("INSERT INTO tasks VALUES ('T-05', 'devcore', 'Task Five', 'coding', 'todo', 0, 1, 1);")
    conn.execute("INSERT INTO runtime_state VALUES ('theme', 'dark');")  # preference_to_migrate
    conn.execute("INSERT INTO runtime_state VALUES ('active_task', 'T-05');")  # ephemeral_to_rebuild
    conn.execute("INSERT INTO runtime_state VALUES ('unusual_custom_key', 'foo');")  # ambiguous_needs_review
    conn.commit()
    conn.close()

    sql_report = importer.dry_run_sqlite(sqlite_file, project="devcore")
    assert sql_report.status == "ready"
    assert sql_report.source_tasks_count == 1
    assert sql_report.task_identity_mappings["T-05"]["task_number"] == 5

    # Check runtime_state classifications
    assert sql_report.runtime_state_classifications["theme"]["disposition"] == "preference_to_migrate"
    assert sql_report.runtime_state_classifications["active_task"]["disposition"] == "ephemeral_to_rebuild"
    assert sql_report.runtime_state_classifications["unusual_custom_key"]["disposition"] == "ambiguous_needs_review"


# ============================================================================
# 7. Post-Cutover Neutralization of Automatic Legacy Import (Item 452)
# ============================================================================

def test_neutralization_of_legacy_importer_post_cutover(tmp_path, monkeypatch):
    from devcore_engine.migrate_to_unified_db import DevCoreMigrator, is_legacy_import_disabled

    test_local = tmp_path / "local_root"
    test_local.mkdir()
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(test_local))

    # Initially enabled
    monkeypatch.delenv("DEVCORE_DISABLE_LEGACY_IMPORT", raising=False)
    assert is_legacy_import_disabled() is False

    # 1. Trigger via environment flag
    monkeypatch.setenv("DEVCORE_DISABLE_LEGACY_IMPORT", "1")
    assert is_legacy_import_disabled() is True

    fake_db = test_local / "test.db"
    migrator = DevCoreMigrator(data_root=tmp_path, db_path=fake_db)
    with pytest.raises(RuntimeError, match="permanently disabled post-cutover"):
        migrator.run_all()

    # 2. Trigger via cutover marker file
    monkeypatch.delenv("DEVCORE_DISABLE_LEGACY_IMPORT", raising=False)
    (test_local / ".cutover_complete").write_text("cutover 2026-10-10", encoding="utf-8")
    assert is_legacy_import_disabled() is True

    with pytest.raises(RuntimeError, match="permanently disabled post-cutover"):
        migrator.run_all()


def test_concurrent_task_creation_atomic_numbering(tmp_path):
    """P1 numbering: concurrent create_task calls must allocate distinct sequential numbers without unique constraint failure."""
    import concurrent.futures
    db_file = tmp_path / "concurrent_tasks.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"timeout": 30.0})

    ddl_statements = [
        "PRAGMA journal_mode=WAL;",
        """CREATE TABLE projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            root_path TEXT NOT NULL
        )""",
        """CREATE TABLE tasks (
            task_uuid TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(id),
            task_number INTEGER NOT NULL,
            legacy_id TEXT,
            title TEXT NOT NULL,
            mode TEXT DEFAULT 'coding',
            status TEXT DEFAULT 'todo',
            version INTEGER DEFAULT 1,
            steps_done INTEGER DEFAULT 0,
            steps_total INTEGER DEFAULT 1,
            depends_on_uuid TEXT,
            worktree TEXT,
            metadata TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (project_id, task_number)
        )""",
        "INSERT INTO projects (id, name, root_path) VALUES ('alpha', 'Alpha', '/alpha')",
    ]
    with engine.begin() as conn:
        for stmt in ddl_statements:
            conn.exec_driver_sql(stmt)

    num_tasks = 10
    created_tasks = []

    def create_one(idx):
        with engine.begin() as conn:
            repo = SqlTaskRepository(conn)
            return repo.create_task(project_id="alpha", title=f"Concurrent Task {idx}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(create_one, i) for i in range(num_tasks)]
        for f in concurrent.futures.as_completed(futures):
            created_tasks.append(f.result())

    assert len(created_tasks) == num_tasks
    numbers = sorted([t["task_number"] for t in created_tasks])
    assert numbers == list(range(1, num_tasks + 1))


def test_postgres_task_numbering_dialect_compilation_and_savepoint_contract():
    """Item 447/449: Qualify PostgreSQL target atomic numbering, row lock DDL, and savepoint retry contract."""
    from sqlalchemy.exc import IntegrityError

    # 1. Verify dialect compilation of row-level lock on projects
    lock_stmt = select(projects.c.id).where(projects.c.id == "alpha").with_for_update()
    compiled_lock = str(lock_stmt.compile(dialect=postgresql.dialect()))
    assert "FOR UPDATE" in compiled_lock
    assert "WHERE projects.id = " in compiled_lock

    # 2. Verify dialect compilation of next task number calculation
    next_stmt = select(func.coalesce(func.max(tasks.c.task_number), 0) + 1).where(
        tasks.c.project_id == "alpha"
    )
    compiled_next = str(next_stmt.compile(dialect=postgresql.dialect()))
    assert "coalesce(max(tasks.task_number)" in compiled_next
    assert "WHERE tasks.project_id = " in compiled_next

    # 3. Verify PostgreSQL session interaction contract:
    # create_task MUST issue row lock query on projects, calculate next number, and insert.
    executed_statements = []

    class MockPgSession:
        def __init__(self):
            self.savepoints = []
            self.attempt = 0

        def execute(self, stmt, params=None):
            # Compile statement to string for inspection
            stmt_sql = str(stmt.compile(dialect=postgresql.dialect()))
            executed_statements.append(stmt_sql)

            if "FOR UPDATE" in stmt_sql:
                mock_res = MagicMock()
                mock_res.scalar.return_value = "alpha"
                return mock_res
            elif "max(tasks.task_number)" in stmt_sql:
                mock_res = MagicMock()
                mock_res.scalar.return_value = 1 if self.attempt == 0 else 2
                return mock_res
            elif "INSERT INTO tasks" in stmt_sql:
                self.attempt += 1
                if self.attempt == 1:
                    # Simulate concurrent race collision in PostgreSQL
                    raise IntegrityError("duplicate key value violates unique constraint uq_tasks_project_task_number", params, None)
                mock_res = MagicMock()
                return mock_res
            return MagicMock()

        def begin_nested(self):
            sp = MagicMock()
            self.savepoints.append(sp)
            return sp

    pg_session = MockPgSession()
    repo = SqlTaskRepository(pg_session)

    result = repo.create_task(project_id="alpha", title="Postgres Qualified Task")

    assert result["task_number"] == 2
    assert result["legacy_id"] == "T-02"

    # Verify savepoint rollback occurred on attempt 1
    assert len(pg_session.savepoints) == 2
    pg_session.savepoints[0].rollback.assert_called_once()

    # Verify that FOR UPDATE was sent to PostgreSQL
    assert any("FOR UPDATE" in s for s in executed_statements)
    assert any("INSERT INTO tasks" in s for s in executed_statements)


