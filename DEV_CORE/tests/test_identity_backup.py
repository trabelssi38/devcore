"""Private snapshot/restore and abrupt worker stops; temporary identity databases only."""

from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from devcore_engine.security import administration as admin, identity_backup as snapshots, local_recovery as recovery
from devcore_engine.security.browser_sessions import authorize_session, create_session
from devcore_engine.security.identity import READ, AuthenticationRequired, IdentityUnavailable, SqliteIdentityProvider, issue_credential
from devcore_engine.security.private_store import check_store_protection
from devcore_engine.security.secret_files import SecretProtectionUnavailable
from test_local_recovery import private_admin, snapshot, PASSWORD, REPLACEMENT, ORIGIN
from test_windows_secret_files import cli_module, descriptor

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Native NTFS maintenance qualification")


def output(tmp_path, name):
    directory = tmp_path / name
    directory.mkdir()
    return directory / "identity.db"


@pytest.mark.parametrize("mode", ["DELETE", "WAL"])
def test_backup_and_restore_preserve_history_without_resurrecting_any_access(private_admin, tmp_path, mode):
    source, admin_token = private_admin
    with closing(sqlite3.connect(source)) as conn:
        conn.execute("PRAGMA journal_mode=" + mode)
    _, token = issue_credential(source, "bob", ["beta"], [READ], now=1000)
    _, cookie = create_session(source, "Bearer " + token, "beta", ORIGIN, now=1001)
    before = snapshot(source)
    archive = output(tmp_path, "archive")
    receipt = snapshots.backup_identity_store(source, archive)
    assert receipt["archive_only"] and snapshots.file_digest(archive) == receipt["sha256"]
    assert snapshot(source) == before and snapshot(archive) == before
    assert check_store_protection(archive)["sidecars"] == []
    restored = output(tmp_path, "restored")
    result = snapshots.restore_identity_store(archive, restored, receipt["sha256"])
    assert result["relogin_required"] and check_store_protection(restored)["sidecars"] == []
    assert snapshot(source) == before and snapshot(archive) == before
    assert admin.authorize_admin(source, "Bearer " + admin_token, now=1100).user_id == "alice"
    with pytest.raises(AuthenticationRequired):
        admin.authorize_admin(restored, "Bearer " + admin_token, now=1100)
    with pytest.raises(AuthenticationRequired):
        SqliteIdentityProvider(restored).authorize("Bearer " + token, "beta", READ, now=1100)
    with pytest.raises(AuthenticationRequired):
        authorize_session(restored, cookie, "beta", READ, ORIGIN, now=1100)
    with pytest.raises(AuthenticationRequired):
        admin.login_admin(restored, "alice", PASSWORD, now=1100)
    with closing(sqlite3.connect(restored)) as conn:
        assert conn.execute("SELECT id,enabled FROM identity_users ORDER BY id").fetchall() == [("alice", 0), ("bob", 0)]
        assert conn.execute("SELECT user_id FROM identity_passwords").fetchall() == [("alice",)]
        assert conn.execute("SELECT * FROM identity_memberships ORDER BY 1").fetchall() == before["identity_memberships"]
        row = conn.execute("SELECT actor,details FROM identity_audit WHERE action='identity.restore-local'").fetchone()
        assert row[0] == "windows:" + result["operator_sid"]
        assert json.loads(row[1])["backup_sha256"] == receipt["sha256"]
        assert all(secret not in str(row) for secret in (PASSWORD, admin_token, token))
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
    # A restored old password remains invalid even if someone only re-enables the admin.
    with closing(sqlite3.connect(restored)) as conn, conn:
        conn.execute("UPDATE identity_users SET enabled=1 WHERE id='alice'")
    with pytest.raises(AuthenticationRequired):
        admin.login_admin(restored, "alice", PASSWORD, now=1101)
    recovery.recover_admin(restored, "alice", REPLACEMENT, now=1102)
    _, fresh = admin.login_admin(restored, "alice", REPLACEMENT, now=1103)
    assert admin.authorize_admin(restored, "Bearer " + fresh, now=1104).user_id == "alice"


def test_wrong_digest_refuses_before_destination_permissions_or_files_change(private_admin, tmp_path):
    source, _ = private_admin
    archive = output(tmp_path, "archive")
    snapshots.backup_identity_store(source, archive)
    restored = output(tmp_path, "restored")
    before = descriptor(restored.parent), archive.read_bytes()
    with pytest.raises(IdentityUnavailable, match="digest differs"):
        snapshots.restore_identity_store(archive, restored, "0" * 64)
    assert not restored.exists() and list(restored.parent.iterdir()) == []
    assert (descriptor(restored.parent), archive.read_bytes()) == before


@pytest.mark.parametrize("operation", ["backup", "restore"])
def test_existing_destination_is_never_replaced(private_admin, tmp_path, operation):
    source, _ = private_admin
    archive = output(tmp_path, "archive")
    receipt = snapshots.backup_identity_store(source, archive)
    destination = output(tmp_path, "occupied")
    destination.write_bytes(b"preserve existing fixture")
    before = destination.read_bytes(), descriptor(destination), descriptor(destination.parent)
    with pytest.raises(SecretProtectionUnavailable):
        if operation == "backup":
            snapshots.backup_identity_store(source, destination)
        else:
            snapshots.restore_identity_store(archive, destination, receipt["sha256"])
    assert (destination.read_bytes(), descriptor(destination), descriptor(destination.parent)) == before


