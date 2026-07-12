import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("server.py")


def load_server():
    spec = importlib.util.spec_from_file_location("obsidian_vault_server_under_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_vault_read_rejects_path_traversal(tmp_path):
    server = load_server()
    server.VAULT_PATH = tmp_path / "Vault"
    server.VAULT_PATH.mkdir()

    result = server.read_file("../outside.md")

    assert result["success"] is False
    assert "vault root" in result["error"]


def test_vault_write_rejects_path_traversal(tmp_path):
    server = load_server()
    server.VAULT_PATH = tmp_path / "Vault"
    server.VAULT_PATH.mkdir()

    result = server.write_file("../outside.md", "blocked")

    assert result["success"] is False
    assert "vault root" in result["error"]
    assert not (tmp_path / "outside.md").exists()


def test_vault_write_accepts_relative_path_inside_root(tmp_path):
    server = load_server()
    server.VAULT_PATH = tmp_path / "Vault"
    server.VAULT_PATH.mkdir()

    result = server.write_file("Decisions/inside.md", "ok")

    assert result["success"] is True
    assert (server.VAULT_PATH / "Decisions" / "inside.md").read_text(encoding="utf-8") == "ok"


def test_vault_list_rejects_folder_traversal(tmp_path):
    server = load_server()
    server.VAULT_PATH = tmp_path / "Vault"
    server.VAULT_PATH.mkdir()

    result = server.list_notes_in_folder("../")

    assert result == [{"error": f"Path escapes vault root: {server.VAULT_PATH.resolve()}"}]
