import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "DEV_CORE" / "Scripts" / "Auto" / "intent_learner.py"
DEFAULTS = REPO_ROOT / "DEV_CORE" / "Config" / "intent_patterns.json"


def _run(tmp_path, project=None):
    env = os.environ.copy()
    env.update(
        DEVCORE_PLATFORM_ROOT=str(REPO_ROOT / "DEV_CORE"),
        DEVCORE_DATA_ROOT=str(tmp_path / "data"),
        DEVCORE_ACTIVE_PROJECT_NAME="beta",
    )
    args = [sys.executable, str(SCRIPT)]
    if project is not None:
        args.extend(["--project", project])
    return subprocess.run(args, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30)


def test_intent_learner_requires_project_before_creating_logs(tmp_path):
    missing = _run(tmp_path)
    traversal = _run(tmp_path, "../beta")
    assert missing.returncode != 0
    assert traversal.returncode != 0
    assert not (tmp_path / "data").exists()


def test_intent_learning_uses_and_updates_a_project_local_registry(tmp_path):
    data_root = tmp_path / "data"
    for project, verb in (("alpha", "qzxifier"), ("beta", "wugifier")):
        folder = data_root / "Memory" / project
        folder.mkdir(parents=True)
        (folder / "tasks.json").write_text(
            json.dumps({"tasks": [{"id": project, "title": f"{verb} une tâche"}]}),
            encoding="utf-8",
        )

    before = hashlib.sha256(DEFAULTS.read_bytes()).hexdigest()
    alpha = _run(tmp_path, "alpha")
    beta = _run(tmp_path, "beta")
    assert alpha.returncode == 0, alpha.stdout + alpha.stderr
    assert beta.returncode == 0, beta.stdout + beta.stderr
    assert hashlib.sha256(DEFAULTS.read_bytes()).hexdigest() == before

    alpha_registry = json.loads((data_root / "Memory" / "alpha" / "intent_patterns.json").read_text(encoding="utf-8"))
    beta_registry = json.loads((data_root / "Memory" / "beta" / "intent_patterns.json").read_text(encoding="utf-8"))
    assert "qzxifier" in alpha_registry["coding"]
    assert "wugifier" in beta_registry["coding"]
    assert "wugifier" not in alpha_registry["coding"]
    assert "qzxifier" not in beta_registry["coding"]
    assert not (data_root / "Memory" / "intent_patterns.json").exists()
