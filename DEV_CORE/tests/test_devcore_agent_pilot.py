"""The autonomous pilot cannot edit a checkout without exact human approval."""

import importlib.util
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "Scripts" / "devcore_agent_pilot.py"


def _pilot(tmp_path, monkeypatch, *, autocrlf="false"):
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(tmp_path / "local"))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(tmp_path / "data"))
    spec = importlib.util.spec_from_file_location("isolated_devcore_agent_pilot", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    repo = tmp_path / "devcore-pilot"
    repo.mkdir()
    (repo / "README.md").write_text("DevCore pilot\n")
    (repo / "DEV_CORE").mkdir()
    target = repo / "DEV_CORE" / "example.txt"
    target.write_text("before\n")
    for command in (["git", "init", "-q"], ["git", "config", "core.autocrlf", autocrlf],
                    ["git", "config", "user.name", "Pilot Test"],
                    ["git", "config", "user.email", "pilot@example.invalid"],
                    ["git", "add", "README.md", "DEV_CORE/example.txt"],
                    ["git", "-c", "core.hooksPath=NUL", "commit", "-qm", "fixture"]):
        subprocess.run(command, cwd=repo, check=True, capture_output=True)
    if autocrlf == "true":
        subprocess.run(["git", "checkout-index", "--force", "--all"], cwd=repo,
                       check=True, capture_output=True)
    monkeypatch.setattr(module, "PILOT_REPO", repo)
    return module, repo, target, tmp_path / "local" / "AgentPilot"


@pytest.mark.parametrize("autocrlf", ["false", "true"])
def test_read_only_proposal_waits_for_exact_interactive_approval(tmp_path, monkeypatch, autocrlf):
    pilot, repo, target, state = _pilot(tmp_path, monkeypatch, autocrlf=autocrlf)
    real_run = subprocess.run

    def run(command, *args, **kwargs):
        if command[0] == "codex":
            assert command[command.index("--sandbox") + 1] == "read-only"
            assert "--ephemeral" in command
            Path(command[command.index("--output-last-message") + 1]).write_text(
                json.dumps({"summary": "Change the fixture", "path": "DEV_CORE/example.txt",
                            "old": "before\n", "new": "after\n"}))
            return subprocess.CompletedProcess(command, 0, "", "")
        return real_run(command, *args, **kwargs)

    monkeypatch.setattr(pilot.subprocess, "run", run)
    result = pilot.propose(repo, state, "Change the fixture", "DEV_CORE/example.txt")
    assert result["status"] == "waiting_approval"
    assert target.read_text() == "before\n"
    with pytest.raises(ValueError, match="hash mismatch"):
        pilot.approve(repo, state, result["id"], "0" * 64)
    with pytest.raises(ValueError, match="Interactive human approval"):
        pilot.approve(repo, state, result["id"], result["sha256"])

    class Console:
        def isatty(self):
            return True

    monkeypatch.setattr(pilot.sys, "stdin", Console())
    monkeypatch.setattr("builtins.input", lambda prompt: f"APPLY {result['sha256']}")
    applied = pilot.approve(repo, state, result["id"], result["sha256"])
    assert applied["status"] == "applied"
    assert target.read_text() == "after\n"
    assert [json.loads(line)["event"] for line in (state / "audit.jsonl").read_text().splitlines()] == [
        "proposal_started", "proposal_ready", "human_approved", "patch_applied"]


def test_dirty_or_outside_checkout_and_unsafe_patch_refused(tmp_path, monkeypatch):
    pilot, repo, target, state = _pilot(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="dedicated"):
        pilot._repo(tmp_path)
    target.write_text("dirty\n")
    with pytest.raises(ValueError, match="clean"):
        pilot.propose(repo, state, "Change fixture", "DEV_CORE/example.txt")
    for patch in ("diff --git a/../secret b/../secret\n", "diff --git a/docs/x b/docs/x\n",
                  "diff --git a/DEV_CORE/x b/DEV_CORE/x\nnew file mode 100644\n"):
        with pytest.raises(ValueError):
            pilot._patch_paths(patch)


def test_checkout_change_invalidates_stored_approval(tmp_path, monkeypatch):
    pilot, repo, target, state = _pilot(tmp_path, monkeypatch)
    real_run = subprocess.run

    def run(command, *args, **kwargs):
        if command[0] == "codex":
            Path(command[command.index("--output-last-message") + 1]).write_text(
                json.dumps({"summary": "Change the fixture", "path": "DEV_CORE/example.txt",
                            "old": "before\n", "new": "after\n"}))
            return subprocess.CompletedProcess(command, 0, "", "")
        return real_run(command, *args, **kwargs)

    monkeypatch.setattr(pilot.subprocess, "run", run)
    proposal = pilot.propose(repo, state, "Change fixture", "DEV_CORE/example.txt")
    target.write_text("changed elsewhere\n")
    with pytest.raises(ValueError, match="clean"):
        pilot.approve(repo, state, proposal["id"], proposal["sha256"])
    assert target.read_text() == "changed elsewhere\n"


def test_daily_proposal_quota_blocks_fourth_model_call(tmp_path, monkeypatch):
    pilot, repo, _, state = _pilot(tmp_path, monkeypatch)
    state.mkdir(parents=True)
    today = datetime.now(timezone.utc).isoformat()
    (state / "audit.jsonl").write_text("".join(
        json.dumps({"at_utc": today, "event": "proposal_started", "id": str(i)}) + "\n"
        for i in range(3)))
    with pytest.raises(ValueError, match="quota exhausted"):
        pilot.propose(repo, state, "Change fixture", "DEV_CORE/example.txt")
