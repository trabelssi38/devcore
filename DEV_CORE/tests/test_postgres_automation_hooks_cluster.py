"""Real RLS and idempotency checks on an isolated PostgreSQL cluster."""

from pathlib import Path
import importlib.util
import json
import socket
import subprocess
from urllib.parse import urlparse

import pg8000.dbapi
import pytest

from devcore_engine.security.identity import Principal, READ, WRITE, ProjectAccessDenied
from devcore_engine.services.postgres_automation_hooks import PostgresAutomationHooks


BIN = Path("C:/Program Files/PostgreSQL/17/bin")
PLATFORM = Path(__file__).resolve().parents[1]


def command(*args):
    subprocess.run(list(map(str, args)), check=True, timeout=120,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


@pytest.fixture
def cluster(tmp_path, monkeypatch):
    if not (BIN / "initdb.exe").is_file():
        pytest.skip("PostgreSQL 17 binaries required")
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(tmp_path / "local"))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(tmp_path / "data"))
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    data = tmp_path / "postgres"
    command(BIN / "initdb.exe", "-D", data, "-U", "fixture_owner", "-A", "trust", "--encoding=UTF8")
    try:
        command(BIN / "pg_ctl.exe", "-D", data, "-l", tmp_path / "postgres.log",
                "-o", f"-h 127.0.0.1 -p {port}", "start", "-w")
        psql = (BIN / "psql.exe", "-h", "127.0.0.1", "-p", port,
                "-U", "fixture_owner", "-d", "postgres", "-v", "ON_ERROR_STOP=1")
        command(*psql, "-c", "CREATE ROLE devcore_app LOGIN NOBYPASSRLS")
        command(*psql, "-f", PLATFORM / "devcore_engine/persistence/schema.sql")
        command(*psql, "-f", PLATFORM / "devcore_engine/persistence/automation_hook_events.sql")
        admin = pg8000.dbapi.connect(user="fixture_owner", host="127.0.0.1",
                                     port=port, database="postgres")
        try:
            cursor = admin.cursor()
            cursor.execute("GRANT USAGE ON SCHEMA public TO devcore_app")
            cursor.execute("GRANT SELECT ON projects TO devcore_app")
            cursor.execute("GRANT SELECT ON tasks TO devcore_app")
            cursor.execute("GRANT SELECT,INSERT,UPDATE ON runs TO devcore_app")
            cursor.execute("GRANT SELECT,INSERT ON events TO devcore_app")
            cursor.execute("GRANT SELECT,INSERT,UPDATE ON schedules TO devcore_app")
            cursor.execute("GRANT SELECT,INSERT ON schedule_history TO devcore_app")
            cursor.execute("INSERT INTO organizations(id,name) VALUES ('o','Fixture')")
            cursor.execute("INSERT INTO workspaces(id,organization_id,name) VALUES ('w','o','Fixture')")
            for project in ("alpha", "beta"):
                root = tmp_path / project
                root.mkdir()
                command("git", "init", "-q", root)
                cursor.execute("""INSERT INTO projects(id,workspace_id,name,root_path,status)
                    VALUES (%s,'w',%s,%s,'active')""", (project, project, str(root)))
            cursor.execute("""INSERT INTO projects(id,workspace_id,name,root_path,status)
                VALUES ('archived','w','Archived',%s,'archived')""", (str(tmp_path / "alpha"),))
            cursor.execute("""INSERT INTO tasks(task_uuid,project_id,task_number,legacy_id,title,status)
                VALUES (gen_random_uuid(),'alpha',1,'T-01','Active alpha task','active'),
                       (gen_random_uuid(),'beta',1,'T-01','Active beta task','active')""")
            admin.commit()
        finally:
            admin.close()
        yield f"postgresql://devcore_app@127.0.0.1:{port}/postgres"
    finally:
        command(BIN / "pg_ctl.exe", "-D", data, "stop", "-m", "fast", "-w")


