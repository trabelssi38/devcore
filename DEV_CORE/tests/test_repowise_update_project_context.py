"""RepoWise updates must resolve an explicit project before side effects."""

import json
import subprocess
import sys
import types

import pytest

from Scripts import repowise_update


def test_missing_or_unknown_project_stops_before_workspace_sync(tmp_path, monkeypatch):
    registry = tmp_path / "projects.json"
    registry.write_text(json.dumps({"projects": []}), encoding="utf-8")
    monkeypatch.setattr(repowise_update, "PROJECTS_JSON", registry)
    calls = []
    monkeypatch.setitem(
        sys.modules, "sync_repowise_workspace",
        types.SimpleNamespace(sync_workspace=lambda: calls.append("sync")),
    )
    for argv in ([], ["--project", "missing"], ["--project", "../escape"]):
        with pytest.raises(SystemExit) as exc:
            repowise_update.main(argv)
        assert exc.value.code == 2
    assert calls == []


def test_registered_project_is_indexed_without_global_fallback(tmp_path, monkeypatch):
    alpha = tmp_path / "alpha"
    beta = tmp_path / "beta"
    alpha.mkdir()
    beta.mkdir()
    (alpha / ".repowiseignore").write_text(".git/\n", encoding="utf-8")
    registry = tmp_path / "projects.json"
    registry.write_text(json.dumps({"projects": [
        {"name": "alpha", "path": str(alpha)},
        {"name": "beta", "path": str(beta)},
    ]}), encoding="utf-8")
    global_selection = tmp_path / "active_project.txt"
    global_selection.write_text("beta", encoding="utf-8")
    monkeypatch.setattr(repowise_update, "PROJECTS_JSON", registry)
    monkeypatch.setattr(repowise_update, "resolve_repowise_exe", lambda: "repowise-test")
    calls = []
    monkeypatch.setitem(
        sys.modules, "sync_repowise_workspace",
        types.SimpleNamespace(sync_workspace=lambda: calls.append(("sync",))),
    )

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, "indexed", "")

    monkeypatch.setattr(repowise_update.subprocess, "run", fake_run)
    repowise_update.main(["--project", "alpha"])
    update = next(item for item in calls if len(item) == 2)
    assert update[0][0] == "repowise-test"
    assert "--index-only" in update[0]
    assert "--no-workspace" in update[0]
    assert update[1]["cwd"] == str(alpha.resolve())
    assert update[1]["env"]["REPOWISE_EMBEDDER"] == "mock"
    assert update[1]["env"]["REPOWISE_TELEMETRY_DISABLED"] == "1"
    assert global_selection.read_text(encoding="utf-8") == "beta"
    assert not any(item == ("sync",) for item in calls)
    assert len([item for item in calls if len(item) == 2]) == 1


def test_registry_mapping_conflicting_with_project_manifest_is_rejected(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    manifest = repo / ".devcore" / "project.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"name": "beta"}), encoding="utf-8")
    registry = tmp_path / "projects.json"
    registry.write_text(json.dumps({"projects": [{"name": "alpha", "path": str(repo)}]}), encoding="utf-8")
    monkeypatch.setattr(repowise_update, "PROJECTS_JSON", registry)
    calls = []
    monkeypatch.setitem(
        sys.modules, "sync_repowise_workspace",
        types.SimpleNamespace(sync_workspace=lambda: calls.append("sync")),
    )
    with pytest.raises(SystemExit) as exc:
        repowise_update.main(["--project", "alpha"])
    assert exc.value.code == 2
    assert calls == []
