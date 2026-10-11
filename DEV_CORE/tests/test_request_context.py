"""Business operations use explicit, independent project contexts."""

import json
import os
import pytest

from devcore_engine.context import RequestContext
from devcore_engine.db import connect_db
from devcore_engine.lifecycle.endday import EndDayManager
from devcore_engine.lifecycle.session import SessionManager
from devcore_engine.services.tasks import TaskService


def test_two_sessions_ignore_client_preference_and_global_state(tmp_path):
    conn = connect_db(tmp_path / "devcore.db")
    tasks = TaskService(conn)
    tasks.add_task("alpha task", project_id="alpha")
    tasks.add_task("beta task", project_id="beta")
    conn.execute("INSERT INTO runtime_state(key,value) VALUES ('active_project','beta')")
    conn.commit()

    first, second = SessionManager(conn), SessionManager(conn)
    first.set_active_project("beta")
    second.set_active_project("alpha")
    alpha = RequestContext(project_id="alpha", user_id="user-a", session_id="session-a", trace_id="trace-a")
    beta = RequestContext(project_id="beta", user_id="user-b", session_id="session-b", trace_id="trace-b")

    started_a = first.start_session(alpha)
    started_b = second.start_session(beta)
    ended_a = first.end_session(alpha)
    ended_b = second.end_session(beta)

    assert (started_a["project"], started_a["active_task"]["id"], started_a["trace_id"]) == ("alpha", "T-01", "trace-a")
    assert (started_b["project"], started_b["active_task"]["id"], started_b["trace_id"]) == ("beta", "T-01", "trace-b")
    assert ended_a["project"] == "alpha" and ended_b["project"] == "beta"
    assert tasks.get_task("T-01", "alpha")["status"] == "in_progress"
    assert tasks.get_task("T-01", "beta")["status"] == "in_progress"
    rows = conn.execute(
        "SELECT event_type,project,correlation_id FROM bus_events "
        "WHERE event_type IN ('SessionStarted','SessionEnded') ORDER BY rowid"
    ).fetchall()
    assert [tuple(row) for row in rows] == [
        ("SessionStarted", "alpha", "trace-a"),
        ("SessionStarted", "beta", "trace-b"),
        ("SessionEnded", "alpha", "trace-a"),
        ("SessionEnded", "beta", "trace-b"),
    ]
    assert conn.execute("SELECT value FROM runtime_state WHERE key='active_project'").fetchone()[0] == "beta"
    assert first.get_active_project() == "beta"
    assert second.get_active_project() == "alpha"
    conn.close()


def test_context_requires_project_before_session_mutation(tmp_path):
    conn = connect_db(tmp_path / "devcore.db")
    manager = SessionManager(conn)
    for invalid in (None, "", "../beta", "alpha/beta"):
        with pytest.raises(ValueError):
            manager.start_session(invalid)
    with pytest.raises(ValueError):
        RequestContext(project_id="alpha", trace_id=" ")
    assert conn.execute("SELECT COUNT(*) FROM bus_events").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0
    conn.close()


def test_session_manager_resolves_or_refuses_active_project(tmp_path, monkeypatch):
    conn = connect_db(tmp_path / "devcore.db")
    sm = SessionManager(conn)

    # 1. When explicit on manager instance
    sm.set_active_project("explicit_proj")
    assert sm.get_active_project() == "explicit_proj"

    # 2. When env var is set
    sm_fresh = SessionManager(conn)
    monkeypatch.setenv("DEVCORE_ACTIVE_PROJECT_NAME", "env_proj")
    assert sm_fresh.get_active_project() == "env_proj"

    # Invalid env var rejected
    monkeypatch.setenv("DEVCORE_ACTIVE_PROJECT_NAME", "../traversal")
    with pytest.raises(ValueError, match="invalid project_id"):
        sm_fresh.get_active_project()

    # 3. When directory has .devcore/project.json
    monkeypatch.delenv("DEVCORE_ACTIVE_PROJECT_NAME", raising=False)
    project_dir = tmp_path / "my_project"
    manifest = project_dir / ".devcore" / "project.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"name": "dir_proj"}), encoding="utf-8")
    monkeypatch.chdir(project_dir)
    assert sm_fresh.get_active_project() == "dir_proj"

    # 4. When no manifest and no env var: refuses implicit fallback to "devcore"
    isolated_dir = tmp_path / "empty_dir"
    isolated_dir.mkdir()
    monkeypatch.chdir(isolated_dir)
    with pytest.raises(ValueError, match="No active project context found"):
        sm_fresh.get_active_project()

    conn.close()


def test_endday_accepts_request_context_and_correlates_event(tmp_path):
    conn = connect_db(tmp_path / "devcore.db")
    tasks = TaskService(conn)
    tasks.add_task("Gamma task done", project_id="gamma")
    tasks.next_task("gamma")
    tasks.complete_task("T-01", project_id="gamma")

    edm = EndDayManager(conn)
    ctx = RequestContext(project_id="gamma", trace_id="trace-gamma-123")
    res = edm.run_endday(ctx)

    assert res["status"] == "success"
    assert res["project"] == "gamma"
    assert res["done_tasks_count"] == 1
    assert res["trace_id"] == "trace-gamma-123"

    row = conn.execute(
        "SELECT event_type, project, correlation_id FROM bus_events WHERE event_type='EndDayCompleted'"
    ).fetchone()
    assert tuple(row) == ("EndDayCompleted", "gamma", "trace-gamma-123")

    # Invalid context or project is rejected
    for invalid in (None, "", "../bad", "a/b"):
        with pytest.raises(ValueError):
            edm.run_endday(invalid)

    conn.close()

