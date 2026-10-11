import importlib.util
import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "DEV_CORE" / "Scripts" / "Auto" / "task_prompt_analyzer.py"


def load_analyzer(monkeypatch, tmp_path):
    data_root = tmp_path / "data"
    monkeypatch.setenv("DEVCORE_PLATFORM_ROOT", str(REPO_ROOT / "DEV_CORE"))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(data_root))
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(tmp_path / "local"))
    monkeypatch.chdir(tmp_path)
    spec = importlib.util.spec_from_file_location("task_prompt_analyzer_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, data_root


@pytest.mark.parametrize("arguments", [[], ["--project", "../beta"], ["--project", "alpha/beta"]])
def test_invalid_or_missing_project_fails_before_writing(monkeypatch, tmp_path, arguments):
    analyzer, data_root = load_analyzer(monkeypatch, tmp_path)

    with pytest.raises(SystemExit):
        analyzer.main(arguments)

    assert not data_root.exists()


def test_explicit_project_wins_over_environment_and_isolates_legacy_queue(monkeypatch, tmp_path):
    analyzer, data_root = load_analyzer(monkeypatch, tmp_path)
    monkeypatch.setenv("DEVCORE_ACTIVE_PROJECT_NAME", "beta")
    monkeypatch.setenv("ANTIGRAVITY_BRAIN_DIR", str(tmp_path / "no-brain-fixture"))
    alpha = data_root / "Memory" / "alpha"
    beta = data_root / "Memory" / "beta"
    alpha.mkdir(parents=True)
    beta.mkdir(parents=True)
    beta_tasks = beta / "tasks.json"
    beta_tasks.write_text(json.dumps({"tasks": [{"id": "B1", "title": "beta secret"}]}), encoding="utf-8")
    before = beta_tasks.read_bytes()

    analyzer.main(["--project", "alpha"])

    log_path = data_root / "Logs" / "scripts" / f"task_prompt_analyzer_{analyzer.datetime.now():%Y-%m-%d}.log"
    assert "project: 'alpha'" in log_path.read_text(encoding="utf-8")
    assert beta_tasks.read_bytes() == before
    assert not (beta / "task_prompt_queue.jsonl").exists()
    assert not (data_root / "Memory" / "task_prompt_queue.jsonl").exists()
