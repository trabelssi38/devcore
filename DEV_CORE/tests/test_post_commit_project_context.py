"""The Git hook must use repository metadata, never another session's project."""

import json
import subprocess

from devcore_engine.db import connect_db
from devcore_engine.hooks import post_commit
from devcore_engine.services.tasks import TaskService


def test_post_commit_uses_repository_project_when_environment_points_elsewhere(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    metadata = repo / ".devcore" / "project.json"
    metadata.parent.mkdir(parents=True)
    metadata.write_text(json.dumps({"name": "alpha"}), encoding="utf-8")
    monkeypatch.setenv("DEVCORE_ACTIVE_PROJECT_NAME", "beta")
    monkeypatch.setattr(
        post_commit.subprocess, "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, str(repo), ""),
    )
    assert post_commit.resolve_commit_context().project_id == "alpha"

    conn = connect_db(tmp_path / "devcore.db")
    service = TaskService(conn)
    service.add_task("Session de travail auto", steps=2, project_id="alpha")
    service.add_task("Session de travail auto", steps=2, project_id="beta")
    monkeypatch.setattr(post_commit, "init_db", lambda: conn)
    monkeypatch.setattr(post_commit, "get_last_commit_message", lambda: "[T-01] Alpha commit")
    post_commit.run_post_commit_hook(post_commit.resolve_commit_context())

    assert service.get_task("T-01", "alpha")["steps_done"] == 1
    assert service.get_task("T-01", "alpha")["title"] == "Alpha commit"
    assert service.get_task("T-01", "beta")["steps_done"] == 0
    assert service.get_task("T-01", "beta")["title"] == "session de travail auto"
    conn.close()


def test_post_commit_has_no_global_or_directory_fallback(tmp_path, monkeypatch):
    repo = tmp_path / "beta"
    repo.mkdir()
    monkeypatch.setenv("DEVCORE_ACTIVE_PROJECT_NAME", "alpha")
    monkeypatch.setattr(
        post_commit.subprocess, "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, str(repo), ""),
    )
    assert post_commit.resolve_commit_context() is None
    try:
        post_commit.run_post_commit_hook(None)
    except TypeError:
        pass
    else:
        raise AssertionError("post-commit accepted a missing project context")
