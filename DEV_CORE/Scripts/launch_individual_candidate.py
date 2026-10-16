"""Explicit loopback Dashboard launcher for a pinned candidate snapshot.

Use Python -I to exclude ambient PYTHONPATH. No migrations, account creation,
service registration or data initialization are performed by the preflight.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import ipaddress
import json
import os
from pathlib import Path
import re
import ssl
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


def lan_tls_settings(bind: str | None, certfile: Path | None, keyfile: Path | None, port: int) -> dict:
    """Require an exact interface and a usable TLS pair before a LAN listener."""
    if not bind and certfile is None and keyfile is None:
        return {"host": "127.0.0.1", "origin": f"http://127.0.0.1:{port}"}
    if not bind or certfile is None or keyfile is None:
        raise ValueError("LAN bind requires an address and both TLS files")
    try:
        address = ipaddress.ip_address(bind)
    except ValueError as exc:
        raise ValueError("LAN bind must be an exact IPv4 address") from exc
    private_lan = tuple(ipaddress.ip_network(block) for block in
                        ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"))
    if address.version != 4 or not any(address in block for block in private_lan):
        raise ValueError("LAN bind must be an exact private IPv4 address")
    cert, key = checked_path(certfile, directory=False), checked_path(keyfile, directory=False)
    if cert.stat().st_size > 65536 or key.stat().st_size > 65536:
        raise ValueError("TLS files are unexpectedly large")
    from cryptography import x509
    certificate = x509.load_pem_x509_certificate(cert.read_bytes())
    names = certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    if address not in names.get_values_for_type(x509.IPAddress):
        raise ValueError("TLS certificate SAN does not cover the LAN address")
    now = datetime.now(timezone.utc)
    if not certificate.not_valid_before_utc <= now < certificate.not_valid_after_utc:
        raise ValueError("TLS certificate is not currently valid")
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(str(cert), str(key))
    return {"host": str(address), "origin": f"https://{address}:{port}",
            "ssl_certfile": str(cert), "ssl_keyfile": str(key)}


def prepare(bundle: Path, pin: str, local: Path, data: Path, identity: Path, port: int,
            *, lan_bind: str | None = None, tls_certfile: Path | None = None,
            tls_keyfile: Path | None = None) -> dict:
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("Port must be 1..65535")
    network = lan_tls_settings(lan_bind, tls_certfile, tls_keyfile, port)
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
        "DEVCORE_DASHBOARD_AUTH_PROFILE": "individual", "DEVCORE_DASHBOARD_BIND": network["host"],
        "DEVCORE_ALLOW_PUBLIC_BIND": "0", "DEVCORE_CORS_ALLOWED_ORIGINS": network["origin"],
    })
    from devcore_engine.security.private_store import check_store_protection
    check_store_protection(identity)  # Descriptor inspection only, no SQLite open.
    import sqlite3
    probe_spec = importlib.util.spec_from_file_location("candidate_sqlite_probe", bundle / "Scripts/check_sqlite_runtime.py")
    probe = importlib.util.module_from_spec(probe_spec)
    probe_spec.loader.exec_module(probe)
    if not probe.inspect_runtime()["eligible_for_wal_qualification"]:
        raise ValueError("Corrected SQLite required")
    return {"profile": "individual", "bind": network["host"], "port": port,
            "origin": network["origin"], "tls": "ssl_certfile" in network,
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
    parser.add_argument("--lan-bind", help="Exact private IPv4 address; requires TLS files")
    parser.add_argument("--tls-certfile", type=Path)
    parser.add_argument("--tls-keyfile", type=Path)
    args = parser.parse_args()
    try:
        if args.managed and args.port != 20129:
            raise ValueError("Managed dashboard requires port 20129")
        network = lan_tls_settings(args.lan_bind, args.tls_certfile, args.tls_keyfile, args.port)
        report = prepare(args.bundle, args.manifest_sha256, args.local_root, args.data_root, args.identity_store,
                         args.port, lan_bind=args.lan_bind, tls_certfile=args.tls_certfile, tls_keyfile=args.tls_keyfile)
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
        tls = {key: network[key] for key in ("ssl_certfile", "ssl_keyfile") if key in network}
        runtime.run_managed(dashboard.app, host=network["host"], port=args.port, service="dashboard",
                            log_level="warning", proxy_headers=False, **tls)
    else:
        import uvicorn
        tls = {key: network[key] for key in ("ssl_certfile", "ssl_keyfile") if key in network}
        uvicorn.run(dashboard.app, host=network["host"], port=args.port,
                    log_level="warning", proxy_headers=False, **tls)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
