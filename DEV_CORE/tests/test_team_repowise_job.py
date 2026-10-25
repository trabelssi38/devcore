"""RepoWise index candidate uses a fake executable and temporary Git repository."""

import importlib.util
import json
from pathlib import Path
import subprocess

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "Scripts" / "team_repowise_job.py"
spec = importlib.util.spec_from_file_location("team_repowise_job", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_repowise_refresh_only_for_project_revision(tmp_path, monkeypatch):
    root = tmp_path / "alpha"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "file.txt").write_text("fixture", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "file.txt"], check=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.name=Fixture", "-c",
                    "user.email=fixture@example.invalid", "commit", "-qm", "fixture"], check=True)
    revision = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    executable = tmp_path / "repowise.exe"
    executable.touch()
    indexed = {"commit": "0" * 40, "updates": 0}
    original = module.call

    def fake_call(argv, cwd, *, timeout, env=None):
        if argv[0] != str(executable):
            return original(argv, cwd, timeout=timeout, env=env)
        if argv[1] == "update":
            indexed["commit"] = revision
            indexed["updates"] += 1
            return subprocess.CompletedProcess(argv, 0, "", "")
        payload = {"indexed": True, "state": {"last_sync_commit": indexed["commit"]},
                   "index_scope": {"file_pages": {"omitted": 0}}}
        return subprocess.CompletedProcess(argv, 0, json.dumps(payload), "")

    monkeypatch.setattr(module, "call", fake_call)
    monkeypatch.setenv("DEVCORE_PROJECT_ID", "alpha")
    first = module.index("alpha", root, revision, executable, force=False)
    assert first["refreshed"] and first["coverage_known"] and indexed["updates"] == 1
    second = module.index("alpha", root, revision, executable, force=False)
    assert not second["refreshed"] and indexed["updates"] == 1
    third = module.index("alpha", root, revision, executable, force=True)
    assert third["refreshed"] and indexed["updates"] == 2
    with pytest.raises(ValueError, match="Run project mismatch"):
        module.index("beta", root, revision, executable, force=False)
    (root / "dirty.txt").write_text("untracked", encoding="utf-8")
    with pytest.raises(ValueError, match="uncommitted"):
        module.index("alpha", root, revision, executable, force=False)