def test_project_isolation_idempotency_and_terminal_result(cluster):
    store = PostgresAutomationHooks(cluster)
    store.verify_ready()
    writer_a = Principal("alice", "credential", "alpha", WRITE)
    writer_b = Principal("bob", "credential", "beta", WRITE)
    reader_a = Principal("alice", "credential", "alpha", READ)
    reader_b = Principal("bob", "credential", "beta", READ)

    first, created = store.start(writer_a, "alpha", "session_start", "codex", "session-1")
    assert created
    assert store.start(writer_a, "alpha", "session_start", "codex", "session-1") == (first, False)
    second, created = store.start(writer_b, "beta", "session_start", "codex", "session-1")
    assert created and second != first
    with pytest.raises(ProjectAccessDenied):
        store.start(writer_b, "alpha", "session_start", "codex", "session-1")
    with pytest.raises(ProjectAccessDenied):
        store.start(Principal("alice", "credential", "archived", WRITE),
                    "archived", "session_start", "codex", "session-1")

    resumed = PostgresAutomationHooks(cluster)
    assert resumed.finish(writer_a, "alpha", first, "succeeded")
    assert not store.finish(writer_a, "alpha", first, "succeeded")
    assert not store.finish(writer_b, "beta", first, "failed")
    assert [(row["id"], row["status"]) for row in store.recent(reader_a, "alpha")] == [
        (first, "succeeded")]
    assert [row["id"] for row in store.recent(reader_b, "beta")] == [second]


def test_cockpit_automation_queries_use_current_project_rls(cluster):
    from devcore_engine.services.postgres_dashboard import (
        PostgresDashboardProjection, _automation_panel, _read_automation)

    store = PostgresAutomationHooks(cluster)
    alpha = Principal("alice", "credential", "alpha", WRITE)
    beta = Principal("bob", "credential", "beta", WRITE)
    first, _ = store.start(alpha, "alpha", "session_start", "codex", "alpha-session")
    store.finish(alpha, "alpha", first, "succeeded")
    store.start(beta, "beta", "session_end", "claude", "beta-session")
    reader = PostgresDashboardProjection(cluster)
    with reader._transaction("alpha") as cursor:
        hooks, hook_successes, jobs, successes, history, schedule_successes = _read_automation(cursor, "alpha")
    assert [(row[0], row[1], row[3]) for row in hooks] == [("session_start", "alice", "succeeded")]
    assert len(hook_successes) == 1
    rendered = _automation_panel(hooks, hook_successes, jobs, successes, [], history, schedule_successes)
    assert "alice" in rendered and "bob" not in rendered
    with reader._transaction("beta") as cursor:
        hooks, hook_successes, jobs, successes, history, schedule_successes = _read_automation(cursor, "beta")
    assert [(row[0], row[1]) for row in hooks] == [("session_end", "bob")]
    assert not hook_successes


