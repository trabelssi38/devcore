"""Explicit roots cannot silently redirect operations to another store."""

import builtins
import json
import os
from pathlib import Path

import pytest

from devcore_engine import db


@pytest.fixture
def roots(tmp_path, monkeypatch):
    appdata = tmp_path / "fake-appdata"
    dropbox = tmp_path / "fake-dropbox"
    dropbox.mkdir()
    metadata = appdata / "Dropbox" / "info.json"
    metadata.parent.mkdir(parents=True)
    metadata.write_text(json.dumps({"personal": {"path": str(dropbox)}}))
    monkeypatch.setenv("LOCALAPPDATA", str(appdata))
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setenv("DEVCORE_PLATFORM_ROOT", str(tmp_path / "platform" / "DEV_CORE"))
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(tmp_path / "specified-local"))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(tmp_path / "specified-data"))
    reads = []
    original_open = builtins.open

    def observed_open(file, *args, **kwargs):
        if not isinstance(file, int) and Path(file) == metadata:
            reads.append(str(file))
        return original_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", observed_open)
    return appdata, dropbox, reads


@pytest.mark.parametrize("suffix,exists", [
    ("configured-data", True), ("missing/parents/data", False),
    ("DEV_CORE/DEV_CORE_DATA", True),
])
def test_explicit_data_root_never_reads_dropbox_metadata(tmp_path, monkeypatch, roots, suffix, exists):
    selected = tmp_path / suffix
    if exists:
        selected.mkdir(parents=True)
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(selected))
    assert db.get_data_root() == selected
    assert os.environ["DEVCORE_DATA_ROOT"] == str(selected)
    assert selected.exists() == exists  # Resolving shared data is read-only.
    assert roots[2] == []
    assert not (roots[1] / "DEV_CORE_DATA").exists()


@pytest.mark.parametrize("variable,resolver", [
    ("DEVCORE_DATA_ROOT", db.get_data_root), ("DEVCORE_LOCAL_ROOT", db.get_local_data_root),
])
@pytest.mark.parametrize("invalid", ["", "   "])
def test_invalid_explicit_root_fails_without_fallback(monkeypatch, roots, variable, resolver, invalid):
    monkeypatch.setenv(variable, invalid)
    with pytest.raises(ValueError):
        resolver()
    assert roots[2] == []
    assert not (roots[0] / "DEV_CORE_LOCAL").exists()


@pytest.mark.parametrize("variable,resolver", [
    ("DEVCORE_DATA_ROOT", db.get_data_root), ("DEVCORE_LOCAL_ROOT", db.get_local_data_root),
])
def test_explicit_file_root_is_rejected(tmp_path, monkeypatch, roots, variable, resolver):
    selected = tmp_path / "file-instead-of-directory"
    selected.write_bytes(b"keep me")
    monkeypatch.setenv(variable, str(selected))
    with pytest.raises(NotADirectoryError):
        resolver()
    assert selected.read_bytes() == b"keep me"
    assert roots[2] == []
    assert not (roots[0] / "DEV_CORE_LOCAL").exists()


def test_new_nested_local_root_hosts_default_database(tmp_path, monkeypatch, roots):
    selected = tmp_path / "missing" / "parents" / "local"
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(selected))
    assert db.get_db_path() == selected / "devcore.db"
    with db.connect_db() as conn:
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    conn.close()
    assert (selected / "devcore.db").is_file()
    assert os.environ["DEVCORE_LOCAL_ROOT"] == str(selected)
    assert roots[2] == []
    assert not (roots[0] / "DEV_CORE_LOCAL").exists()


def test_failed_local_creation_does_not_open_another_database(tmp_path, monkeypatch, roots):
    blocked = tmp_path / "parent-file"
    blocked.write_bytes(b"untouched")
    selected = blocked / "missing" / "local"
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(selected))
    with pytest.raises(OSError):
        db.connect_db()
    assert blocked.read_bytes() == b"untouched"
    assert not list(tmp_path.rglob("devcore.db"))
    assert not (roots[0] / "DEV_CORE_LOCAL").exists()
    assert roots[2] == []


def test_permission_failure_does_not_redirect_local_root(tmp_path, monkeypatch, roots):
    selected = tmp_path / "denied-local"
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(selected))
    original_mkdir = Path.mkdir

    def denied_mkdir(path, *args, **kwargs):
        if path == selected:
            raise PermissionError("fixture denied")
        return original_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", denied_mkdir)
    with pytest.raises(PermissionError):
        db.get_db_path()
    assert not (roots[0] / "DEV_CORE_LOCAL").exists()
    assert roots[2] == []


@pytest.mark.skipif(os.name != "nt", reason="Windows legacy discovery")
def test_absent_data_root_retains_legacy_dropbox_discovery(monkeypatch, roots):
    monkeypatch.delenv("DEVCORE_DATA_ROOT")
    expected = roots[1] / "DEV_CORE_DATA"
    assert db.get_data_root() == expected
    assert len(roots[2]) == 1
    assert os.environ["DEVCORE_DATA_ROOT"] == str(expected)
    assert not expected.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows legacy local default")
def test_absent_local_root_retains_localappdata_default(monkeypatch, roots):
    monkeypatch.delenv("DEVCORE_LOCAL_ROOT")
    expected = roots[0] / "DEV_CORE_LOCAL"
    assert db.get_local_data_root() == expected
    assert expected.is_dir()
    assert os.environ["DEVCORE_LOCAL_ROOT"] == str(expected)
    assert roots[2] == []
