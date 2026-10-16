"""Exercise the v253 managed HTTPS path on an isolated virtual interface."""
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time


RELEASE = Path("E:/DevCoreRuntime/qualification/service-profile-v250-postgres/runtime/releases/devcore-py31316-20261015-postgres-v253-lan")
TEST_ADDRESS = "172.26.0.1"


def main(release: Path = RELEASE, test_address: str = TEST_ADDRESS) -> dict:
    with closing(socket.socket()) as probe:
        probe.bind((test_address, 0))
    root = Path(tempfile.mkdtemp(prefix="devcore-v253-lan-managed-"))
    local, data = root / "local", root / "data"
    (local / "Security").mkdir(parents=True)
    data.mkdir()
    os.environ["DEVCORE_LOCAL_ROOT"] = str(local)
    os.environ["DEVCORE_DATA_ROOT"] = str(data)
    for name in ("DEVCORE_DATABASE_URL", "DEVCORE_TASK_READ_MODE", "DEVCORE_IDENTITY_READ_MODE"):
        os.environ.pop(name, None)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from devcore_engine.db import init_db
    from devcore_engine.security.identity import add_user, set_membership
    from devcore_engine.security.browser_sessions import upgrade_session_store
    from devcore_engine.security.passwords import set_password, upgrade_password_store
    from devcore_engine.security.private_store import initialize_private_store
    from prepare_lan_tls_certificate import create
    from verify_v253_second_host import client as public_client, request as public_request

    identity = local / "Security/identity.db"
    initialize_private_store(identity)
    add_user(identity, "alice")
    set_membership(identity, "alice", "alpha", "owner")
    upgrade_session_store(identity)
    upgrade_password_store(identity)
    password = secrets.token_urlsafe(24)
    set_password(identity, "alice", password)
    with closing(init_db(local / "devcore.db")) as connection:
        connection.execute("INSERT INTO projects(id,name,root_path) VALUES ('alpha','alpha','.')")
        connection.execute("INSERT INTO tasks(id,project_id,title,status) VALUES ('T-01','alpha','TLS fixture','todo')")
        connection.commit()
    certificate = create(local, test_address)
    bundle = release / "individual-platform-v2"
    pin = hashlib.sha256((bundle / "manifest.json").read_bytes()).hexdigest()
    command = [str(release / "Scripts/python.exe"), "-I",
               str(release / "controls/Scripts/launch_individual_candidate.py"),
               "--bundle", str(bundle), "--manifest-sha256", pin,
               "--local-root", str(local), "--data-root", str(data),
               "--identity-store", str(identity), "--port", "20129", "--managed",
               "--lan-bind", test_address, "--tls-certfile", certificate["certificate"],
               "--tls-keyfile", certificate["key"]]
    log_path = root / "server.log"
    result = {"root": str(root), "address": test_address, "service_unchanged": True}
    with log_path.open("wb") as log:
        process = subprocess.Popen(command, cwd=release, env=os.environ.copy(),
                                   stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            import httpx
            origin = f"https://{test_address}:20129"
            with httpx.Client(base_url=origin, verify=certificate["certificate"],
                              trust_env=False, timeout=2) as client:
                deadline = time.monotonic() + 30
                while True:
                    try:
                        if client.get("/project").status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    if process.poll() is not None or time.monotonic() > deadline:
                        raise RuntimeError("Managed TLS candidate failed readiness")
                    time.sleep(.2)
                result["project_http"] = 200
                pinned_client = public_client(Path(certificate["certificate"]))
                if (public_request(pinned_client, origin, "/project")[0] != 200
                        or public_request(pinned_client, origin, "/api/auth/session")[0] != 401):
                    raise RuntimeError("Portable second-host TLS client failed")
                result["portable_client_tls"] = True
                result["anonymous_session_http"] = client.get("/api/auth/session").status_code
                hostile = client.post("/api/auth/session", headers={"Origin": "https://invalid.example"},
                                      json={"user_id": "alice", "password": password, "project": "alpha"})
                result["hostile_origin_http"] = hostile.status_code
                login = client.post("/api/auth/session", headers={"Origin": origin},
                                    json={"user_id": "alice", "password": password, "project": "alpha"})
                result["login_http"] = login.status_code
                result["cookie_secure"] = "Secure" in login.headers.get("set-cookie", "")
                result["task_read_http"] = client.get("/api/dashboard/tasks?project=alpha").status_code
                csrf = login.json().get("csrf_token") if login.status_code == 200 else None
                logout = client.delete("/api/auth/session", headers={"Origin": origin, "X-CSRF-Token": csrf or ""})
                result["logout_http"] = logout.status_code
                result["revoked_session_http"] = client.get("/api/auth/session").status_code
                if (result["anonymous_session_http"], result["hostile_origin_http"], result["login_http"],
                    result["cookie_secure"], result["task_read_http"], result["logout_http"],
                    result["revoked_session_http"]) != (401, 403, 200, True, 200, 200, 401):
                    raise RuntimeError("Managed TLS browser contract failed")
            stop = subprocess.run([str(release / "Scripts/python.exe"), "-I",
                                   str(release / "controls/Scripts/stop_service.py"),
                                   "--local-root", str(local), "--data-root", str(data),
                                   "--platform-root", str(bundle), "--service", "dashboard",
                                   "--wait-seconds", "30"], cwd=release, env=os.environ.copy(),
                                  capture_output=True, timeout=35)
            process.wait(timeout=10)
            result["graceful_stop"] = stop.returncode == 0 and process.returncode == 0
            if not result["graceful_stop"]:
                raise RuntimeError("Managed TLS candidate did not stop cleanly")
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, default=RELEASE)
    parser.add_argument("--test-address", default=TEST_ADDRESS)
    args = parser.parse_args()
    print(json.dumps(main(args.release.resolve(strict=True), args.test_address), separators=(",", ":")))
