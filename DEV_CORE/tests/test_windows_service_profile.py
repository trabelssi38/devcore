"""Portable service paths stay outside the versioned release and preserve data."""
import json
from pathlib import Path
import sys
import types

import pytest

from Scripts.install_individual_service import install, prepare
from devcore_engine.windows_service import load_profile


def fixture_release(tmp_path):
    release = tmp_path / "runtime" / "releases" / "candidate"
    (release / "individual-platform-v2").mkdir(parents=True)
    (release / "individual-platform-v2" / "manifest.json").write_text("{}", encoding="utf-8")
    (release / "Scripts").mkdir()
    (release / "Scripts" / "python.exe").write_bytes(b"fixture")
    (release / "pythonservice.exe").write_bytes(b"fixture")
    (release / "controls" / "Scripts").mkdir(parents=True)
    return release


def test_portable_roots_survive_release_change(tmp_path):
    release = fixture_release(tmp_path)
    report = prepare(release, "state/local", "state/data")
    assert Path(report["local_root"]) == tmp_path / "runtime" / "state" / "local"
    assert Path(report["data_root"]) == tmp_path / "runtime" / "state" / "data"
    assert not report["identity_ready"]
    identity = Path(report["local_root"]) / "Security" / "identity.db"
    identity.parent.mkdir()
    identity.write_bytes(b"untouched")
    profile = load_profile(release)
    assert profile["identity"] == identity
    assert prepare(release, "state/local", "state/data")["identity_ready"]
    assert identity.read_bytes() == b"untouched"


@pytest.mark.parametrize("bad", ["../outside", "C:relative", "C:/absolute", "", "state/../other"])
def test_unsafe_portable_root_rejected_before_configuration(tmp_path, bad):
    release = fixture_release(tmp_path)
    with pytest.raises(ValueError):
        prepare(release, bad, "state/data")
    assert not (release / "individual-service.json").exists()


def test_existing_configuration_cannot_be_repointed(tmp_path):
    release = fixture_release(tmp_path)
    prepare(release, "state/local", "state/data")
    original = (release / "individual-service.json").read_bytes()
    with pytest.raises(ValueError, match="differs"):
        prepare(release, "other/local", "state/data")
    assert (release / "individual-service.json").read_bytes() == original


@pytest.mark.parametrize("startup", ["automatic", "manual"])
def test_windows_startup_setting_reaches_service_manager(tmp_path, monkeypatch, startup):
    release = fixture_release(tmp_path)
    prepare(release, "state/local", "state/data", startup)
    identity = tmp_path / "runtime" / "state" / "local" / "Security" / "identity.db"
    identity.parent.mkdir()
    identity.write_bytes(b"fixture")
    profile = load_profile(release)
    assert profile["windows_startup"] == startup
    assert json.loads((release / "individual-service.json").read_text())["windows_startup"] == startup

    calls = []
    monkeypatch.setitem(sys.modules, "win32service", types.SimpleNamespace(
        SERVICE_AUTO_START=2, SERVICE_DEMAND_START=3))
    monkeypatch.setitem(sys.modules, "win32serviceutil", types.SimpleNamespace(
        InstallService=lambda *args, **kwargs: calls.append(kwargs)))
    monkeypatch.setattr("Scripts.install_individual_service.getpass.getpass", lambda _: "fixture")
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: types.SimpleNamespace(returncode=0))
    result = install(release, ".\\Fixture", False)
    assert calls[0]["startType"] == (2 if startup == "automatic" else 3)
    assert result["windows_startup"] == startup
    assert not result["start_requested"]


def test_existing_service_is_reconfigured_without_delete(tmp_path, monkeypatch):
    release = fixture_release(tmp_path)
    prepare(release, "state/local", "state/data", "automatic")
    identity = tmp_path / "runtime" / "state" / "local" / "Security" / "identity.db"
    identity.parent.mkdir()
    identity.write_bytes(b"fixture")

    class ExistingServiceError(Exception):
        winerror = 1073

    calls = []
    monkeypatch.setitem(sys.modules, "win32service", types.SimpleNamespace(SERVICE_AUTO_START=2))
    monkeypatch.setitem(sys.modules, "win32serviceutil", types.SimpleNamespace(
        InstallService=lambda *args, **kwargs: (_ for _ in ()).throw(ExistingServiceError()),
        ChangeServiceConfig=lambda *args, **kwargs: calls.append((args, kwargs)),
    ))
    monkeypatch.setattr("Scripts.install_individual_service.getpass.getpass", lambda _: "fixture")
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: types.SimpleNamespace(returncode=0))
    result = install(release, ".\\Fixture", False)
    assert result["installed"]
    assert len(calls) == 1
    assert calls[0][0][1] == "DevCoreIndividual"
    assert calls[0][1]["startType"] == 2


def test_invalid_windows_startup_rejected(tmp_path):
    release = fixture_release(tmp_path)
    with pytest.raises(ValueError, match="Windows startup"):
        prepare(release, "state/local", "state/data", "disabled")
    assert not (release / "individual-service.json").exists()


def test_legacy_service_profile_defaults_to_automatic(tmp_path):
    release = fixture_release(tmp_path)
    prepare(release, "state/local", "state/data")
    config_path = release / "individual-service.json"
    config = json.loads(config_path.read_text())
    config["schema_version"] = 1
    del config["windows_startup"]
    config_path.write_text(json.dumps(config))
    identity = tmp_path / "runtime" / "state" / "local" / "Security" / "identity.db"
    identity.parent.mkdir()
    identity.write_bytes(b"fixture")
    assert load_profile(release)["windows_startup"] == "automatic"
    assert prepare(release, "state/local", "state/data")["windows_startup"] == "automatic"
    assert json.loads(config_path.read_text()) == config
