"""Comparison must not advertise savings from incomparable or failed runs."""

import importlib.util
import json
from pathlib import Path
import sys
import subprocess

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "Scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("compare_codex_usage", SCRIPTS / "compare_codex_usage.py")
comparison = importlib.util.module_from_spec(spec)
spec.loader.exec_module(comparison)


def experiment(tmp_path):
    runs = []
    for condition, input_tokens in (("baseline", 1000), ("context", 700)):
        path = tmp_path / f"{condition}.jsonl"
        usage = {"input_tokens": input_tokens, "output_tokens": 100,
                 "cached_input_tokens": 200, "total_tokens": input_tokens + 100}
        rows = [{"type": "session_meta", "payload": {"id": condition}},
                {"type": "turn_context", "payload": {"model": "test-model"}},
                {"type": "event_msg", "payload": {"type": "token_count", "info": {"total_token_usage": usage}}}]
        path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
        runs.append({"condition": condition, "rollout": path.name, "project_id": "alpha", "task_id": "T-01",
                     "git_commit": "fixture-sha", "model": "test-model", "reasoning_effort": "same-effort",
                     "completed": True, "quality_checks": {"tests_pass": True, "decisions_respected": True}})
    manifest = tmp_path / "experiment.json"
    manifest.write_text(json.dumps({"schema_version": 1, "runs": runs}), encoding="utf-8")
    return manifest, runs


def test_observed_comparison_preserves_sources(tmp_path):
    manifest, _ = experiment(tmp_path)
    before = {path: path.read_bytes() for path in tmp_path.iterdir()}
    result = comparison.compare(manifest)
    assert result["status"] == "comparable"
    assert result["tokens_saved"] == 300
    assert result["tokens_saved_percent"] == 27.27
    assert result["equivalence_and_quality"] == "declared_in_manifest"
    assert all(path.read_bytes() == content for path, content in before.items())


def test_cli_returns_json_without_writing_files(tmp_path):
    manifest, _ = experiment(tmp_path)
    before = set(tmp_path.iterdir())
    result = subprocess.run([sys.executable, str(SCRIPTS / "compare_codex_usage.py"), str(manifest)],
                            cwd=tmp_path, capture_output=True, text=True, check=True)
    assert json.loads(result.stdout)["tokens_saved"] == 300
    assert set(tmp_path.iterdir()) == before


@pytest.mark.parametrize("change", ["quality", "model", "commit", "session", "counter"])
def test_no_gain_claim_when_comparison_is_invalid(tmp_path, change):
    manifest, runs = experiment(tmp_path)
    if change == "quality":
        runs[1]["quality_checks"]["tests_pass"] = False
    elif change == "model":
        runs[1]["model"] = "other-model"
    elif change == "commit":
        runs[1]["git_commit"] = "other-sha"
    elif change == "session":
        runs[1]["rollout"] = runs[0]["rollout"]
    elif change == "counter":
        path = tmp_path / runs[1]["rollout"]
        with path.open("a", encoding="utf-8") as stream:
            stream.write('\n' + json.dumps({"type": "event_msg", "payload": {
                "type": "token_count", "info": {"total_token_usage": {
                    "input_tokens": 5, "output_tokens": 1, "total_tokens": 6}}}}))
    manifest.write_text(json.dumps({"schema_version": 1, "runs": runs}), encoding="utf-8")
    result = comparison.compare(manifest)
    assert result["status"] == "inconclusive"
    assert result["reasons"]
    assert "tokens_saved_percent" not in result