def test_hook_migration_restores_full_backup_before_install(cluster, tmp_path):
    script = PLATFORM / "Scripts/apply_automation_hook_events_schema.py"
    spec = importlib.util.spec_from_file_location("hook_migration_fixture", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    parsed = urlparse(cluster)
    admin = pg8000.dbapi.connect(user="fixture_owner", host="127.0.0.1",
                                 port=parsed.port, database="postgres")
    try:
        cursor = admin.cursor()
        cursor.execute("DROP TABLE automation_hook_events")
        admin.commit()
    finally:
        admin.close()
    config = tmp_path / "fixture-service.json"
    config.write_text(json.dumps({"environment": {"DEVCORE_DATABASE_URL": cluster}}),
                      encoding="utf-8")
    backups = tmp_path / "private-backups"
    backups.mkdir()
    result = module.apply(config, backups, "postgres", admin_user="fixture_owner", password="")
    assert result["status"] == "automation_hook_schema_verified"
    assert result["restore_rehearsal"] == "restored_and_schema_verified"
    assert Path(result["backup"]).is_file()
    assert module._ready(module._options(config, "postgres"))


def test_team_lifecycle_replays_session_and_never_mutates_tasks(cluster):
    from devcore_engine.services.postgres_automation_lifecycle import PostgresAutomationLifecycle

    service = PostgresAutomationLifecycle(cluster)
    alice = Principal("alice", "credential", "alpha", WRITE)
    bob = Principal("bob", "credential", "beta", WRITE)
    before = service._task_snapshot("alpha")
    started = service.execute(alice, "alpha", "session_start", "codex", session="s-1")
    assert started["created"] and started["event"]["status"] == "succeeded"
    assert started["event"]["details"]["active_task"]["id"] == "T-01"
    assert service.execute(alice, "alpha", "session_start", "codex", session="s-1")["created"] is False
    ended = service.execute(alice, "alpha", "session_end", "codex", session="s-1")
    assert ended["event"]["details"]["tasks_completed_since_start"] == 0
    assert service.execute(alice, "alpha", "session_end", "codex", session="s-1")["created"] is False
    assert service._task_snapshot("alpha") == before
    assert service.execute(bob, "beta", "session_start", "codex", session="s-1")["created"]
    with pytest.raises(ProjectAccessDenied):
        service.execute(bob, "alpha", "session_start", "codex", session="s-2")
    assert [row["hook"] for row in service.recent(Principal("alice", "credential", "alpha", READ), "alpha")] == [
        "session_end", "session_start"]


def test_git_commit_is_verified_and_tool_report_is_labeled(cluster, tmp_path):
    from devcore_engine.services.postgres_automation_lifecycle import (
        HookOperationFailed, PostgresAutomationLifecycle,
    )

    service = PostgresAutomationLifecycle(cluster)
    alice = Principal("alice", "credential", "alpha", WRITE)
    root = tmp_path / "alpha"
    (root / "file.txt").write_text("fixture", encoding="utf-8")
    command("git", "-C", root, "add", "file.txt")
    command("git", "-C", root, "-c", "user.name=Fixture", "-c",
            "user.email=fixture@example.invalid", "commit", "-qm", "finish T-01")
    sha = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], check=True,
                         capture_output=True, text=True).stdout.strip()
    result = service.execute(alice, "alpha", "git_commit", "git", commit=sha)
    assert result["event"]["details"]["verified"] == "git_reachable"
    assert service.execute(alice, "alpha", "git_commit", "git", commit=sha)["created"] is False
    with pytest.raises(HookOperationFailed):
        service.execute(alice, "alpha", "git_commit", "git", commit="0" * 40)
    tool = service.execute(alice, "alpha", "tool_use", "codex", session="s-2",
                           tool="Bash", reported_outcome="succeeded", occurrence="call-1")
    assert tool["event"]["details"]["verification"] == "client_report_only"
    assert service._task_snapshot("alpha")["active_task"]["status"] == "active"


