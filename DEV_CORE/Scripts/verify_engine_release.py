"""Verify a candidate engine wheel, provenance, and installed package together."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys


SHA256 = re.compile(r"[0-9a-f]{64}\Z")
ENGINE_SUFFIXES = {".py", ".sql", ".ps1"}
CONTROL_FILES = {
    "Scripts/build_candidate_controls.py", "Scripts/build_individual_bundle.py",
    "Scripts/verify_engine_release.py", "Scripts/launch_individual_candidate.py",
    "Scripts/launch_individual_mcp_candidate.py", "Scripts/service_runtime.py",
    "Scripts/stop_service.py", "Scheduler/scheduler_lock.py",
    "Scripts/qualify_individual_managed.py",
    "Scripts/install_individual_service.py",
    "Scheduler/scheduler_storage.py", "Scheduler/windows_process_identity.py",
}
SERVICE_RUNTIME_FILES = {
    "python313.dll", "python3.dll", "pywintypes313.dll", "python313._pth",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _record(path: Path) -> dict:
    if path.is_symlink() or path.is_junction() or not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
        raise ValueError(f"Missing, linked or oversized release record: {path.name}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Invalid release record: {path.name}")
    return value


def verify(release: Path, engine_init: Path) -> dict:
    release = Path(release).resolve(strict=True)
    engine_init = Path(engine_init).resolve(strict=True)
    package = engine_init.parent
    if (engine_init.name != "__init__.py" or package.name != "devcore_engine"
            or package.parent != release / "Lib" / "site-packages"):
        raise ValueError("Engine is not installed in the selected release")

    provenance = _record(release / "provenance.json")
    manifest_path = release / "artifacts" / "manifest.json"
    manifest = _record(manifest_path)
    manifest_pin = provenance.get("engine_artifact_manifest_sha256")
    if not isinstance(manifest_pin, str) or not SHA256.fullmatch(manifest_pin) or digest(manifest_path) != manifest_pin:
        raise ValueError("Engine artifact manifest differs from release provenance")
    packages_pin = provenance.get("installed_packages_sha256")
    packages_path = release / "installed-packages.txt"
    if (not isinstance(packages_pin, str) or not SHA256.fullmatch(packages_pin)
            or not packages_path.is_file() or digest(packages_path) != packages_pin):
        raise ValueError("Installed package inventory differs from release provenance")
    service_host_pin = provenance.get("service_host_sha256")
    if service_host_pin is not None:
        service_host = release / "pythonservice.exe"
        if (not isinstance(service_host_pin, str) or not SHA256.fullmatch(service_host_pin)
                or service_host.is_symlink() or service_host.is_junction()
                or not service_host.is_file() or digest(service_host) != service_host_pin):
            raise ValueError("Windows service host differs from release provenance")
        runtime_pins = provenance.get("service_runtime_sha256")
        if not isinstance(runtime_pins, dict) or set(runtime_pins) != SERVICE_RUNTIME_FILES:
            raise ValueError("Windows service runtime inventory differs from release provenance")
        for name, pin in runtime_pins.items():
            component = release / name
            if (not isinstance(pin, str) or not SHA256.fullmatch(pin)
                    or component.is_symlink() or component.is_junction()
                    or not component.is_file() or digest(component) != pin):
                raise ValueError(f"Windows service runtime differs: {name}")
    elif "service_runtime_sha256" in provenance:
        raise ValueError("Windows service runtime requires a pinned host")
    controls_pin = provenance.get("controls_manifest_sha256")
    if controls_pin is not None:
        controls_root = release / "controls"
        controls_manifest = controls_root / "manifest.json"
        if (not isinstance(controls_pin, str) or not SHA256.fullmatch(controls_pin)
                or not controls_manifest.is_file() or digest(controls_manifest) != controls_pin):
            raise ValueError("Candidate controls differ from release provenance")
        controls_record = _record(controls_manifest)
        records = controls_record.get("files")
        if (controls_record.get("schema_version") != 1
                or controls_record.get("profile") != "individual-candidate-controls"
                or not isinstance(records, dict) or set(records) != CONTROL_FILES):
            raise ValueError("Candidate control inventory differs")
        actual_controls = {path.relative_to(controls_root).as_posix()
                           for path in controls_root.rglob("*")
                           if path.is_file() and "__pycache__" not in path.relative_to(controls_root).parts}
        if actual_controls != CONTROL_FILES | {"manifest.json"}:
            raise ValueError("Unexpected candidate control file")
        for name, pin in records.items():
            control = controls_root / name
            if (not isinstance(pin, str) or not SHA256.fullmatch(pin)
                    or control.is_symlink() or control.is_junction()
                    or digest(control) != pin):
                raise ValueError(f"Candidate control differs: {name}")

    wheels = manifest.get("wheel_sha256")
    if not isinstance(wheels, dict) or len(wheels) != 1:
        raise ValueError("Release must declare exactly one engine wheel")
    wheel_name, wheel_pin = next(iter(wheels.items()))
    if (not isinstance(wheel_name, str) or not re.fullmatch(r"devcore_engine-[A-Za-z0-9_.-]+\.whl", wheel_name)
            or not isinstance(wheel_pin, str) or not SHA256.fullmatch(wheel_pin)):
        raise ValueError("Invalid engine wheel record")
    wheel = release / "artifacts" / "wheels" / wheel_name
    if wheel.is_symlink() or wheel.is_junction() or not wheel.is_file() or digest(wheel) != wheel_pin:
        raise ValueError("Engine wheel differs from artifact manifest")

    sources = manifest.get("source_files_sha256")
    if not isinstance(sources, dict):
        raise ValueError("Engine source hashes absent")
    expected = {name: pin for name, pin in sources.items()
                if isinstance(name, str) and name.startswith("devcore_engine/")}
    if not expected or "devcore_engine/__init__.py" not in expected:
        raise ValueError("Engine source inventory incomplete")
    installed = package.parent
    actual = set()
    for path in package.rglob("*"):
        if not path.is_file() or path.suffix not in ENGINE_SUFFIXES:
            continue
        if path.is_symlink() or path.is_junction():
            raise ValueError("Linked installed engine file")
        actual.add(path.relative_to(installed).as_posix())
    if actual != set(expected):
        raise ValueError("Installed engine inventory differs from artifact manifest")
    for name, pin in expected.items():
        if not isinstance(pin, str) or not SHA256.fullmatch(pin) or digest(installed / name) != pin:
            raise ValueError(f"Installed engine differs from artifact manifest: {name}")
    return {"release": str(release), "engine": str(engine_init),
            "artifact_manifest_sha256": manifest_pin, "wheel_sha256": wheel_pin,
            "installed_engine_files": len(expected), "controls_manifest_sha256": controls_pin}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, default=Path(sys.prefix))
    parser.add_argument("--engine-init", type=Path)
    args = parser.parse_args()
    spec = importlib.util.find_spec("devcore_engine") if args.engine_init is None else None
    engine_init = args.engine_init or (Path(spec.origin) if spec and spec.origin else None)
    if engine_init is None:
        raise SystemExit("Engine installation unavailable")
    print(json.dumps(verify(args.release, engine_init), separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
