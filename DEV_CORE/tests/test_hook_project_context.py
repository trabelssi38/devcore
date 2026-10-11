"""Session and tool hooks resolve one local manifest, not global active state."""

import json
import os
import subprocess
import sys
from pathlib import Path

from devcore_engine.context import project_from_directory
from devcore_engine.db import connect_db
from devcore_engine.hooks import post_tool


def test_session_cli_skips_without_a_project_manifest(tmp_path):
    env = dict(os.environ)
    env["DEVCORE_LOCAL_ROOT"] = str(tmp_path / "local")
    env["DEVCORE_DATA_ROOT"] = str(tmp_path / "shared")
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    result = subprocess.run(
        [sys.executable, "-m", "devcore_engine.cli", "session", "start"],
        cwd=tmp_path, env=env, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0
    assert json.loads(result.stdout)["status"] == "skipped"
    assert not (tmp_path / "local" / "devcore.db").exists()


def test_project_manifest_resolution_is_local_to_each_working_directory(tmp_path, monkeypatch):
    alpha = tmp_path / "alpha"
    beta = tmp_path / "beta"
    for root, name in ((alpha, "alpha"), (beta, "beta")):
        manifest = root / ".devcore" / "project.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({"name": name}), encoding="utf-8")
        (root / "nested").mkdir()
    monkeypatch.setenv("DEVCORE_ACTIVE_PROJECT_NAME", "wrong")
    assert project_from_directory(alpha / "nested") == "alpha"
    assert project_from_directory(beta / "nested") == "beta"
    assert project_from_directory(tmp_path / "unregistered") is None


def test_post_tool_uses_local_manifest_and_skips_missing_context(tmp_path, monkeypatch):
    alpha = tmp_path / "alpha"
    beta = tmp_path / "beta"
    alpha.mkdir()
    beta.mkdir()
    manifest = alpha / ".devcore" / "project.json"
    manifest.parent.mkdir()
    manifest.write_text(json.dumps({"name": "alpha"}), encoding="utf-8")
    conn = connect_db(tmp_path / "devcore.db")
    monkeypatch.setattr(post_tool, "init_db", lambda: conn)
    monkeypatch.setenv("DEVCORE_ACTIVE_PROJECT_NAME", "beta")

    monkeypatch.chdir(alpha)
    post_tool.run_post_tool_hook("Python", {"ok": True})
    assert conn.execute("SELECT project FROM metrics WHERE source='post_tool_hook'").fetchall()[0][0] == "alpha"
    monkeypatch.chdir(beta)
    post_tool.run_post_tool_hook("Python", {"ok": True})
    assert conn.execute("SELECT count(*) FROM metrics WHERE source='post_tool_hook'").fetchone()[0] == 1
    conn.close()