@pytest.mark.parametrize("mode", ["DELETE", "WAL"])
def test_backup_refuses_an_open_reader_without_creating_a_destination(private_admin, tmp_path, mode):
    source, _ = private_admin
    destination = output(tmp_path, "busy")
    with closing(sqlite3.connect(source)) as reader:
        reader.execute("PRAGMA journal_mode=" + mode)
        reader.execute("BEGIN")
        reader.execute("SELECT * FROM identity_users").fetchall()
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            snapshots.backup_identity_store(source, destination)
        assert not destination.exists() and list(destination.parent.iterdir()) == []
        reader.rollback()


@pytest.mark.parametrize("damage", ["audit", "resurrect"])
def test_failed_restore_never_publishes_an_activatable_store(private_admin, tmp_path, damage):
    source, _ = private_admin
    _, token = issue_credential(source, "alice", ["alpha"], [READ], now=1000)
    with closing(sqlite3.connect(source)) as conn, conn:
        statement = "SELECT RAISE(ABORT,'fixture refusal')" if damage == "audit" else "UPDATE identity_credentials SET revoked=0"
        conn.execute("CREATE TRIGGER restore_fault AFTER INSERT ON identity_audit WHEN NEW.action='identity.restore-local' BEGIN " + statement + "; END")
    archive = output(tmp_path, "archive")
    receipt = snapshots.backup_identity_store(source, archive)
    before = snapshot(archive)
    destination = output(tmp_path, "failed")
    with pytest.raises((sqlite3.DatabaseError, IdentityUnavailable)):
        snapshots.restore_identity_store(archive, destination, receipt["sha256"])
    assert not destination.exists() and snapshot(archive) == before
    pending = list(destination.parent.glob(".*.pending-*"))
    assert len(pending) == 1 and check_store_protection(pending[0])["valid"]


def test_backup_failure_before_sqlite_copy_preserves_protected_empty_stage(private_admin, tmp_path, monkeypatch):
    source, _ = private_admin
    destination = output(tmp_path, "failed-copy")
    def refuse(*args):
        raise OSError("fixture copy failure")
    monkeypatch.setattr(snapshots, "copy_snapshot", refuse)
    with pytest.raises(OSError):
        snapshots.backup_identity_store(source, destination)
    assert not destination.exists()
    pending = list(destination.parent.iterdir())
    assert len(pending) == 1 and pending[0].stat().st_size == 0
    assert check_store_protection(pending[0])["valid"]


def worker(code, arguments, tmp_path):
    environment = dict(os.environ)
    environment["DEVCORE_LOCAL_ROOT"] = str(tmp_path / "worker-local")
    environment["DEVCORE_DATA_ROOT"] = str(tmp_path / "worker-data")
    engine = str(Path(__file__).resolve().parents[1])
    return subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0,sys.argv[1]); " + code,
                           engine, *map(str, arguments)], env=environment, cwd=tmp_path,
                          capture_output=True, timeout=35)


@pytest.mark.parametrize("mode", ["DELETE", "WAL"])
def test_abrupt_recovery_stop_rolls_back_after_reopening(private_admin, tmp_path, mode):
    source, _ = private_admin
    with closing(sqlite3.connect(source)) as conn:
        conn.execute("PRAGMA journal_mode=" + mode)
    before = snapshot(source)
    code = ("import os; from devcore_engine.security import local_recovery as r; "
            "r.audit=lambda *a,**k: os._exit(77); "
            "r.recover_admin(sys.argv[2],'alice','Une phrase interrompue de recette')")
    result = worker(code, [source], tmp_path)
    assert result.returncode == 77, result.stderr.decode("utf-8", "replace")
    assert check_store_protection(source)["valid"]
    # rw opening performs SQLite crash recovery inside the private directory.
    with closing(sqlite3.connect(source)) as conn:
        assert conn.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
    assert snapshot(source) == before


def test_abrupt_restore_stop_leaves_only_unpublished_private_stage(private_admin, tmp_path):
    source, _ = private_admin
    archive = output(tmp_path, "archive")
    receipt = snapshots.backup_identity_store(source, archive)
    before = snapshot(archive)
    destination = output(tmp_path, "interrupted")
    code = ("import os; from devcore_engine.security import identity_backup as b; "
            "b.audit=lambda *a,**k: os._exit(78); "
            "b.restore_identity_store(sys.argv[2],sys.argv[3],sys.argv[4])")
    result = worker(code, [archive, destination, receipt["sha256"]], tmp_path)
    assert result.returncode == 78, result.stderr.decode("utf-8", "replace")
    assert not destination.exists() and snapshot(archive) == before
    pending = list(destination.parent.glob(".*.pending-*"))
    assert len(pending) >= 1
    stage = next(p for p in pending if not p.name.endswith("-journal"))
    assert check_store_protection(stage)["valid"]


def test_cli_confirmation_and_receipts_have_no_credentials(private_admin, tmp_path, monkeypatch, capsys):
    source, token = private_admin
    archive = output(tmp_path, "archive")
    cli = cli_module()
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)
    args = ["--store", str(source), "backup-private-store", "--output", str(archive)]
    with pytest.raises(ValueError, match="maintenance confirmation"):
        cli.main(args)
    cli.main(args + ["--confirm-services-stopped"])
    receipt = json.loads(capsys.readouterr().out)
    destination = output(tmp_path, "restored")
    restore_args = ["--store", str(destination), "restore-private-store", "--backup", str(archive),
                    "--expected-sha256", receipt["sha256"], "--confirm-services-stopped"]
    with pytest.raises(ValueError, match="maintenance confirmation"):
        cli.main(restore_args)
    cli.main(restore_args + ["--confirm-local-restore"])
    stdout = capsys.readouterr().out
    assert json.loads(stdout)["relogin_required"]
    assert PASSWORD not in stdout and token not in stdout
