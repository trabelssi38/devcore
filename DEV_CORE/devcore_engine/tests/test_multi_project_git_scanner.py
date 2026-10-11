import json
import subprocess
from pathlib import Path

from devcore_engine.db import init_db
from devcore_engine.infra.multi_project_git_scanner import MultiProjectGitScanner


def test_scanner_keeps_deleted_task_and_other_project_isolated(tmp_path, monkeypatch):
    data_root = tmp_path / "shared"
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(data_root))
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    conn = init_db(tmp_path / "devcore.db")
    try:
        conn.executemany(
            "INSERT INTO projects(id, name, root_path) VALUES (?, ?, ?)",
            [("alpha", "alpha", str(repo_path)), ("beta", "beta", str(repo_path))],
        )
        conn.executemany(
            "INSERT INTO tasks(id, project_id, title, status) VALUES ('T-01', ?, ?, ?)",
            [("alpha", "removed", "deleted"), ("beta", "working", "in_progress")],
        )
        conn.commit()
        scanner = MultiProjectGitScanner(conn)
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, "a" * 40 + "|[T-01] change|2026-10-02 10:00:00 +0000\n", ""),
        )

        assert scanner.scan_project_repo("alpha", repo_path) == 0
        assert scanner.scan_project_repo("beta", repo_path) == 0
        rows = conn.execute(
            "SELECT project_id, title, status FROM tasks WHERE id = 'T-01' ORDER BY project_id"
        ).fetchall()
        assert [(r[0], r[1], r[2]) for r in rows] == [
            ("alpha", "removed", "deleted"),
            ("beta", "working", "done"),
        ]
        assert not (data_root / "Memory" / "alpha" / "tasks.json").exists()
    finally:
        conn.close()


def test_scan_all_does_not_export_legacy_json(tmp_path, monkeypatch):
    data_root = tmp_path / "shared"
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(data_root))
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    conn = init_db(tmp_path / "devcore.db")
    try:
        scanner = MultiProjectGitScanner(conn)
        scanner.projects_json = tmp_path / "projects.json"
        scanner.projects_json.write_text(
            json.dumps({"projects": [{"name": "alpha", "path": str(repo_path)}]}),
            encoding="utf-8",
        )
        monkeypatch.setattr(scanner, "scan_project_repo", lambda *args, **kwargs: 0)

        assert scanner.scan_all_projects()["total_new_tasks"] == 0
        assert not (data_root / "Memory" / "alpha" / "tasks.json").exists()
    finally:
        conn.close()
