"""Prepare portable roots and optionally register the Windows Dashboard service."""
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
from pathlib import Path
import socket
import sys


def prepare(release: Path, local_relative: str, data_relative: str,
            windows_startup: str = "automatic") -> dict:
    from devcore_engine.windows_service import _relative

    release = release.resolve(strict=True)
    if release.parent.name.lower() != "releases":
        raise ValueError("Versioned release directory required")
    base = release.parent.parent
    local = _relative(base, local_relative)
    data = _relative(base, data_relative)
    if local == data or local.is_relative_to(data) or data.is_relative_to(local):
        raise ValueError("Separate local and data roots required")
    if windows_startup not in ("automatic", "manual"):
        raise ValueError("Windows startup must be automatic or manual")
    bundle = release / "individual-platform-v2" / "manifest.json"
    pin = hashlib.sha256(bundle.read_bytes()).hexdigest()
    config = {"schema_version": 2, "local_relative": local_relative,
              "data_relative": data_relative, "bundle_manifest_sha256": pin,
              "windows_startup": windows_startup}
    target = release / "individual-service.json"
    if target.is_symlink() or target.is_junction():
        raise ValueError("Linked service configuration refused")
    if target.exists():
        existing = json.loads(target.read_text(encoding="utf-8"))
        legacy = {key: value for key, value in config.items() if key != "windows_startup"}
        legacy["schema_version"] = 1
        if existing != config and not (windows_startup == "automatic" and existing == legacy):
            raise ValueError("Existing service configuration differs")
    local.mkdir(parents=True, exist_ok=True)
    data.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return {"release": str(release), "local_root": str(local), "data_root": str(data),
            "identity_ready": (local / "Security" / "identity.db").is_file(),
            "configured": True, "service_installed": False,
            "windows_startup": windows_startup}


def install(release: Path, account: str, start: bool) -> dict:
    import win32service
    import win32serviceutil
    from devcore_engine.windows_service import DevCoreIndividualService, load_profile, SERVICE_NAME

    release = release.resolve(strict=True)
    profile = load_profile(release)
    python = profile["python"]
    verifier = profile["controls"] / "verify_engine_release.py"
    import subprocess
    result = subprocess.run([str(python), "-I", str(verifier), "--release", str(release)],
                            capture_output=True, timeout=30)
    if result.returncode:
        raise ValueError("Release attestation failed")
    if not isinstance(account, str) or not account or "\x00" in account:
        raise ValueError("Windows service account required")
    if start:
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1", 20129)) == 0:
                raise ValueError("Dashboard port 20129 is already in use")
    exe = release / "pythonservice.exe"
    if not exe.is_file():
        exe = Path(win32serviceutil.LocatePythonServiceExe())
    password = getpass.getpass(f"Mot de passe local pour {account} (non affiché) : ")
    service_args = dict(
        startType=(win32service.SERVICE_AUTO_START if profile["windows_startup"] == "automatic"
                   else win32service.SERVICE_DEMAND_START),
        userName=account, password=password, exeName=str(exe),
        description=DevCoreIndividualService._svc_description_,
    )
    try:
        try:
            win32serviceutil.InstallService(
                "devcore_engine.windows_service.DevCoreIndividualService",
                SERVICE_NAME, DevCoreIndividualService._svc_display_name_, **service_args)
        except Exception as exc:
            # CreateService returns ERROR_SERVICE_EXISTS when a previous
            # DevCoreIndividual registration is stopped but still present.
            # Update that registration in place so its account, startup mode,
            # command line and description move together atomically.
            if getattr(exc, "winerror", None) != 1073:
                raise
            win32serviceutil.ChangeServiceConfig(
                "devcore_engine.windows_service.DevCoreIndividualService",
                SERVICE_NAME,
                displayName=DevCoreIndividualService._svc_display_name_,
                **service_args)
    finally:
        password = None
    if start:
        win32serviceutil.StartService(SERVICE_NAME)
    return {"service": SERVICE_NAME, "account": account,
            "installed": True, "start_requested": start,
            "windows_startup": profile["windows_startup"],
            "local_root": str(profile["local"]), "data_root": str(profile["data"])}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    setup = sub.add_parser("prepare")
    setup.add_argument("--local-relative", default="state/local")
    setup.add_argument("--data-relative", default="state/data")
    setup.add_argument("--windows-startup", choices=("automatic", "manual"), default="automatic",
                       help="Windows Service Control Manager startup mode; independent of install --start")
    register = sub.add_parser("install")
    register.add_argument("--account", default=".\\" + getpass.getuser())
    register.add_argument("--start", action="store_true")
    args = parser.parse_args()
    try:
        report = (prepare(args.release, args.local_relative, args.data_relative,
                          args.windows_startup)
                  if args.command == "prepare" else install(args.release, args.account, args.start))
    except Exception as exc:
        print(json.dumps({"success": False, "error": str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps(report, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
