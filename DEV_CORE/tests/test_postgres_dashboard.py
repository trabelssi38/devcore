"""Project isolation and output safety for the team Cockpit projection."""

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import sys

import pytest

API_ROOT = Path(__file__).resolve().parents[1] / "API"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from devcore_api.team_cockpit import render_team_cockpit
from devcore_api.team_login import render_team_login

from devcore_engine.security.identity import Principal, ProjectAccessDenied
from devcore_engine.services.postgres_dashboard import PostgresDashboardProjection
from devcore_engine.services.global_stack_monitor import global_stack_health, render_global_stack_health


class Cursor:
    def __init__(self):
        now = datetime.now(timezone.utc)
        self.answers = [(1,), [("T-1", "uuid", "<script>alert(1)</script>",
                                "active", "coding", 2, 0, 1, now)],
                        [("run-1", "running", "<img src=x>", now)],
                        [("<script>event</script>", now)],
                        [("schedule-1", "<script>job</script>", "active", "*/5 * * * *", "UTC", now, None, "true")],
                        [("<img src=x>", "dispatched", "queued", now)],
                        [("<script>plugin</script>", "1.0", True)],
                        [("<img src=x>", 2)],
                        (100, 5, 50)]
        self.statements = []

    def execute(self, sql, params):
        self.statements.append((sql, params))

    def fetchone(self):
        return self.answers.pop(0)

    def fetchall(self):
        return self.answers.pop(0)


def test_dashboard_bounds_project_reads_and_escapes_database_text(monkeypatch):
    reader = PostgresDashboardProjection("postgresql://app@127.0.0.1/fixture")
    cursor = Cursor()

    @contextmanager
    def transaction(project):
        assert project == "alpha"
        yield cursor

    monkeypatch.setattr(reader, "_transaction", transaction)
    data = reader.snapshot(Principal("user", "credential", "alpha", "task.read"))
    assert data["project"] == "alpha"
    assert data["counts"] == {"tasks": 1, "shown_tasks": 1, "runs": 1}
    assert "<script>" not in str(data)
    assert "<img" not in str(data)
    assert "&lt;script&gt;" in data["sections"]["tasks_pipeline"]
    assert 'data-task-id="T-1"' in data["sections"]["tasks_pipeline"]
    assert 'data-version="2"' in data["sections"]["tasks_pipeline"]
    assert "&lt;script&gt;job&lt;/script&gt;" in data["sections"]["automation_hooks"]
    assert "&lt;img src=x&gt;" in data["sections"]["automation_hooks"]
    assert "exécution qualifiée : oui" in data["sections"]["automation_hooks"]
    assert "&lt;script&gt;plugin&lt;/script&gt;" in data["sections"]["plugin_status"]
    assert "&lt;img src=x&gt; · 2" in data["sections"]["context_composition"]
    assert "100 jetons modèle/jour" in data["sections"]["metrics_service_summary"]
    assert all(params == ("alpha",) for _, params in cursor.statements)
    assert "LIMIT 60" in cursor.statements[1][0]
    assert "LIMIT 10" in cursor.statements[2][0]
    assert "LIMIT 20" in cursor.statements[4][0]
    assert "LIMIT 10" in cursor.statements[5][0]
    assert "LIMIT 20" in cursor.statements[6][0]
    assert "LIMIT 20" in cursor.statements[7][0]


def test_dashboard_rejects_non_read_principal_before_database(monkeypatch):
    reader = PostgresDashboardProjection("postgresql://app@127.0.0.1/fixture")
    monkeypatch.setattr(reader, "_transaction", lambda _: (_ for _ in ()).throw(
        AssertionError("Database opened")))
    with pytest.raises(ProjectAccessDenied):
        reader.snapshot(Principal("user", "credential", "alpha", "task.mutate"))


def test_html_render_escapes_project_in_script_context():
    snapshot = {
        "project": '</script><script>alert(1)</script>',
        "sections": {name: "" for name in (
            "project_cards", "tasks_pipeline", "services_monitoring", "automation_hooks",
            "token_activity_report", "context_composition", "metrics_service_summary",
            "event_bus_recent", "knowledge_graph_summary", "plugin_status")},
        "task_details": {}, "task_interactions": {}, "token_metrics": {},
    }
    directory = Path(__file__).resolve().parents[1] / "Dashboard"
    for terminal in (False, True):
        html = render_team_cockpit(directory, snapshot, terminal=terminal)
        assert '</script><script>alert(1)</script>' not in html
        assert "\\u003c/script\\u003e" in html
        assert "{{PROJECT_CARDS}}" not in html
        assert "X-CSRF-Token" in html
        assert "?project='+encodeURIComponent(window.devcoreActiveProject)" in html
        if terminal:
            assert 'id="api-ok">:20131' in html
            assert 'SCHEDULER <span class="v-ok">ACTIVE' not in html
            assert 'REPOWISE <span class="v-cyan">MCP' not in html


def test_login_escapes_project_and_uses_same_origin_session():
    html = render_team_login('</strong><script>alert(1)</script>')
    assert '</strong><script>alert(1)</script>' not in html
    assert '&lt;/strong&gt;&lt;script&gt;' in html
    assert "fetch('/api/auth/session'" in html
    assert "location.assign('/cockpit?project='" in html


def test_global_stack_monitor_requires_fresh_ready_heartbeat(tmp_path):
    import json
    from datetime import timedelta

    path = tmp_path / "manifest.json"
    now = datetime.now(timezone.utc)
    names = ("router", "headroom-native", "headroom-auxiliary", "gateway", "scheduler")
    state = {"status": "ready", "heartbeat_utc": now.isoformat(),
             "processes": {name: {"pid": 1} for name in names},
             "health": {name: True for name in names}}
    path.write_text(json.dumps(state), encoding="utf-8")
    result = global_stack_health(str(path), now=now)
    assert result["status"] == "ready"
    assert "Scheduler PostgreSQL · en ligne" in render_global_stack_health(result)
    assert "RepoWise" not in render_global_stack_health(result)
    state["health"]["scheduler"] = False
    path.write_text(json.dumps(state), encoding="utf-8")
    degraded = global_stack_health(str(path), now=now)
    assert degraded["status"] == "degraded"
    assert "Scheduler PostgreSQL · indisponible" in render_global_stack_health(degraded)
    assert global_stack_health(str(path), now=now + timedelta(seconds=9))["status"] == "unavailable"
    state["status"] = "stopping"
    path.write_text(json.dumps(state), encoding="utf-8")
    assert global_stack_health(str(path), now=now)["status"] == "unavailable"
