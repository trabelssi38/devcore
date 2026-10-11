"""Real NTFS ACL checks on temporary files; no active store or account changes."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess

import pytest

from devcore_engine.security.secret_files import (
    SecretProtectionUnavailable, check_credential_file, protect_empty_directory,
    protect_reserved_file, validate_output_path, windows_acl,
)

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Native Windows NTFS qualification")


def powershell(script, path):
    environment = {k: v for k, v in os.environ.items() if k.casefold() != "psmodulepath"}
    environment["DEVCORE_ACL_TEST_PATH"] = str(path)
    executable = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    result = subprocess.run([str(executable), "-NoProfile", "-NonInteractive", "-Command", script],
                            env=environment, capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    return result.stdout.decode("utf-8", "replace").strip()


def descriptor(path):
    return powershell("(Get-Acl -LiteralPath $env:DEVCORE_ACL_TEST_PATH).Sddl", path)


def cli_module():
    source = Path(__file__).resolve().parents[1] / "Scripts/manage_local_identity.py"
    spec = importlib.util.spec_from_file_location("secret_acl_cli_test", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_native_file_acl_is_private_before_secret_bytes_and_paths_are_literal(tmp_path):
    file = tmp_path / "credential[1] $(not-code).json"
    file.touch()
    metadata = protect_reserved_file(file)
    assert metadata["valid"] and metadata["kind"] == "file"
    sddl = descriptor(file)
    assert "D:P" in sddl and "(A;;FA;;;SY)" in sddl
    assert "(A;;FA;;;WD)" not in sddl and "(A;;FA;;;BU)" not in sddl
    # SDDL abbreviates the local Administrator SID as LA on this workstation.
    actual_owner = powershell("(Get-Acl -LiteralPath $env:DEVCORE_ACL_TEST_PATH).GetOwner([System.Security.Principal.SecurityIdentifier]).Value", file)
    assert actual_owner == metadata["owner_sid"]
    file.write_text('{"token":"synthetic-fixture"}', encoding="utf-8")
    before = file.read_bytes()
    assert check_credential_file(file)["inheritance_protected"]
    assert file.read_bytes() == before and descriptor(file) == sddl


def test_existing_nonempty_secret_is_never_repaired_or_modified(tmp_path):
    file = tmp_path / "existing.json"
    file.write_text("existing fixture", encoding="utf-8")
    before, acl = file.read_bytes(), descriptor(file)
    with pytest.raises(SecretProtectionUnavailable):
        protect_reserved_file(file)
    assert file.read_bytes() == before and descriptor(file) == acl


def test_extra_everyone_rule_refuses_read_without_repair(tmp_path):
    file = tmp_path / "credential.json"
    file.touch()
    protect_reserved_file(file)
    file.write_text('{"token":"synthetic-fixture"}', encoding="utf-8")
    broadened = subprocess.run(["icacls.exe", str(file), "/grant", "*S-1-1-0:(F)"],
                               capture_output=True, timeout=15)
    assert broadened.returncode == 0
    before, acl = file.read_bytes(), descriptor(file)
    with pytest.raises(SecretProtectionUnavailable):
        check_credential_file(file)
    with pytest.raises(SecretProtectionUnavailable):
        cli_module().read_admin_authorization(file)
    assert file.read_bytes() == before and descriptor(file) == acl


def test_only_empty_directories_can_be_protected(tmp_path):
    directory = tmp_path / "private"
    directory.mkdir()
    metadata = protect_empty_directory(directory)
    assert metadata["kind"] == "directory"
    assert windows_acl(directory, "CheckDirectory")["valid"]
    (directory / "existing").write_text("fixture", encoding="utf-8")
    before = descriptor(directory)
    with pytest.raises(SecretProtectionUnavailable):
        protect_empty_directory(directory)
    assert descriptor(directory) == before
    assert (directory / "existing").read_text(encoding="utf-8") == "fixture"


def test_parent_junction_is_rejected_before_creation_and_real_target_is_preserved(tmp_path):
    target = tmp_path / "real"
    target.mkdir()
    link = tmp_path / "junction"
    environment = {k: v for k, v in os.environ.items() if k.casefold() != "psmodulepath"}
    environment["DEVCORE_ACL_TEST_TARGET"] = str(target)
    environment["DEVCORE_ACL_TEST_LINK"] = str(link)
    executable = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    result = subprocess.run([str(executable), "-NoProfile", "-NonInteractive", "-Command",
        "New-Item -ItemType Junction -Path $env:DEVCORE_ACL_TEST_LINK -Target $env:DEVCORE_ACL_TEST_TARGET | Out-Null"],
        env=environment, capture_output=True, timeout=15)
    assert result.returncode == 0
    try:
        from devcore_engine.security.private_store import initialize_private_store
        before = descriptor(target)
        with pytest.raises(SecretProtectionUnavailable):
            validate_output_path(link / "secret.json")
        with pytest.raises(SecretProtectionUnavailable):
            initialize_private_store(link / "identity.db")
        assert not (target / "secret.json").exists()
        assert not (target / "identity.db").exists() and descriptor(target) == before
        assert target.is_dir()
    finally:
        os.rmdir(link)  # Remove the junction itself, never recurse into its target.
    assert target.is_dir()


def test_failed_acl_prevents_credential_callback_and_removes_reserved_file(tmp_path, monkeypatch):
    cli = cli_module()
    output = tmp_path / "failed.json"
    def fail(_):
        raise SecretProtectionUnavailable("fixture ACL refusal")
    def never_issue(_):
        raise AssertionError("No credential must be issued before ACL protection")
    monkeypatch.setattr(cli, "protect_reserved_file", fail)
    with pytest.raises(SecretProtectionUnavailable):
        cli.deliver_credential(output, never_issue)
    assert not output.exists()


def test_private_directory_command_does_not_initialize_identity_store(tmp_path, capsys):
    cli = cli_module()
    path = tmp_path / "uninitialized.db"
    directory = tmp_path / "private"
    directory.mkdir()
    cli.main(["--store", str(path), "protect-secret-dir", "--directory", str(directory)])
    assert json.loads(capsys.readouterr().out)["protection"]["valid"]
    assert not path.exists()


def test_parent_powershell_module_path_does_not_change_native_protection(tmp_path, monkeypatch):
    monkeypatch.setenv("PSModulePath", str(tmp_path / "unrelated-modules"))
    file = tmp_path / "empty.json"
    file.touch()
    assert protect_reserved_file(file)["valid"]
