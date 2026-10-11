"""Local metric snapshots stay isolated and survive concurrent writers."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from Scripts import metrics_service as metrics


def test_latest_snapshots_are_summed_once_per_project_and_secrets_are_redacted(tmp_path, monkeypatch):
    local, shared = tmp_path / "local", tmp_path / "shared"
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(local))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(shared))
    base = {"source": "token_report", "task_id": "", "metric_type": "tokens", "unit": "tokens"}
    metrics.record(**base, project="alpha", value=10, payload_json='{"api_key":"secret"}')
    metrics.record(**base, project="beta", value=20)
    metrics.record(**base, project="alpha", value=12)
    result = metrics.aggregate()
    assert result["events_count"] == 3 and result["errors_count"] == 0
    assert result["projects"]["alpha"]["totals"]["tokens"]["tokens"]["sum"] == 12
    assert result["projects"]["beta"]["totals"]["tokens"]["tokens"]["sum"] == 20
    assert result["totals"]["tokens"]["tokens"]["sum"] == 32
    assert result["totals"]["tokens"]["tokens"]["aggregation"] == "latest_by_project"
    lines = metrics.store_path().read_text(encoding="utf-8").splitlines()
    assert json.loads(lines[0])["payload"]["api_key"] == "[REDACTED]"
    assert "secret" not in "\n".join(lines)
    assert not shared.exists()


def test_dashboard_totals_sum_latest_project_snapshots_without_shared_fallback(tmp_path, monkeypatch):
    from Scripts.dashboard import html_renderer

    local, shared = tmp_path / "local", tmp_path / "shared"
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(local))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(shared))
    monkeypatch.setattr(html_renderer, "LOCAL_ROOT", local)
    monkeypatch.setattr(html_renderer, "DATA_ROOT", shared)
    base = {"source": "token_report", "task_id": "", "metric_type": "tokens", "unit": "tokens"}
    metrics.record(**base, project="alpha", value=10)
    metrics.record(**base, project="beta", value=20)
    metrics.record(**base, project="alpha", value=12)
    status = html_renderer.get_metrics_service_status()
    assert status["aggregate"]["totals"]["tokens"]["tokens"]["sum"] == 32
    assert status["aggregate"]["totals"]["tokens"]["tokens"]["aggregation"] == "latest_by_project"
    assert not shared.exists()


def test_malformed_historical_lines_are_skipped_without_losing_valid_metrics(tmp_path, monkeypatch):
    from Scripts.dashboard import html_renderer

    local, shared = tmp_path / "local", tmp_path / "shared"
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(local))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(shared))
    monkeypatch.setattr(html_renderer, "LOCAL_ROOT", local)
    metrics.record(source="token_report", project="alpha", task_id="",
                   metric_type="tokens", value=7, unit="tokens")
    path = metrics.store_path()
    with path.open("a", encoding="utf-8") as handle:
        handle.write('{"event_type":"MetricRecorded"}\n')
        handle.write('{"schema_version":1,"event_type":"MetricRecorded","source":"x",'
                     '"project":"alpha","metric_type":"tokens","unit":"tokens","value":NaN}\n')
        handle.write('{broken}\n')
    for result in (metrics.aggregate(), html_renderer.get_metrics_service_status()["aggregate"]):
        assert result["events_count"] == 1
        assert result["errors_count"] == 3
        assert result["totals"]["tokens"]["tokens"]["sum"] == 7
    assert path.read_text(encoding="utf-8").count("\n") == 4
    assert not shared.exists()


def test_local_root_cannot_be_inside_shared_root(tmp_path, monkeypatch):
    shared = tmp_path / "shared"
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(shared))
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(shared / "local"))
    with pytest.raises(ValueError, match="inside"):
        metrics.health()
    assert not shared.exists()


def test_invalid_batch_is_rejected_before_any_event_is_written(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(tmp_path / "local"))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(tmp_path / "shared"))
    valid = {"source": "token_report", "project": "alpha", "task_id": "",
             "metric_type": "tokens", "value": 3, "unit": "tokens"}
    with pytest.raises(ValueError, match="project"):
        metrics.record_batch([valid, {**valid, "project": "../beta"}])
    assert not (tmp_path / "local").exists()
    assert not (tmp_path / "shared").exists()


def test_parallel_writers_append_complete_json_lines(tmp_path):
    env = os.environ.copy()
    env["DEVCORE_LOCAL_ROOT"] = str(tmp_path / "local")
    env["DEVCORE_DATA_ROOT"] = str(tmp_path / "shared")
    script = Path(metrics.__file__)
    commands = [
        [sys.executable, str(script), "-Action", "Record", "-Source", "token_report",
         "-Project", project, "-MetricType", "tokens", "-Value", "1", "-Unit", "tokens"]
        for project in ("alpha", "beta", "alpha", "beta")
    ]
    processes = [subprocess.Popen(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                 for command in commands]
    for process in processes:
        stdout, stderr = process.communicate(timeout=15)
        assert process.returncode == 0, (stdout, stderr)
    paths = list((Path(env["DEVCORE_LOCAL_ROOT"]) / "Logs" / "metrics").glob("metrics-*.jsonl"))
    assert len(paths) == 1
    path = paths[0]
    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(events) == 4
    assert {event["project"] for event in events} == {"alpha", "beta"}
    assert not Path(env["DEVCORE_DATA_ROOT"]).exists()


@pytest.mark.skipif(shutil.which("powershell.exe") is None, reason="PowerShell unavailable")
def test_token_report_reaches_local_metric_store(tmp_path, monkeypatch):
    from Scripts.Auto import token_report

    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(tmp_path / "local"))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(tmp_path / "shared"))
    monkeypatch.setenv("DEVCORE_PLATFORM_ROOT", str(Path(__file__).resolve().parents[1]))
    monkeypatch.setenv("DEVCORE_PYTHON", sys.executable)
    assert token_report.record_metric("tokens", 42, "tokens", {"date": "2026-10-09"}, project="alpha") is True
    assert token_report.record_project_metrics({"projects": {
        "alpha": {"tokens": 12, "cache_hits": 2, "cost_usd": 0.1, "sessions": 1},
        "beta": {"tokens": 20, "cache_hits": 3, "cost_usd": 0.2, "sessions": 2},
    }}, "2026-10-09") is True
    aggregate = metrics.aggregate()
    assert aggregate["events_count"] == 9
    assert aggregate["projects"]["alpha"]["totals"]["tokens"]["tokens"]["sum"] == 12
    assert aggregate["totals"]["tokens"]["tokens"]["sum"] == 32
    assert not (tmp_path / "shared").exists()


def test_task_metrics_are_partitioned_by_project_and_task_id(tmp_path, monkeypatch):
    from Scripts.dashboard import html_renderer
    from Scripts.dashboard.task_interactions import scoped_task_metrics

    local, shared = tmp_path / "local", tmp_path / "shared"
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(local))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(shared))
    monkeypatch.setattr(html_renderer, "LOCAL_ROOT", local)
    monkeypatch.setattr(html_renderer, "DATA_ROOT", shared)

    metrics.record(source="cli", project="alpha", task_id="T-01", metric_type="tokens", value=2, unit="tokens")
    metrics.record(source="cli", project="beta", task_id="T-01", metric_type="tokens", value=7, unit="tokens")

    for result in (metrics.aggregate(), html_renderer.get_metrics_service_status()["aggregate"]):
        assert result["events_count"] == 2
        assert result["errors_count"] == 0
        assert "T-01" not in result["tasks"]
        assert "alpha_T-01" in result["tasks"]
        assert "beta_T-01" in result["tasks"]
        assert result["tasks"]["alpha_T-01"]["totals"]["tokens"]["tokens"]["sum"] == 2
        assert result["tasks"]["beta_T-01"]["totals"]["tokens"]["tokens"]["sum"] == 7
        assert result["projects"]["alpha"]["totals"]["tokens"]["tokens"]["sum"] == 2
        assert result["projects"]["beta"]["totals"]["tokens"]["tokens"]["sum"] == 7
        assert result["totals"]["tokens"]["tokens"]["sum"] == 9

        alpha_scoped = scoped_task_metrics(result["tasks"], "alpha", "T-01")
        beta_scoped = scoped_task_metrics(result["tasks"], "beta", "T-01")
        assert alpha_scoped["totals"]["tokens"]["tokens"]["sum"] == 2
        assert beta_scoped["totals"]["tokens"]["tokens"]["sum"] == 7


def test_append_events_recovers_gracefully_from_missing_trailing_newline(tmp_path, monkeypatch):
    from Scripts.dashboard import html_renderer

    local, shared = tmp_path / "local", tmp_path / "shared"
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(local))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(shared))
    monkeypatch.setattr(html_renderer, "LOCAL_ROOT", local)
    monkeypatch.setattr(html_renderer, "DATA_ROOT", shared)

    path = metrics.store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    initial_event = {
        "schema_version": 1,
        "event_type": "MetricRecorded",
        "recorded_at": "2026-10-10T12:00:00+00:00",
        "source": "cli",
        "project": "alpha",
        "task_id": "T-01",
        "metric_type": "tokens",
        "value": 3,
        "unit": "tokens",
        "payload": {},
    }
    # Deliberately write valid JSON without trailing newline
    path.write_bytes(json.dumps(initial_event, separators=(",", ":")).encode("utf-8"))

    result1 = metrics.aggregate()
    assert result1["events_count"] == 1
    assert result1["errors_count"] == 0

    metrics.record(source="cli", project="beta", task_id="T-02", metric_type="tokens", value=5, unit="tokens")

    for result2 in (metrics.aggregate(), html_renderer.get_metrics_service_status()["aggregate"]):
        assert result2["events_count"] == 2
        assert result2["errors_count"] == 0
        assert result2["projects"]["alpha"]["totals"]["tokens"]["tokens"]["sum"] == 3
        assert result2["projects"]["beta"]["totals"]["tokens"]["tokens"]["sum"] == 5
        assert result2["totals"]["tokens"]["tokens"]["sum"] == 8