def test_http_hook_routes_require_scoped_identity(cluster, tmp_path, monkeypatch):
    import sys
    from fastapi.testclient import TestClient
    from devcore_engine.security.identity import add_user, initialize_store, issue_credential, set_membership

    api_dir = PLATFORM / "API"
    if str(api_dir) not in sys.path:
        sys.path.insert(0, str(api_dir))
    from devcore_api import create_app
    from devcore_api.ports import PostgresTaskRepository

    identity = tmp_path / "identity.db"
    initialize_store(identity)
    add_user(identity, "alice")
    set_membership(identity, "alice", "alpha", "owner")
    _, token = issue_credential(identity, "alice", ["alpha"], [READ, WRITE])
    monkeypatch.setenv("DEVCORE_IDENTITY_STORE", str(identity))
    monkeypatch.setenv("DEVCORE_DATABASE_URL", cluster)
    monkeypatch.setenv("DEVCORE_TASK_READ_MODE", "postgres")
    monkeypatch.setenv("DEVCORE_IDENTITY_READ_MODE", "sqlite")
    client = TestClient(create_app(task_repository=PostgresTaskRepository(cluster),
                                   require_auth=True, start_run_worker=False))
    body = {"project": "alpha", "hook": "session_start", "source": "codex", "session": "http-1"}
    assert client.post("/api/v1/automation/hooks", json=body).status_code == 401
    headers = {"Authorization": f"Bearer {token}"}
    started = client.post("/api/v1/automation/hooks", json=body, headers=headers)
    assert started.status_code == 200, started.text
    assert started.json()["event"]["status"] == "succeeded"
    assert client.post("/api/v1/automation/hooks", json=body, headers=headers).json()["created"] is False
    assert client.get("/api/v1/automation/hooks", params={"project": "alpha"},
                      headers=headers).json()["events"][0]["hook"] == "session_start"
    assert client.post("/api/v1/automation/hooks", json={**body, "project": "beta"},
                       headers=headers).status_code == 403
    root = tmp_path / "alpha"
    (root / "http.txt").write_text("http", encoding="utf-8")
    command("git", "-C", root, "add", "http.txt")
    command("git", "-C", root, "-c", "user.name=Fixture", "-c",
            "user.email=fixture@example.invalid", "commit", "-qm", "http scan")
    assert client.post("/api/v1/automation/jobs/git-scan", json={"project": "alpha"}).status_code == 401
    submitted = client.post("/api/v1/automation/jobs/git-scan", json={"project": "alpha"}, headers=headers)
    assert submitted.status_code == 200 and submitted.json()["created"]
    assert client.post("/api/v1/automation/jobs/git-scan", json={"project": "beta"},
                       headers=headers).status_code == 403
    fake_executable = tmp_path / "fake-repowise.exe"
    fake_executable.touch()
    monkeypatch.setenv("DEVCORE_REPOWISE_EXE", str(fake_executable))
    sha = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                         check=True, capture_output=True, text=True).stdout.strip()
    commit_hook = client.post("/api/v1/automation/hooks", json={"project": "alpha",
                              "hook": "git_commit", "source": "git", "commit": sha}, headers=headers)
    assert commit_hook.status_code == 200, commit_hook.text
    assert commit_hook.json()["jobs"]["git_scan"]["run_id"] == submitted.json()["run_id"]
    assert commit_hook.json()["jobs"]["repowise_index"]["created"]
    daily = {"project": "alpha", "timezone": "Europe/Paris", "hour": 9, "minute": 0}
    assert client.post("/api/v1/automation/jobs/daily-metrics", json=daily,
                       headers=headers).status_code == 200
    assert client.post("/api/v1/automation/jobs/daily-metrics", json={**daily, "project": "beta"},
                       headers=headers).status_code == 403
    assert client.delete("/api/v1/automation/jobs/daily-metrics", params={"project": "alpha"},
                         headers=headers).status_code == 200


def test_git_scan_job_has_durable_run_and_scoped_history(cluster, tmp_path):
    import json
    from devcore_engine.runs.engine import DurableRunEngine
    from devcore_engine.runs.postgres_store import PostgresRunStore
    from devcore_engine.services.postgres_git_scan_jobs import PostgresGitScanJobs

    root = tmp_path / "alpha"
    (root / "scan.txt").write_text("scan fixture", encoding="utf-8")
    command("git", "-C", root, "add", "scan.txt")
    command("git", "-C", root, "-c", "user.name=Fixture", "-c",
            "user.email=fixture@example.invalid", "commit", "-qm", "[T-01] [T-02] scan fixture")
    service = PostgresGitScanJobs(cluster)
    alice = Principal("alice", "credential", "alpha", WRITE)
    first = service.submit(alice, "alpha")
    assert first["created"] and first["status"] == "queued"
    assert service.submit(alice, "alpha") == {**first, "created": False}
    (root / "next.txt").write_text("next revision", encoding="utf-8")
    command("git", "-C", root, "add", "next.txt")
    command("git", "-C", root, "-c", "user.name=Fixture", "-c",
            "user.email=fixture@example.invalid", "commit", "-qm", "next revision")
    overlapping = service.submit(alice, "alpha")
    assert overlapping["run_id"] == first["run_id"] and not overlapping["created"]
    with pytest.raises(ProjectAccessDenied):
        service.submit(Principal("bob", "credential", "beta", WRITE), "alpha")
    engine = DurableRunEngine(store=PostgresRunStore(cluster), local_root=tmp_path / "runlocal")
    completed = engine.step("alpha")
    assert completed is not None and completed.id == first["run_id"]
    assert completed.status == "succeeded", completed.error
    report = json.loads(completed.output)
    assert report["missing_task_tags"] == ["T-02"]
    assert report["task_changes"] == 0
    second = service.submit(alice, "alpha")
    assert second["created"] and second["run_id"] != first["run_id"]
    assert engine.step("alpha").status == "succeeded"
    with service._transaction("alpha") as cursor:
        cursor.execute("SELECT event_type FROM events WHERE project_id='alpha' AND run_id=%s ORDER BY created_at",
                       (first["run_id"],))
        assert {row[0] for row in cursor.fetchall()} == {"project_job.submitted", "project_job.finished"}
    with service._transaction("beta") as cursor:
        cursor.execute("SELECT count(*) FROM events WHERE project_id='beta'")
        assert cursor.fetchone()[0] == 0


