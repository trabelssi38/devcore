"""A candidate must bind the archived wheel to the installed engine files."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from Scripts.verify_engine_release import verify


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def candidate(tmp_path):
    release = tmp_path / "releases" / "candidate"
    package = release / "Lib" / "site-packages" / "devcore_engine"
    package.mkdir(parents=True)
    engine_init = package / "__init__.py"
    engine_init.write_bytes(b"engine\n")
    (package / "schema.sql").write_bytes(b"CREATE TABLE fixture(id);\n")
    wheel = release / "artifacts" / "wheels" / "devcore_engine-10.2.0-py3-none-any.whl"
    wheel.parent.mkdir(parents=True)
    wheel.write_bytes(b"fixture wheel")
    manifest = release / "artifacts" / "manifest.json"
    manifest.write_text(json.dumps({
        "source_files_sha256": {
            "devcore_engine/__init__.py": sha(engine_init.read_bytes()),
            "devcore_engine/schema.sql": sha((package / "schema.sql").read_bytes()),
        },
        "wheel_sha256": {wheel.name: sha(wheel.read_bytes())},
    }), encoding="utf-8")
    packages = release / "installed-packages.txt"
    packages.write_bytes(b"devcore-engine==10.2.0\n")
    (release / "provenance.json").write_text(json.dumps({
        "engine_artifact_manifest_sha256": sha(manifest.read_bytes()),
        "installed_packages_sha256": sha(packages.read_bytes()),
    }), encoding="utf-8")
    return release, engine_init, manifest, wheel


def test_release_attestation_detects_wheel_and_installed_code_changes(tmp_path):
    release, engine_init, manifest, wheel = candidate(tmp_path)
    assert verify(release, engine_init)["installed_engine_files"] == 2
    wheel.write_bytes(b"replacement wheel")
    with pytest.raises(ValueError, match="wheel differs"):
        verify(release, engine_init)
    wheel.write_bytes(b"fixture wheel")
    engine_init.write_bytes(b"replacement engine")
    with pytest.raises(ValueError, match="Installed engine differs"):
        verify(release, engine_init)
    engine_init.write_bytes(b"engine\n")
    manifest.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="provenance"):
        verify(release, engine_init)
    manifest.write_text(json.dumps({
        "source_files_sha256": {"devcore_engine/__init__.py": sha(engine_init.read_bytes()),
                                "devcore_engine/schema.sql": sha((engine_init.parent / "schema.sql").read_bytes())},
        "wheel_sha256": {wheel.name: sha(wheel.read_bytes())},
    }), encoding="utf-8")
    provenance_path = release / "provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["engine_artifact_manifest_sha256"] = sha(manifest.read_bytes())
    provenance_path.write_text(json.dumps(provenance), encoding="utf-8")
    (release / "installed-packages.txt").write_bytes(b"changed\n")
    with pytest.raises(ValueError, match="package inventory"):
        verify(release, engine_init)


def test_release_attestation_binds_windows_service_runtime(tmp_path):
    release, engine_init, _, _ = candidate(tmp_path)
    components = {name: sha(name.encode()) for name in
                  ("python313.dll", "python3.dll", "pywintypes313.dll", "python313._pth")}
    for name in components:
        (release / name).write_bytes(name.encode())
    host = release / "pythonservice.exe"
    host.write_bytes(b"host")
    provenance_path = release / "provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["service_host_sha256"] = sha(host.read_bytes())
    provenance["service_runtime_sha256"] = components
    provenance_path.write_text(json.dumps(provenance), encoding="utf-8")
    verify(release, engine_init)
    (release / "python313._pth").write_bytes(b"alternate path")
    with pytest.raises(ValueError, match="Windows service runtime differs"):
        verify(release, engine_init)


def test_missing_scheduler_refuses_launch_instead_of_bypassing_guards(tmp_path):
    platform = tmp_path / "minimal-platform"
    platform.mkdir()
    repo_platform = Path(__file__).resolve().parents[1]
    env = dict(os.environ, DEVCORE_PLATFORM_ROOT=str(platform),
               DEVCORE_LOCAL_ROOT=str(tmp_path / "local"),
               DEVCORE_DATA_ROOT=str(tmp_path / "data"))
    code = ("import sys; sys.path.insert(0, sys.argv[1]); "
            "from devcore_engine.infra import system_watcher as w; "
            "assert w.DEV_CORE_ROOT == __import__('pathlib').Path(sys.argv[2]); "
            "\ntry: w.services_paused(sys.argv[3])\n"
            "except RuntimeError as exc: assert 'Scheduler unavailable' in str(exc)\n"
            "else: raise AssertionError('missing Scheduler allowed service launch')")
    result = subprocess.run([sys.executable, "-I", "-c", code,
                             str(repo_platform), str(platform), str(tmp_path / "local")],
                            env=env, cwd=tmp_path, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
