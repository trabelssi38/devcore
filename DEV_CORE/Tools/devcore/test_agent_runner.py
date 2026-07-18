import sys
import json
from pathlib import Path
import pytest

# Ensure devcore is in path
tools_dir = Path(__file__).resolve().parent.parent
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))

from devcore.router import recommend_engine
from devcore.agent_runner import get_agent_runner, HermesAgentRunner, LocalProcessAgentRunner, CodexManualAgentRunner


def test_recommend_engine_rules(monkeypatch, tmp_path):
    """Test recommend_engine using declarative harness rules in harness_profiles.json."""
    config_path = tmp_path / "Config"
    config_path.mkdir()
    harness_file = config_path / "harness_profiles.json"
    
    profiles = {
        "schema_version": "1.0",
        "default_harness": "coding",
        "harnesses": {
            "reasoning": {"engine": "gemini", "fallback_harness": "coding"},
            "coding": {"engine": "gemini", "fallback_harness": "reasoning"},
            "claude_sonnet": {"engine": "claude", "fallback_harness": "reasoning"}
        },
        "routing_rules": [
            {"criteria": {"task_type": "architecture"}, "recommended_harness": "reasoning"},
            {"criteria": {"task_type": "review"}, "recommended_harness": "claude_sonnet"}
        ]
    }
    with open(harness_file, "w", encoding="utf-8") as f:
        json.dump(profiles, f)

    # Monkeypatch get_paths to point platform_root to tmp_path
    from devcore import router
    from devcore.paths import DevCorePaths
    
    dummy_paths = DevCorePaths(
        platform_root=tmp_path,
        data_root=tmp_path,
        bus_root=tmp_path,
        session_root=tmp_path,
        vault_root=tmp_path,
        memory_root=tmp_path,
        memory_review_pending=tmp_path,
        memory_review_approved=tmp_path,
        canonical_memory_root=tmp_path,
        qdrant_refresh_queue=tmp_path,
        qdrant_rebuild_manifest=tmp_path,
        schema_root=tools_dir.parent / "Schemas",
        router_log_root=tmp_path,
        scoring_log_root=tmp_path
    )
    monkeypatch.setattr(router, "get_paths", lambda: dummy_paths)

    # 1. Matches rule (architecture -> reasoning -> gemini)
    decision = recommend_engine("architecture", "normal", "small")
    assert decision["engine"] == "gemini"
    assert decision["fallback"] == "gemini"
    assert "rule matched (task_type=architecture)" in decision["reason"]

    # 2. Matches rule (review -> claude_sonnet -> claude)
    decision = recommend_engine("review", "normal", "small")
    assert decision["engine"] == "claude"
    assert decision["fallback"] == "gemini"
    assert "rule matched (task_type=review)" in decision["reason"]

    # 3. Fallback (bugfix -> default -> coding -> gemini)
    decision = recommend_engine("bugfix", "normal", "small")
    assert decision["engine"] == "gemini"
    assert decision["fallback"] == "gemini"
    assert "default fallback" in decision["reason"]


def test_agent_runner_backends(tmp_path):
    """Test behavior and health check of different AgentRunner backends."""
    settings_file = tmp_path / "Config" / "settings.json"
    settings_file.parent.mkdir(parents=True, exist_ok=True)

    # 1. Hermes enabled
    with open(settings_file, "w", encoding="utf-8") as f:
        json.dump({"services": {"hermes_daemon": True}}, f)
        
    hermes_runner = HermesAgentRunner(settings_file, tmp_path)
    assert hermes_runner.report_status()["status"] == "OK"

    # 2. Hermes disabled
    with open(settings_file, "w", encoding="utf-8") as f:
        json.dump({"services": {"hermes_daemon": False}}, f)
        
    hermes_runner_disabled = HermesAgentRunner(settings_file, tmp_path)
    assert hermes_runner_disabled.report_status()["status"] == "DOWN"
    assert hermes_runner_disabled.has_active_task() is False

    # 3. Local process runner
    local_runner = LocalProcessAgentRunner(tmp_path)
    assert local_runner.report_status()["status"] == "OK"
    assert local_runner.run({"id": "T-100", "title": "Test"})["runner"] == "local_process"

    # 4. Codex manual runner
    codex_runner = CodexManualAgentRunner(tmp_path)
    assert codex_runner.report_status()["status"] == "OK"
    receipt = codex_runner.run({"id": "T-101", "title": "Test Manual"})
    assert receipt["runner"] == "codex_manual"
    assert Path(receipt["prompt_path"]).exists()