def test_daily_schedule_has_snapshot_history_and_nonoverlap(cluster, tmp_path):
    from datetime import UTC, datetime, timedelta
    import json
    from devcore_engine.runs.engine import DurableRunEngine
    from devcore_engine.runs.postgres_schedules import PostgresScheduleDispatcher
    from devcore_engine.runs.postgres_store import PostgresRunStore
    from devcore_engine.services.postgres_daily_metrics_schedules import PostgresDailyMetricsSchedules

    dispatcher = PostgresScheduleDispatcher(cluster)
    registration = PostgresDailyMetricsSchedules(cluster)
    alice = Principal("alice", "credential", "alpha", WRITE)
    enrolled = registration.register(alice, "alpha", timezone="Europe/Paris", hour=9, minute=0)
    assert enrolled["created"] and enrolled["status"] == "active"
    assert not registration.register(alice, "alpha", timezone="Europe/Paris", hour=9, minute=0)["created"]
    with pytest.raises(ProjectAccessDenied):
        registration.register(Principal("bob", "credential", "beta", WRITE), "alpha",
                              timezone="Europe/Paris", hour=9, minute=0)
    now = datetime.now(UTC).replace(second=0, microsecond=0)
    due = now - timedelta(minutes=2)
    with dispatcher._transaction("alpha") as cursor:
        cursor.execute("UPDATE schedules SET next_run_at=%s WHERE id=%s",
                       (due, enrolled["schedule_id"]))
    first = dispatcher.poll_once(now)
    assert len(first) == 1 and first[0]["project"] == "alpha"
    run_id = first[0]["run_id"]
    with dispatcher._transaction("alpha") as cursor:
        cursor.execute("UPDATE schedules SET next_run_at=%s WHERE id=%s", (due, enrolled["schedule_id"]))
    overlap = dispatcher.poll_once(now)
    assert overlap[0]["status"] == "skipped_overlap"
    with dispatcher._transaction("alpha") as cursor:
        cursor.execute("SELECT count(*) FROM runs WHERE project_id='alpha' AND metadata->>'schedule_id'=%s",
                       (enrolled["schedule_id"],))
        assert cursor.fetchone()[0] == 1
    engine = DurableRunEngine(store=PostgresRunStore(cluster), local_root=tmp_path / "daily-runs")
    completed = engine.step("alpha")
    assert completed is not None and completed.status == "succeeded", getattr(completed, "error", "")
    report = json.loads(completed.output)
    assert report["project"] == "alpha" and report["task_changes"] == 0
    assert set(report["metrics"]) == {"tasks_created", "tasks_completed", "runs_succeeded", "runs_failed"}
    with dispatcher._transaction("alpha") as cursor:
        cursor.execute("SELECT event_type,status FROM schedule_history WHERE run_id=%s", (run_id,))
        assert {tuple(row) for row in cursor.fetchall()} == {("dispatched", "queued"), ("finished", "succeeded")}
        cursor.execute("SELECT count(*) FROM schedule_history WHERE schedule_id=%s AND status='skipped'",
                       (enrolled["schedule_id"],))
        assert cursor.fetchone()[0] == 1
        cursor.execute("UPDATE schedules SET next_run_at=%s WHERE id=%s",
                       (due + timedelta(minutes=1), enrolled["schedule_id"]))
    retry = dispatcher.poll_once(now)
    assert len(retry) == 1 and retry[0]["run_id"] != run_id
    failed_run = PostgresRunStore(cluster)
    assert failed_run.claim_run(retry[0]["run_id"], "worker-failed") is not None
    assert failed_run.complete_run(retry[0]["run_id"], "worker-failed", exit_code=2).status == "failed"
    with dispatcher._transaction("alpha") as cursor:
        cursor.execute("SELECT status FROM schedule_history WHERE run_id=%s AND event_type='finished'",
                       (retry[0]["run_id"],))
        assert cursor.fetchone()[0] == "failed"
        cursor.execute("UPDATE schedules SET next_run_at=%s WHERE id=%s",
                       (due + timedelta(minutes=1, seconds=30), enrolled["schedule_id"]))
    interrupted = dispatcher.poll_once(now)
    assert len(interrupted) == 1
    assert failed_run.claim_run(interrupted[0]["run_id"], "worker-interrupted") is not None
    with dispatcher._transaction("alpha") as cursor:
        cursor.execute("""UPDATE runs SET attempt_number=3,heartbeat_at=now()-interval '1 hour'
            WHERE id=%s AND project_id='alpha'""", (interrupted[0]["run_id"],))
    assert interrupted[0]["run_id"] in failed_run.recover_stale_or_interrupted(15)
    with dispatcher._transaction("alpha") as cursor:
        cursor.execute("SELECT status FROM schedule_history WHERE run_id=%s AND event_type='finished'",
                       (interrupted[0]["run_id"],))
        assert cursor.fetchone()[0] == "timed_out"
    with dispatcher._transaction("beta") as cursor:
        cursor.execute("SELECT count(*) FROM schedule_history")
        assert cursor.fetchone()[0] == 0
    assert registration.disable(alice, "alpha")["status"] == "disabled"


