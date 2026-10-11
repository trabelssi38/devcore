import importlib.util
from pathlib import Path
import tomllib

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "Scripts"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


configure = load("configure_codex_mcp")
guard = load("repowise_mcp_local")


def test_config_replaces_stale_tables_and_preserves_other_settings(tmp_path):
    original = b'''model = "existing-model"
[mcp_servers.repowise]
command = "missing.exe"
[mcp_servers.repowise.env]
OLD_SETTING = "old"
[mcp_servers.other]
command = "keep.exe"
[projects."other-project"]
trust_level = "trusted"
'''
    updated = configure.build_config(original, tmp_path, tmp_path / "python.exe", tmp_path / "repo-python.exe",
                                      tmp_path / "local", tmp_path / "shared", "alpha")
    parsed = tomllib.loads(updated)
    assert parsed["model"] == "existing-model"
    assert parsed["mcp_servers"]["other"]["command"] == "keep.exe"
    assert parsed["mcp_servers"]["devcore"]["env"]["DEVCORE_MCP_PROJECT"] == "alpha"
    assert parsed["mcp_servers"]["devcore"]["enabled_tools"] == ["devcore_task_status", "devcore_check", "devcore_project_context"]
    assert parsed["mcp_servers"]["devcore"]["env"]["DEVCORE_CONTEXT_ROOT"] == str(tmp_path / "docs" / "project-context")
    assert parsed["mcp_servers"]["devcore"]["env"]["DEVCORE_CONTEXT_MAX_BYTES"] == "12000"
    assert parsed["mcp_servers"]["repowise"]["env"]["REPOWISE_EMBEDDER"] == "mock"
    assert "OLD_SETTING" not in parsed["mcp_servers"]["repowise"]["env"]
    assert updated == configure.build_config(updated.encode(), tmp_path, tmp_path / "python.exe", tmp_path / "repo-python.exe",
                                             tmp_path / "local", tmp_path / "shared", "alpha")


def test_apply_backs_up_exact_original_and_rejects_concurrent_edit(tmp_path):
    config = tmp_path / ".codex" / "config.toml"
    config.parent.mkdir()
    original = b'model = "old"\n'
    config.write_bytes(original)
    backup = configure.install(config, 'model = "new"\n', original)
    assert backup.read_bytes() == original
    with pytest.raises(ValueError, match="changed since"):
        configure.install(config, 'model = "overwrite"\n', original)
    assert config.read_text() == 'model = "new"\n'


def test_local_socket_guard_rejects_external_access():
    guard.block_external_sockets("socket.connect", (None, ("127.0.0.1", 7337)))
    guard.block_external_sockets("socket.getaddrinfo", ("localhost", 7337))
    for event, args in (("socket.connect", (None, ("8.8.8.8", 443))),
                        ("socket.getaddrinfo", ("api.example.com", 443))):
        with pytest.raises(PermissionError):
            guard.block_external_sockets(event, args)
