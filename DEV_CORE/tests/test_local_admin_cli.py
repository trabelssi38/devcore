"""Local bootstrap boundary, CLI author authentication and secret delivery."""

import importlib.util
import json
from pathlib import Path
import sqlite3

import pytest

from test_instance_administration import prepared, managed, PASSWORD
from devcore_engine.security import administration as admin
from devcore_engine.security.identity import READ, AuthenticationRequired, issue_credential
from devcore_engine.security.secret_files import (
    SecretProtectionUnavailable, check_credential_file, protect_reserved_file,
)


@pytest.fixture
def cli(monkeypatch):
    source = Path(__file__).resolve().parents[1] / "Scripts" / "manage_local_identity.py"
    spec = importlib.util.spec_from_file_location("admin_cli_under_test", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module.sys.stdin, "isatty", lambda: True)
    return module


def test_bootstrap_requires_local_interactive_confirmation_and_cannot_repeat(prepared, cli, monkeypatch):
    admin.upgrade_admin_store(prepared)
    args = ["--store", str(prepared), "bootstrap-admin", "--user", "alice"]
    with pytest.raises(ValueError):
        cli.main(args)
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: False)
    with pytest.raises(ValueError):
        cli.main(args + ["--confirm-local-bootstrap"])
    with sqlite3.connect(prepared) as conn:
        assert conn.execute("SELECT bootstrapped FROM identity_admin_state").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM identity_audit").fetchone()[0] == 0
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)
    cli.main(args + ["--confirm-local-bootstrap"])
    with pytest.raises(PermissionError):
        cli.main(args + ["--confirm-local-bootstrap"])


@pytest.mark.parametrize("command,extra", [
    ("add-user", ["--user", "charlie"]),
    ("grant", ["--user", "bob", "--project", "alpha", "--role", "owner"]),
    ("reset-password", ["--user", "alice"]),
    ("issue-token", ["--user", "alice", "--project", "alpha", "--action", "task.read"]),
])
def test_schema4_provisioning_refuses_missing_admin_before_password_or_file(managed, cli, monkeypatch, tmp_path, command, extra):
    path, _, _ = managed
    before = path.read_bytes()
    def never_prompt(*_):
        raise AssertionError("Unauthorized caller must not be prompted")
    monkeypatch.setattr(cli.getpass, "getpass", never_prompt)
    output = tmp_path / "no-secret.json"
    if command == "issue-token":
        extra = extra + ["--output", str(output)]
    with pytest.raises(ValueError, match="administrative credential file"):
        cli.main(["--store", str(path), command, *extra])
    assert path.read_bytes() == before
    assert not output.exists()


def test_project_token_file_cannot_administer_and_authenticated_cli_uses_token_actor(managed, cli, tmp_path, capsys):
    path, _, token = managed
    _, project_token = issue_credential(path, "alice", ["alpha"], [READ])
    file = tmp_path / "credential.json"
    file.touch()
    protect_reserved_file(file)
    file.write_text(json.dumps({"token": project_token}), encoding="utf-8")
    args = ["--store", str(path), "--admin-credential-file", str(file)]
    with pytest.raises(AuthenticationRequired):
        cli.main(args + ["add-user", "--user", "charlie"])
    # Reissue in real time for this CLI process; managed's deterministic token has expired.
    _, fresh = admin.login_admin(path, "alice", PASSWORD)
    file.write_text(json.dumps({"token": fresh}), encoding="utf-8")
    cli.main(args + ["add-user", "--user", "charlie"])
    cli.main(args + ["grant", "--user", "charlie", "--project", "gamma", "--role", "reader"])
    delivered = tmp_path / "project-token.json"
    cli.main(args + ["issue-token", "--user", "charlie", "--project", "gamma", "--action", READ, "--output", str(delivered)])
    saved = json.loads(delivered.read_text(encoding="utf-8"))
    assert saved["token"] and saved["credential_id"]
    out = capsys.readouterr().out
    assert all(secret not in out for secret in (fresh, token, project_token, saved["token"], PASSWORD))
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT actor FROM identity_audit WHERE action='identity.add-user'").fetchall() == [("alice",)]


def test_login_delivery_is_exclusive_and_failed_output_leaves_no_new_credential(managed, cli, monkeypatch, tmp_path, capsys):
    path, _, _ = managed
    monkeypatch.setattr(cli.getpass, "getpass", lambda *_: PASSWORD)
    output = tmp_path / "admin-token.json"
    args = ["--store", str(path), "login-admin", "--user", "alice", "--output", str(output)]
    cli.main(args)
    raw = output.read_bytes()
    secret = json.loads(raw)["token"]
    assert secret not in capsys.readouterr().out
    assert admin.authorize_admin(path, "Bearer " + secret).user_id == "alice"
    with pytest.raises(FileExistsError):
        cli.main(args)
    assert output.read_bytes() == raw
    with sqlite3.connect(path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM identity_admin_credentials").fetchone()[0]
    def fail_fsync(_):
        raise OSError("fixture disk failure")
    monkeypatch.setattr(cli.os, "fsync", fail_fsync)
    failed = tmp_path / "failed.json"
    with pytest.raises(OSError):
        cli.main(["--store", str(path), "login-admin", "--user", "alice", "--output", str(failed)])
    assert not failed.exists()
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM identity_admin_credentials").fetchone()[0] == count


def test_legacy_project_issuance_protects_before_creating_credential(prepared, cli, monkeypatch, tmp_path):
    output = tmp_path / "legacy-project.json"
    args = ["--store", str(prepared), "issue-token", "--user", "alice", "--project", "alpha", "--action", READ]
    cli.main(args + ["--output", str(output)])
    check_credential_file(output)
    with sqlite3.connect(prepared) as conn:
        before = conn.execute("SELECT COUNT(*) FROM identity_credentials").fetchone()[0]
    def reject(_):
        raise SecretProtectionUnavailable("fixture ACL refusal")
    monkeypatch.setattr(cli, "protect_reserved_file", reject)
    failed = tmp_path / "not-written.json"
    with pytest.raises(SecretProtectionUnavailable):
        cli.main(args + ["--output", str(failed)])
    assert not failed.exists()
    with sqlite3.connect(prepared) as conn:
        assert conn.execute("SELECT COUNT(*) FROM identity_credentials").fetchone()[0] == before
