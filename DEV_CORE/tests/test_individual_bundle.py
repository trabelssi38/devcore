"""Immutable allowlisted source snapshots; fixtures never use live state."""
import importlib.util
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

from Scripts import build_individual_bundle as builder
from Scripts.build_individual_bundle import FILES, build, verify


@pytest.fixture
def sources(tmp_path):
    root = tmp_path / "source"
    for name in FILES:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture", encoding="utf-8")
    (root / "secret.db").write_bytes(b"must not be copied")
    return root


def test_allowlist_and_no_overwrite(sources, tmp_path):
    destination = tmp_path / "bundle"
    result = build(sources, destination)
    assert verify(destination) == result
    assert not (destination / "secret.db").exists()
    assert result["operationally_qualified"] is False
    with pytest.raises(ValueError, match="overwrite"):
        build(sources, destination)
    assert verify(destination) == result


@pytest.mark.parametrize("change", ["tamper", "extra", "missing"])
def test_modified_bundle_rejected(sources, tmp_path, change):
    destination = tmp_path / "bundle"
    build(sources, destination)
    if change == "tamper":
        (destination / FILES[0]).write_text("tampered", encoding="utf-8")
    elif change == "extra":
        (destination / "credential.txt").write_text("unexpected", encoding="utf-8")
    else:
        (destination / FILES[0]).unlink()
    with pytest.raises(ValueError):
        verify(destination)


def test_source_destination_and_missing_file_refused(sources, tmp_path):
    with pytest.raises(ValueError, match="outside"):
        build(sources, sources / "output")
    (sources / FILES[0]).unlink()
    with pytest.raises(ValueError, match="Missing"):
        build(sources, tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_source_change_during_copy_never_publishes(sources, tmp_path, monkeypatch):
    original = builder.shutil.copyfile

    def changed(source, target):
        result = original(source, target)
        source.write_text("concurrent edit", encoding="utf-8")
        return result

    monkeypatch.setattr(builder.shutil, "copyfile", changed)
    with pytest.raises(ValueError, match="changed"):
        build(sources, tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_source_link_refused_without_copy(sources, tmp_path, monkeypatch):
    target = sources / FILES[0]
    original = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda path: path == target or original(path))
    with pytest.raises(ValueError, match="Links"):
        build(sources, tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_real_snapshot_http_individual_gate_without_legacy_dependencies(tmp_path, monkeypatch):
    platform = Path(__file__).resolve().parents[1]
    destination = tmp_path / "bundle"
    build(platform, destination)
    local, data = tmp_path / "local", tmp_path / "data"
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(local))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(data))
    monkeypatch.setenv("DEVCORE_PLATFORM_ROOT", str(destination))
    monkeypatch.setenv("DEVCORE_DASHBOARD_AUTH_PROFILE", "individual")
    monkeypatch.setenv("DEVCORE_IDENTITY_STORE", str(local / "absent.db"))
    monkeypatch.setattr(sys, "dont_write_bytecode", True)
    spec = importlib.util.spec_from_file_location("bundle_dashboard", destination / FILES[0])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with TestClient(module.app) as client:
        assert client.get("/project").status_code == 200
        assert client.get("/project.js").status_code == 200
        assert client.get("/api/dashboard/tasks?project=alpha").status_code == 401
        assert client.get("/api/settings").status_code == 403
    assert not local.exists() and not data.exists()
    assert verify(destination)
