"""Real NTFS inheritance while SQLite journals are open, on disposable stores only."""

from contextlib import closing
import json
import os
import sqlite3
import subprocess

import pytest

from devcore_engine.security import private_store
from devcore_engine.security.identity import add_user, connect_existing
from devcore_engine.security.secret_files import SecretProtectionUnavailable
from test_windows_secret_files import cli_module, descriptor

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Native Windows NTFS qualification")


def destination(tmp_path):
    directory = tmp_path / "identity-private"
    directory.mkdir()
    return directory / "identity[1] $(not-code).db"


def test_private_acl_precedes_schema_bytes_and_no_account_is_bootstrapped(tmp_path, monkeypatch):
    path = destination(tmp_path)
    initialize = private_store.initialize_store
    observed = []
    def inspect_before_schema(reserved):
        assert reserved.stat().st_size == 0
        observed.append(private_store.check_store_protection(reserved))
        initialize(reserved)
    monkeypatch.setattr(private_store, "initialize_store", inspect_before_schema)
    metadata = private_store.initialize_private_store(path)
    assert observed[0]["valid"] and metadata["valid"]
    with closing(connect_existing(path)) as conn:
        assert conn.execute("SELECT count(*) FROM identity_users").fetchone()[0] == 0
        assert conn.execute("SELECT version FROM identity_schema").fetchone()[0] == 1


@pytest.mark.parametrize("name", ["identity[1] $(not-code).db", "existing.json"])
def test_nonempty_directory_is_never_adopted_or_repaired(tmp_path, name):
    path = destination(tmp_path)
    existing = path.parent / name
    existing.write_bytes(b"preserve fixture")
    before = descriptor(path.parent), descriptor(existing), existing.read_bytes()
    with pytest.raises(SecretProtectionUnavailable):
        private_store.initialize_private_store(path)
    assert (descriptor(path.parent), descriptor(existing), existing.read_bytes()) == before
    assert sorted(p.name for p in path.parent.iterdir()) == [name]


def test_acl_failure_leaves_empty_reservation_and_never_initializes_schema(tmp_path, monkeypatch):
    path = destination(tmp_path)
    def refuse(_):
        raise SecretProtectionUnavailable("fixture refusal")
    def never_initialize(_):
        raise AssertionError("Schema cannot precede private file ACL")
    monkeypatch.setattr(private_store, "protect_reserved_file", refuse)
    monkeypatch.setattr(private_store, "initialize_store", never_initialize)
    with pytest.raises(SecretProtectionUnavailable):
        private_store.initialize_private_store(path)
    assert path.read_bytes() == b""
    assert sorted(p.name for p in path.parent.iterdir()) == [path.name]


@pytest.mark.parametrize("mode,suffixes", [("DELETE", {"-journal"}), ("WAL", {"-wal", "-shm"})])
def test_sqlite_generated_sidecars_inherit_private_acl_while_transaction_is_open(tmp_path, mode, suffixes):
    path = destination(tmp_path)
    private_store.initialize_private_store(path)
    add_user(path, "alice")
    with closing(sqlite3.connect(path)) as conn:
        assert conn.execute("PRAGMA journal_mode=" + mode).fetchone()[0].upper() == mode
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("UPDATE identity_users SET enabled=0 WHERE id='alice'")
        metadata = private_store.check_store_protection(path)
        assert {child["suffix"] for child in metadata["sidecars"]} == suffixes
        assert all(not child["inheritance_protected"] for child in metadata["sidecars"])
        # The native helper only examines security descriptors, even under a write lock.
        conn.rollback()
    assert private_store.check_store_protection(path)["sidecars"] == []


@pytest.mark.parametrize("target_name", ["directory", "database", "-journal", "-wal", "-shm"])
def test_broadened_store_or_sidecar_acl_is_refused_without_repair(tmp_path, target_name):
    path = destination(tmp_path)
    private_store.initialize_private_store(path)
    add_user(path, "alice")
    with closing(sqlite3.connect(path)) as conn:
        mode = "WAL" if target_name in {"-wal", "-shm"} else "DELETE"
        conn.execute("PRAGMA journal_mode=" + mode)
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("UPDATE identity_users SET enabled=0 WHERE id='alice'")
        target = path.parent if target_name == "directory" else path if target_name == "database" else path.with_name(path.name + target_name)
        grant = subprocess.run(["icacls.exe", str(target), "/grant", "*S-1-1-0:(F)"], capture_output=True, timeout=15)
        assert grant.returncode == 0
        before_acl, before_db = descriptor(target), path.read_bytes()
        with pytest.raises(SecretProtectionUnavailable):
            private_store.check_store_protection(path)
        assert descriptor(target) == before_acl and path.read_bytes() == before_db
        conn.rollback()


def test_cli_inspection_does_not_open_sqlite_or_rewrite_data(tmp_path, capsys, monkeypatch):
    path = destination(tmp_path)
    cli = cli_module()
    cli.main(["--store", str(path), "init-private-store"])
    assert json.loads(capsys.readouterr().out)["protection"]["valid"]
    before = path.read_bytes(), descriptor(path), descriptor(path.parent)
    def never_open(*args, **kwargs):
        raise AssertionError("ACL inspection must not open SQLite")
    monkeypatch.setattr(sqlite3, "connect", never_open)
    cli.main(["--store", str(path), "check-store-protection"])
    metadata = json.loads(capsys.readouterr().out)
    assert metadata["protection"]["sidecars"] == []
    assert (path.read_bytes(), descriptor(path), descriptor(path.parent)) == before
