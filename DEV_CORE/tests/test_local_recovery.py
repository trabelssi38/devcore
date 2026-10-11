"""Local OS recovery on private temporary NTFS stores, never on live identities."""

from contextlib import closing
import json
import os
import sqlite3
import subprocess

import pytest

from devcore_engine.security import administration as admin, local_recovery as recovery, passwords
from devcore_engine.security.browser_sessions import authorize_session, create_session, upgrade_session_store
from devcore_engine.security.identity import (
    READ, WRITE, AuthenticationRequired, ProjectAccessDenied, SqliteIdentityProvider,
    add_user, issue_credential, set_membership,
)
from devcore_engine.security.private_store import initialize_private_store, check_store_protection
from devcore_engine.security.secret_files import SecretProtectionUnavailable
from test_windows_secret_files import cli_module

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Native Windows operator recovery")
PASSWORD = "Une phrase de recette initiale"
REPLACEMENT = "Une phrase renouvelée pour la recette"
ORIGIN = "http://localhost"


@pytest.fixture
def private_admin(tmp_path):
    directory = tmp_path / "identity"
    directory.mkdir()
    path = directory / "identity.db"
    initialize_private_store(path)
    upgrade_session_store(path)
    passwords.upgrade_password_store(path)
    for user, project, role in (("alice", "alpha", "owner"), ("bob", "beta", "reader")):
        add_user(path, user)
        set_membership(path, user, project, role)
        passwords.set_password(path, user, PASSWORD, now=1000)
    admin.upgrade_admin_store(path)
    admin.bootstrap_admin(path, "alice", now=1000)
    _, token = admin.login_admin(path, "alice", PASSWORD, now=1000)
    return path, token


def snapshot(path):
    with closing(sqlite3.connect(path)) as conn:
        return {name: conn.execute("SELECT * FROM " + name + " ORDER BY 1").fetchall()
                for name in ("identity_users", "identity_passwords", "identity_memberships",
                             "identity_credentials", "identity_browser_sessions", "identity_admin_credentials")}


@pytest.mark.parametrize("disabled", [False, True])
@pytest.mark.parametrize("mode", ["DELETE", "WAL"])
def test_recovery_restores_existing_admin_revokes_only_target_and_records_windows_sid(private_admin, disabled, mode):
    path, old_admin = private_admin
    with closing(sqlite3.connect(path)) as conn:
        assert conn.execute("PRAGMA journal_mode=" + mode).fetchone()[0].upper() == mode
    _, alice_token = issue_credential(path, "alice", ["alpha"], [READ, WRITE], now=1000)
    _, alice_cookie = create_session(path, "Bearer " + alice_token, "alpha", ORIGIN, now=1001)
    _, bob_token = issue_credential(path, "bob", ["beta"], [READ], now=1000)
    _, bob_cookie = create_session(path, "Bearer " + bob_token, "beta", ORIGIN, now=1001)
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("UPDATE identity_users SET enabled=? WHERE id='alice'", (int(not disabled),))
        conn.execute("UPDATE identity_passwords SET failures=5,blocked_until=9999 WHERE user_id='alice'")
    before = snapshot(path)
    sid = check_store_protection(path)["owner_sid"]
    result = recovery.recover_admin(path, "alice", REPLACEMENT, now=1100)
    assert result == {"user": "alice", "operator_sid": sid, "relogin_required": True}
    with pytest.raises(AuthenticationRequired):
        admin.authorize_admin(path, "Bearer " + old_admin, now=1101)
    with pytest.raises(AuthenticationRequired):
        SqliteIdentityProvider(path).authorize("Bearer " + alice_token, "alpha", READ, now=1101)
    with pytest.raises(AuthenticationRequired):
        authorize_session(path, alice_cookie, "alpha", READ, ORIGIN, now=1101)
    assert authorize_session(path, bob_cookie, "beta", READ, ORIGIN, now=1101).principal.user_id == "bob"
    with pytest.raises(AuthenticationRequired):
        admin.login_admin(path, "alice", PASSWORD, now=1101)
    _, fresh = admin.login_admin(path, "alice", REPLACEMENT, now=1102)
    assert admin.authorize_admin(path, "Bearer " + fresh, now=1103).user_id == "alice"
    with closing(sqlite3.connect(path)) as conn:
        row = conn.execute("SELECT actor,details FROM identity_audit WHERE action='admin.recover-local'").fetchone()
        assert row[0] == "windows:" + sid
        assert json.loads(row[1]) == {"operator_sid": sid, "previously_enabled": not disabled, "maintenance": True}
        assert all(secret not in str(row) for secret in (PASSWORD, REPLACEMENT, old_admin, alice_token))
        assert conn.execute("SELECT user_id FROM identity_instance_admins").fetchall() == [("alice",)]
        assert conn.execute("SELECT bootstrapped FROM identity_admin_state").fetchone()[0] == 1
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    after = snapshot(path)
    assert after["identity_memberships"] == before["identity_memberships"]
    assert [r for r in after["identity_passwords"] if r[0] == "bob"] == [r for r in before["identity_passwords"] if r[0] == "bob"]


@pytest.mark.parametrize("target", ["bob", "unknown"])
def test_recovery_never_promotes_or_creates_an_admin(private_admin, monkeypatch, target):
    path, _ = private_admin
    before = snapshot(path)
    def never_hash(_):
        raise AssertionError("Invalid target must be refused before hashing")
    monkeypatch.setattr(passwords, "hash_password", never_hash)
    with pytest.raises(ProjectAccessDenied):
        recovery.recover_admin(path, target, REPLACEMENT)
    assert snapshot(path) == before


