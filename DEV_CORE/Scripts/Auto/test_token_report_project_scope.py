"""Keep token attribution on verified project boards and the local database."""

import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).with_name("token_report.py")


def load_report():
    spec = importlib.util.spec_from_file_location("token_report_project_scope", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_foreign_board_never_attributes_a_task_to_directory_project(tmp_path, monkeypatch):
    data = tmp_path / "data"
    local = tmp_path / "local"
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(data))
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(local))
    alpha = data / "Memory" / "alpha"
    alpha.mkdir(parents=True)
    board = alpha / "tasks.json"
    board.write_text(json.dumps({"project": "beta", "current_task": "T-01", "tasks": [
        {"id": "T-01", "project": "beta", "status": "active"}]}), encoding="utf-8")
    report = load_report()
    _, mapping = report.discover_projects(data / "Memory")
    assert "T-01" not in mapping
    assert report.get_active_task_for_project("alpha") is None
    assert report.get_active_task_for_project("../beta") is None

    board.write_text(json.dumps({"project": "alpha", "current_task": "T-02", "tasks": [
        {"id": "T-01", "project": "beta", "status": "active"},
        {"id": "T-02", "project": "alpha", "status": "in_progress"}]}), encoding="utf-8")
    report._active_task_cache.clear()
    _, mapping = report.discover_projects(data / "Memory")
    assert "T-01" not in mapping
    assert mapping["T-02"] == ["alpha"]
    assert report.get_active_task_for_project("alpha") == "T-02"


def test_active_task_reads_only_local_sqlite_project_column(tmp_path, monkeypatch):
    data = tmp_path / "data"
    local = tmp_path / "local"
    data.mkdir()
    local.mkdir()
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(data))
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(local))
    for path, task_id in ((data / "devcore.db", "T-SHARED"), (local / "devcore.db", "T-LOCAL")):
        with sqlite3.connect(path) as conn:
            conn.execute("CREATE TABLE tasks (id TEXT, project_id TEXT, status TEXT, created_at TEXT)")
            conn.execute("INSERT INTO tasks VALUES (?, 'alpha', 'in_progress', '2026-10-09')", (task_id,))
    report = load_report()
    assert report.get_active_task_for_project("alpha") == "T-LOCAL"
    assert report.get_active_task_for_project("beta") is None
    _, mapping = report.discover_projects(data / "Memory")
    assert mapping["T-LOCAL"] == ["alpha"]
    assert "T-SHARED" not in mapping


def test_report_refuses_to_write_under_shared_data_without_local_root(tmp_path):
    env = os.environ.copy()
    env.pop("DEVCORE_LOCAL_ROOT", None)
    env.pop("LOCALAPPDATA", None)
    env["DEVCORE_DATA_ROOT"] = str(tmp_path / "data")
    env["USERPROFILE"] = str(tmp_path / "home")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--date", "2026-10-09"],
        cwd=tmp_path, env=env, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 2
    assert "DEVCORE_LOCAL_ROOT is required" in result.stderr
    assert not (tmp_path / "data").exists()


def test_untagged_proxy_usage_is_global_but_never_assigned_to_devcore(tmp_path):
    data, local, home = (tmp_path / name for name in ("data", "local", "home"))
    stats = data / "Metrics" / "headroom_stats.json"
    stats.parent.mkdir(parents=True)
    stats.write_text(json.dumps({"tasks": {"Aucune": {
        "total_tokens": 100, "tokens_in": 80, "tokens_out": 20,
    }}}), encoding="utf-8")
    env = os.environ.copy()
    env.update({"DEVCORE_DATA_ROOT": str(data), "DEVCORE_LOCAL_ROOT": str(local),
                "DEVCORE_PLATFORM_ROOT": str(tmp_path / "platform"), "USERPROFILE": str(home)})
    result = subprocess.run([sys.executable, str(SCRIPT), "--date", "2026-10-09"],
                            cwd=tmp_path, env=env, capture_output=True, text=True, check=True)
    summary = json.loads((local / "Logs" / "token_reports" / "token_metrics_summary.json").read_text())
    assert result.returncode == 0
    assert summary["totals"]["tokens"] == 100
    assert summary["unattributed"]["tokens"] == 100
    assert summary["projects"] == {}
    assert summary["clients"]["headroom-proxy"]["sessions"] == 0


def test_metric_snapshots_use_each_project_and_exclude_global_unattributed(monkeypatch):
    report = load_report()
    batches = []
    def unavailable_sink(records):
        batches.append(records)
        return False
    monkeypatch.setattr(report, "record_metric_batch", unavailable_sink)
    delivered = report.record_project_metrics({
        "totals": {"tokens": 130},
        "unattributed": {"tokens": 30},
        "projects": {
            "alpha": {"tokens": 60, "cache_hits": 10, "cost_usd": 0.2, "sessions": 1},
            "beta": {"tokens": 40, "cache_hits": 5, "cost_usd": 0.1, "sessions": 2},
        },
    }, "2026-10-09")
    assert delivered is False
    assert len(batches) == 1 and len(batches[0]) == 8
    assert {record["project"] for record in batches[0]} == {"alpha", "beta"}
    assert sum(record["value"] for record in batches[0] if record["metric_type"] == "tokens") == 100
    assert all(record["project"] != "devcore" for record in batches[0])


def test_metric_snapshots_are_batched_below_windows_command_limit(monkeypatch):
    report = load_report()
    batches = []
    monkeypatch.setattr(report, "record_metric_batch", lambda records: batches.append(records) or True)
    projects = {f"project_{index}": {"tokens": index, "sessions": 1}
                for index in range(9)}
    assert report.record_project_metrics({"projects": projects}, "2026-10-09") is True
    assert [len(batch) for batch in batches] == [32, 4]
    assert len({record["project"] for batch in batches for record in batch}) == 9
