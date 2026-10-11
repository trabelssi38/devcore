"""Read disposable Codex rollouts without touching operational reports."""

import importlib.util
import json
from pathlib import Path


spec = importlib.util.spec_from_file_location("token_report_counters", Path(__file__).with_name("token_report.py"))
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


def counter(input_tokens, output_tokens, cached=0):
    return {"type": "event_msg", "timestamp": "2026-10-02T12:00:00Z", "payload": {
        "type": "token_count", "info": {"total_token_usage": {
            "input_tokens": input_tokens, "output_tokens": output_tokens,
            "cached_input_tokens": cached, "total_tokens": input_tokens + output_tokens}}}}


def parse(tmp_path, monkeypatch, rows):
    path = tmp_path / "rollout.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    monkeypatch.setattr(report, "get_active_task_for_project", lambda project: None)
    return report.parse_source({"client": "codex", "session_id": "test", "path": path}, ["alpha"], {})


def test_cumulative_snapshots_are_not_added_or_mixed_with_message_estimates(tmp_path, monkeypatch):
    result = parse(tmp_path, monkeypatch, [
        {"type": "session_meta", "timestamp": "2026-10-02T11:59:00Z",
         "payload": {"id": "test", "cwd": "E:/alpha"}},
        {"type": "response_item", "payload": {"type": "message", "role": "assistant", "content": "T-01 T-02 T-03"}},
        counter(100, 10, 20), counter(100, 10, 20), counter(160, 15, 30),
    ])
    assert result["tokens"] == 175
    assert result["cache_hits"] == 30
    assert result["output_tokens"] == 15
    assert len(result["model_turns"]) == 2
    assert result["usage_measurement"]["observed_tokens"] == 175
    assert result["usage_measurement"]["estimated_tokens"] == 0
    assert sum(task["tokens"] for task in result["_task_tokens"].values()) == 175
    assert all(not turn["estimated"] for turn in result["model_turns"])


def test_counter_reset_is_flagged_without_negative_usage(tmp_path, monkeypatch):
    result = parse(tmp_path, monkeypatch, [counter(100, 10), counter(5, 1), counter(15, 3)])
    assert result["tokens"] == 122
    assert result["usage_measurement"]["warnings"] == ["cumulative_usage_decreased"]


def test_missing_counters_remain_explicit_estimates(tmp_path, monkeypatch):
    result = parse(tmp_path, monkeypatch, [
        {"type": "response_item", "timestamp": "2026-10-02T12:00:00Z", "payload": {
            "type": "message", "role": "assistant", "content": "estimated response"}},
    ])
    assert result["usage_measurement"]["observed_tokens"] == 0
    assert result["usage_measurement"]["estimated_tokens"] > 0
    assert result["model_turns"][0]["measurement_source"] == "text_estimate"


def test_invalid_cumulative_values_are_rejected():
    for values in ({"input_tokens": -1}, {"input_tokens": "12"},
                   {"input_tokens": 5, "cached_input_tokens": 6}):
        raw = {"input_tokens": 10, "output_tokens": 1, "total_tokens": 11, **values}
        usage, previous, warning = report.codex_counter_delta({"info": {"total_token_usage": raw}}, None)
        assert usage is None
        assert previous is None
        assert warning
