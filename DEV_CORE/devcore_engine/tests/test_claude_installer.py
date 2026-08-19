"""
Unit tests for devcore_engine.installers.claude_installer
"""

import json
import pytest
from pathlib import Path
from devcore_engine.installers.claude_installer import (
    detect_environment,
    ClaudeInstaller,
)


def test_detect_environment(tmp_path: Path) -> None:
    env = detect_environment(repo_root=tmp_path)
    assert env["repo_root"] == tmp_path.resolve()
    assert "python_exe" in env
    assert "claude_code_settings" in env
    assert "claude_desktop_config" in env


def test_install_claude_code_isolated(tmp_path: Path) -> None:
    fake_repo = tmp_path / "my_project"
    fake_repo.mkdir(parents=True)
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir(parents=True)

    installer = ClaudeInstaller(repo_root=fake_repo)
    # Override environment target paths for test isolation
    installer.env["home_dir"] = fake_home
    installer.env["claude_code_dir"] = fake_home / ".claude"
    installer.env["claude_code_settings"] = fake_home / ".claude" / "settings.json"
    installer.env["claude_code_md"] = fake_home / ".claude" / "CLAUDE.md"

    res = installer.install_claude_code()
    assert res["status"] == "OK"

    # Verify settings.json created and valid
    settings_file = installer.env["claude_code_settings"]
    assert settings_file.exists()

    with open(settings_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "hooks" in data
    assert "UserPromptSubmit" in data["hooks"]
    assert "PostToolUse" in data["hooks"]
    assert "Stop" in data["hooks"]

    assert "mcpServers" in data
    assert "repowise" in data["mcpServers"]
    assert data["mcpServers"]["repowise"]["args"][1] == str(fake_repo.resolve()).replace("\\", "/")

    # Verify local .mcp.json
    local_mcp = fake_repo / ".mcp.json"
    assert local_mcp.exists()
    with open(local_mcp, "r", encoding="utf-8") as f:
        local_data = json.load(f)
    assert "repowise" in local_data["mcpServers"]


def test_install_claude_desktop_preserves_preferences(tmp_path: Path) -> None:
    fake_repo = tmp_path / "my_project"
    fake_repo.mkdir(parents=True)
    fake_desktop_dir = tmp_path / "fake_appdata" / "Claude"
    fake_desktop_dir.mkdir(parents=True)
    config_file = fake_desktop_dir / "claude_desktop_config.json"

    # Pre-populate with user preferences
    initial_config = {
        "preferences": {
            "coworkWebSearchEnabled": True,
            "customTheme": "dark"
        },
        "coworkUserFilesPath": "C:\\Users\\test\\Claude"
    }
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(initial_config, f)

    installer = ClaudeInstaller(repo_root=fake_repo)
    installer.env["claude_desktop_config"] = config_file

    res = installer.install_claude_desktop()
    assert res["status"] == "OK"

    with open(config_file, "r", encoding="utf-8") as f:
        updated = json.load(f)

    # Check preserved user preferences
    assert updated["preferences"]["coworkWebSearchEnabled"] is True
    assert updated["preferences"]["customTheme"] == "dark"
    assert updated["coworkUserFilesPath"] == "C:\\Users\\test\\Claude"

    # Check added mcpServers
    assert "mcpServers" in updated
    assert "repowise" in updated["mcpServers"]
    assert updated["mcpServers"]["repowise"]["args"][1] == str(fake_repo.resolve()).replace("\\", "/")

    # Check backup file created
    backup_file = config_file.with_suffix(".json.bak")
    assert backup_file.exists()


def test_dry_run_mode(tmp_path: Path) -> None:
    fake_repo = tmp_path / "dry_repo"
    fake_repo.mkdir(parents=True)
    fake_desktop_dir = tmp_path / "dry_appdata" / "Claude"
    fake_desktop_dir.mkdir(parents=True)
    config_file = fake_desktop_dir / "claude_desktop_config.json"

    installer = ClaudeInstaller(repo_root=fake_repo, dry_run=True)
    installer.env["claude_desktop_config"] = config_file

    res = installer.install_claude_desktop()
    assert res["status"] == "OK"
    assert not config_file.exists()


def test_verify_checks(tmp_path: Path) -> None:
    fake_repo = tmp_path / "verify_repo"
    fake_repo.mkdir(parents=True)
    installer = ClaudeInstaller(repo_root=fake_repo)
    report = installer.verify()
    assert "overall_status" in report
    assert len(report["checks"]) >= 5
