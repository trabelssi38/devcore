"""Explicit loopback Dashboard launcher for a pinned candidate snapshot.

Use Python -I to exclude ambient PYTHONPATH. No migrations, account creation,
service registration or data initialization are performed by the preflight.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True


def checked_path(value: Path, *, directory: bool) -> Path:
    path = Path(value)
    if not path.is_absolute():
        raise ValueError("Absolute paths required")
    for part in [path, *path.parents]:
        if part.is_symlink() or part.is_junction():
            raise ValueError("Linked paths refused")
    if not (path.is_dir() if directory else path.is_file()):
        raise ValueError("Existing directory/file required")
    return path.resolve()


def installed_engine() -> Path:
    spec = importlib.util.find_spec("devcore_engine")
    if spec is None or spec.origin is None:
        raise ValueError("Installed engine required")
    path = checked_path(Path(spec.origin), directory=False)
    if not path.is_relative_to(Path(sys.prefix).resolve()):
        raise ValueError("Engine must be installed in the selected runtime")
    release = Path(sys.prefix)
    verifier_path = Path(__file__).with_name("verify_engine_release.py")
    if (release.parent.name.lower() == "releases" or (release / "artifacts" / "manifest.json").exists()):
        spec = importlib.util.spec_from_file_location("candidate_engine_release_verifier", verifier_path)
        verifier = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(verifier)
        verifier.verify(release, path)
    return path


def verified_bundle(bundle: Path, pin: str) -> Path:
    if not isinstance(pin, str) or not re.fullmatch(r"[0-9a-f]{64}", pin):
        raise ValueError("Explicit SHA-256 manifest pin required")
    bundle = checked_path(bundle, directory=True)
    manifest = checked_path(bundle / "manifest.json", directory=False)
    if manifest.stat().st_size > 2 * 1024 * 1024:
        raise ValueError("Manifest too large")
    if hashlib.sha256(manifest.read_bytes()).hexdigest() != pin:
        raise ValueError("Manifest differs from trusted pin")
    # Import the builder from this trusted launcher directory, not the bundle.
    spec = importlib.util.spec_from_file_location(
        "candidate_bundle_verifier", Path(__file__).with_name("build_individual_bundle.py")
    )
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    verifier.verify(bundle)
    if hashlib.sha256(manifest.read_bytes()).hexdigest() != pin:
        raise ValueError("Manifest changed during verification")
    sys.dont_write_bytecode = True
    return bundle


def prepare(bundle: Path, pin: str, local: Path, data: Path, identity: Path, port: int) -> dict:
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("Port must be 1..65535")
    bundle = verified_bundle(bundle, pin)
    local, data = checked_path(local, directory=True), checked_path(data, directory=True)
    identity = checked_path(identity, directory=False)
    if local == data or local.is_relative_to(data) or data.is_relative_to(local):
        raise ValueError("Separate transaction and document roots required")
    for root in (local, data):
        if root.is_relative_to(bundle) or bundle.is_relative_to(root):
            raise ValueError("Code snapshot must be separate from data roots")
    if not identity.is_relative_to(local):
        raise ValueError("Identity store must be inside the local root")
    engine = installed_engine()
    # Set roots and force the qualified profile before importing engine services.
    os.environ.update({
        "DEVCORE_PLATFORM_ROOT": str(bundle), "DEVCORE_LOCAL_ROOT": str(local),
        "DEVCORE_DATA_ROOT": str(data), "DEVCORE_IDENTITY_STORE": str(identity),
        "DEVCORE_DASHBOARD_AUTH_PROFILE": "individual", "DEVCORE_DASHBOARD_BIND": "127.0.0.1",
        "DEVCORE_ALLOW_PUBLIC_BIND": "0", "DEVCORE_CORS_ALLOWED_ORIGINS": f"http://127.0.0.1:{port}",
    })
    from devcore_engine.security.private_store import check_store_protection
    check_store_protection(identity)  # Descriptor inspection only, no SQLite open.
    import sqlite3
    probe_spec = importlib.util.spec_from_file_location("candidate_sqlite_probe", bundle / "Scripts/check_sqlite_runtime.py")
    probe = importlib.util.module_from_spec(probe_spec)
    probe_spec.loader.exec_module(probe)
    if not probe.inspect_runtime()["eligible_for_wal_qualification"]:
        raise ValueError("Corrected SQLite required")
    return {"profile": "individual", "bind": "127.0.0.1", "port": port,
            "manifest_sha256": pin, "engine": str(engine), "sqlite": sqlite3.sqlite_version,
            "operationally_qualified": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--local-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--identity-store", type=Path, required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--check", action="store_true", help="Preflight only; no listener")
    parser.add_argument("--managed", action="store_true", help="Register cooperative dashboard shutdown on port 20129")
    args = parser.parse_args()
    try:
        if args.managed and args.port != 20129:
            raise ValueError("Managed dashboard requires port 20129")
        report = prepare(args.bundle, args.manifest_sha256, args.local_root, args.data_root, args.identity_store, args.port)
    except Exception:
        print(json.dumps({"success": False, "code": "candidate_preflight_refused"}), file=sys.stderr)
        return 2
    if args.check:
        print(json.dumps(report, separators=(",", ":")))
        return 0
    spec = importlib.util.spec_from_file_location("candidate_dashboard", args.bundle / "Scripts/dashboard_api.py")
    dashboard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dashboard)
    if args.managed:
        runtime_spec = importlib.util.spec_from_file_location(
            "candidate_service_runtime", Path(__file__).with_name("service_runtime.py"))
        runtime = importlib.util.module_from_spec(runtime_spec)
        runtime_spec.loader.exec_module(runtime)
        runtime.run_managed(dashboard.app, host="127.0.0.1", port=args.port, service="dashboard",
                            log_level="warning", proxy_headers=False)
    else:
        import uvicorn
        uvicorn.run(dashboard.app, host="127.0.0.1", port=args.port, log_level="warning", proxy_headers=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