def test_repowise_submission_deduplicates_and_records_terminal_result(cluster, tmp_path, monkeypatch):
    import json
    from devcore_engine.runs.engine import DurableRunEngine
    from devcore_engine.runs.postgres_store import PostgresRunStore
    from devcore_engine.services.postgres_repowise_jobs import PostgresRepoWiseJobs

    root = tmp_path / "alpha"
    (root / "index.txt").write_text("index fixture", encoding="utf-8")
    command("git", "-C", root, "add", "index.txt")
    command("git", "-C", root, "-c", "user.name=Fixture", "-c",
            "user.email=fixture@example.invalid", "commit", "-qm", "index fixture")
    fake_executable = tmp_path / "fake-repowise.cmd"
    fake_executable.write_text("""@echo off
setlocal EnableDelayedExpansion
if "%1"=="update" (
  echo refreshed>"%~dp0indexed.marker"
  exit /b 0
)
for /f "delims=" %%h in ('git rev-parse HEAD') do set "HASH=%%h"
if not exist "%~dp0indexed.marker" set "HASH=0000000000000000000000000000000000000000"
echo {"indexed":true,"state":{"last_sync_commit":"!HASH!"},"index_scope":{"file_pages":{"omitted":0}}}
""", encoding="utf-8")
    monkeypatch.setenv("DEVCORE_REPOWISE_EXE", str(fake_executable))
    service = PostgresRepoWiseJobs(cluster)
    alice = Principal("alice", "credential", "alpha", WRITE)
    first = service.submit(alice, "alpha")
    assert first["created"] and first["status"] == "queued"
    assert service.submit(alice, "alpha")["run_id"] == first["run_id"]
    with pytest.raises(ProjectAccessDenied):
        service.submit(Principal("bob", "credential", "beta", WRITE), "alpha")
    engine = DurableRunEngine(store=PostgresRunStore(cluster), local_root=tmp_path / "repowise-runs")
    completed = engine.step("alpha")
    assert completed is not None and completed.status == "succeeded", getattr(completed, "error", "")
    assert json.loads(completed.output)["indexed_commit"]
    assert service.submit(alice, "alpha")["created"] is False
    with service._transaction("alpha") as cursor:
        cursor.execute("SELECT event_type FROM events WHERE project_id='alpha' AND run_id=%s", (first["run_id"],))
        assert {row[0] for row in cursor.fetchall()} == {"project_job.submitted", "project_job.finished"}