@pytest.mark.parametrize("damage", ["absent", "reject"])
def test_audit_failure_rolls_back_password_reactivation_and_all_revocations(private_admin, damage):
    path, _ = private_admin
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("UPDATE identity_users SET enabled=0 WHERE id='alice'")
        if damage == "absent":
            conn.execute("DROP TABLE identity_audit")
        else:
            conn.execute("""CREATE TRIGGER reject_recovery BEFORE INSERT ON identity_audit
                WHEN NEW.action='admin.recover-local' BEGIN SELECT RAISE(ABORT,'fixture refusal'); END""")
    before = snapshot(path)
    with pytest.raises(sqlite3.DatabaseError):
        recovery.recover_admin(path, "alice", REPLACEMENT)
    assert snapshot(path) == before


@pytest.mark.parametrize("mode,holder", [("DELETE", "reader"), ("DELETE", "writer"), ("WAL", "reader"), ("WAL", "writer")])
def test_exclusive_maintenance_refuses_an_existing_sqlite_transaction(private_admin, mode, holder):
    path, _ = private_admin
    with closing(sqlite3.connect(path)) as conn:
        assert conn.execute("PRAGMA journal_mode=" + mode).fetchone()[0].upper() == mode
        conn.execute("BEGIN" if holder == "reader" else "BEGIN IMMEDIATE")
        conn.execute("SELECT * FROM identity_users").fetchall()
        before = snapshot(path)
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            recovery.recover_admin(path, "alice", REPLACEMENT)
        assert snapshot(path) == before
        conn.rollback()


@pytest.mark.parametrize("change", ["role", "acl"])
def test_admission_is_repeated_after_hashing(private_admin, monkeypatch, change):
    path, _ = private_admin
    original = passwords.hash_password
    before = snapshot(path)
    def hash_then_change(password):
        encoded = original(password)
        if change == "role":
            with closing(sqlite3.connect(path)) as conn, conn:
                conn.execute("DELETE FROM identity_instance_admins WHERE user_id='alice'")
        else:
            result = subprocess.run(["icacls.exe", str(path), "/grant", "*S-1-1-0:(F)"], capture_output=True, timeout=15)
            assert result.returncode == 0
        return encoded
    monkeypatch.setattr(passwords, "hash_password", hash_then_change)
    with pytest.raises((ProjectAccessDenied, SecretProtectionUnavailable)):
        recovery.recover_admin(path, "alice", REPLACEMENT)
    assert snapshot(path) == before


@pytest.mark.parametrize("tty,flags", [(False, ["--confirm-local-recovery", "--confirm-services-stopped"]),
                                        (True, ["--confirm-local-recovery"]), (True, ["--confirm-services-stopped"])])
def test_cli_requires_interactive_maintenance_flags_before_prompt_or_store_access(tmp_path, monkeypatch, tty, flags):
    cli = cli_module()
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: tty)
    def never_prompt(_):
        raise AssertionError("Missing confirmation cannot prompt")
    monkeypatch.setattr(cli.getpass, "getpass", never_prompt)
    path = tmp_path / "absent.db"
    with pytest.raises(ValueError, match="maintenance confirmation"):
        cli.main(["--store", str(path), "recover-local-admin", "--user", "alice", *flags])
    assert not path.exists()


def test_cli_masked_confirmation_and_relogin_without_admin_token(private_admin, monkeypatch, capsys):
    path, old_admin = private_admin
    cli = cli_module()
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)
    answers = iter([REPLACEMENT, "Une confirmation différente"])
    monkeypatch.setattr(cli.getpass, "getpass", lambda _: next(answers))
    args = ["--store", str(path), "recover-local-admin", "--user", "alice", "--confirm-local-recovery", "--confirm-services-stopped"]
    before = snapshot(path)
    with pytest.raises(ValueError, match="confirmation differs"):
        cli.main(args)
    assert snapshot(path) == before
    monkeypatch.setattr(cli.getpass, "getpass", lambda _: REPLACEMENT)
    cli.main(args)
    stdout = capsys.readouterr().out
    result = json.loads(stdout)
    assert result["relogin_required"] and result["operator_sid"].startswith("S-1-")
    assert all(secret not in stdout for secret in (PASSWORD, REPLACEMENT, old_admin))
    _, token = admin.login_admin(path, "alice", REPLACEMENT)
    assert admin.authorize_admin(path, "Bearer " + token).user_id == "alice"


@pytest.mark.parametrize("refusal", ["non-admin", "acl"])
def test_cli_rejects_target_or_native_acl_before_password_prompt(private_admin, monkeypatch, refusal):
    path, _ = private_admin
    cli = cli_module()
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)
    def never_prompt(_):
        raise AssertionError("Recovery admission must precede secret entry")
    monkeypatch.setattr(cli.getpass, "getpass", never_prompt)
    target = "bob"
    if refusal == "acl":
        target = "alice"
        grant = subprocess.run(["icacls.exe", str(path), "/grant", "*S-1-1-0:(F)"], capture_output=True, timeout=15)
        assert grant.returncode == 0
    before = snapshot(path)
    with pytest.raises((ProjectAccessDenied, SecretProtectionUnavailable)):
        cli.main(["--store", str(path), "recover-local-admin", "--user", target,
                  "--confirm-local-recovery", "--confirm-services-stopped"])
    assert snapshot(path) == before


def test_regular_admin_capability_cannot_invoke_local_recovery(private_admin):
    path, token = private_admin
    before = snapshot(path)
    with pytest.raises(ValueError, match="Unsupported"):
        admin.administer(path, "Bearer " + token, "recover-local-admin", user="alice", password=REPLACEMENT, now=1100)
    assert snapshot(path) == before
