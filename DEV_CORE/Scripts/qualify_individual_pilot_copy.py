"""Qualify HTTP sessions and two confined runs on a verified SQLite copy.

The input is read-only and the output root must be new. Credentials exist only
in memory and are revoked after the probe. This does not perform a cutover.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import socket
import sqlite3
import statistics
import subprocess
import sys
import time


PROJECTS = ("devcore", "dashboard_recette_br")
USERS = ("pilot_v230_a", "pilot_v230_b")


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def qualify(release: Path, source: Path, expected_sha256: str, root: Path, port: int,
            session_count: int = 5, reads_per_session: int = 1) -> dict:
    release = release.resolve(strict=True)
    source = source.resolve(strict=True)
    root = root.resolve()
    if root.exists() or root.parent != source.parent or not 1 <= port <= 65535:
        raise ValueError("New sibling qualification root and valid port required")
    if not 1 <= session_count <= 20 or not 1 <= reads_per_session <= 20:
        raise ValueError("Session and read counts must be 1..20")
    if digest(source) != expected_sha256:
        raise ValueError("Pilot source differs from the pinned copy")
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", port)) == 0:
            raise ValueError("Pilot port already in use")
    bundle = release / "individual-platform-v2"
    python = release / "Scripts" / "python.exe"
    controls = release / "controls" / "Scripts"
    pin = digest(bundle / "manifest.json")
    local, data = root / "local", root / "data"
    (local / "Security").mkdir(parents=True)
    data.mkdir()
    db = local / "devcore.db"
    identity = local / "Security" / "identity.db"
    with sqlite3.connect(f"{source.as_uri()}?mode=ro", uri=True) as original:
        original.execute("PRAGMA query_only=ON")
        if original.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("Pilot source integrity failed")
        with sqlite3.connect(db) as copy:
            original.backup(copy)

    # Set every root before importing the installed engine or launching children.
    os.environ.update({"DEVCORE_LOCAL_ROOT": str(local), "DEVCORE_DATA_ROOT": str(data),
                       "DEVCORE_PLATFORM_ROOT": str(bundle), "DEVCORE_IDENTITY_STORE": str(identity)})
    from devcore_engine.security.private_store import initialize_private_store
    from devcore_engine.security.browser_sessions import upgrade_session_store
    from devcore_engine.security.identity import (
        READ, add_user, disable_user, issue_credential, revoke_credential, set_membership,
    )
    from devcore_engine.runs.engine import DurableRunEngine
    from devcore_engine.runs.models import RunSubmission
    import httpx

    initialize_private_store(identity)
    upgrade_session_store(identity)
    credentials: list[tuple[str, str]] = []
    clients: list[httpx.Client] = []
    sessions: list[tuple[httpx.Client, str, str, str]] = []
    process: subprocess.Popen | None = None
    try:
        for user, project in zip(USERS, PROJECTS):
            add_user(identity, user)
            set_membership(identity, user, project, "reader")
            credential_id, token = issue_credential(identity, user, [project], [READ], ttl_seconds=600)
            credentials.append((credential_id, token))

        command = [str(python), "-I", str(controls / "launch_individual_candidate.py"),
                   "--bundle", str(bundle), "--manifest-sha256", pin,
                   "--local-root", str(local), "--data-root", str(data),
                   "--identity-store", str(identity), "--port", str(port)]
        with (root / "dashboard.log").open("wb") as log:
            process = subprocess.Popen(command, cwd=root, env=os.environ.copy(),
                                       stdout=log, stderr=log,
                                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            with httpx.Client(base_url=f"http://127.0.0.1:{port}", trust_env=False, timeout=3) as probe:
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        raise RuntimeError(f"Pilot Dashboard exited: {process.returncode}")
                    try:
                        if probe.get("/project").status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    time.sleep(.2)
                else:
                    raise RuntimeError("Pilot Dashboard readiness timeout")

            origin = f"http://127.0.0.1:{port}"
            for index in range(session_count):
                account = index % 2
                project = PROJECTS[account]
                client = httpx.Client(base_url=origin, trust_env=False, timeout=5,
                                      headers={"Origin": origin})
                clients.append(client)
                login = client.post("/api/auth/session", json={"project": project},
                                    headers={"Authorization": "Bearer " + credentials[account][1]})
                if login.status_code != 200:
                    raise RuntimeError(f"Browser session creation failed: {login.status_code}")
                sessions.append((client, project, PROJECTS[1 - account], login.json()["csrf_token"]))

            with sqlite3.connect(f"{identity.as_uri()}?mode=ro", uri=True) as private:
                simultaneous_sessions = private.execute(
                    "SELECT count(*) FROM identity_browser_sessions WHERE revoked=0"
                ).fetchone()[0]
            if simultaneous_sessions != session_count:
                raise RuntimeError("Requested simultaneous sessions were not recorded")

            def read_pair(item: tuple[httpx.Client, str, str, str]) -> dict:
                client, own, other, _ = item
                durations = []
                for _ in range(reads_per_session):
                    start = time.perf_counter()
                    own_reply = client.get("/api/dashboard/tasks", params={"project": own, "limit": 20})
                    durations.append(round((time.perf_counter() - start) * 1000, 2))
                    if own_reply.status_code != 200:
                        break
                other_reply = client.get("/api/dashboard/tasks", params={"project": other})
                return {"project": own, "own": own_reply.status_code,
                        "other": other_reply.status_code, "own_read_ms": durations}

            with ThreadPoolExecutor(max_workers=session_count) as pool:
                reads = list(pool.map(read_pair, sessions))
            if not all(row["own"] == 200 and row["other"] == 403 for row in reads):
                raise RuntimeError(f"Session project isolation failed: {reads}")
            logout = []
            for client, _, _, csrf in sessions:
                response = client.delete("/api/auth/session", headers={"X-CSRF-Token": csrf})
                logout.append((response.status_code, client.get("/api/auth/session").status_code))
            if any(pair != (200, 401) for pair in logout):
                raise RuntimeError(f"Session logout failed: {logout}")
    finally:
        for client in clients:
            client.close()
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        for credential_id, _ in credentials:
            revoke_credential(identity, credential_id)
        for user in USERS:
            disable_user(identity, user)

    engine = DurableRunEngine()
    run_ids = []
    for index, project in enumerate(PROJECTS):
        record, created = engine.submit_run(RunSubmission(
            project_id=project, title=f"L9 pilot contained run {index + 1}",
            command=[str(python), "-I", "-c",
                     f'import time; time.sleep(0.8); print("pilot-run-{index + 1}")'],
            timeout_seconds=10, actor="l9-pilot", idempotency_key=f"l9-v230-{index + 1}",
        ))
        if not created:
            raise RuntimeError("Pilot run was not newly admitted")
        run_ids.append(record.id)
    engine.start_worker(poll_interval=.05)
    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            runs = [engine.get_run(run_id) for run_id in run_ids]
            if all(run is not None and run.is_terminal() for run in runs):
                break
            time.sleep(.1)
        else:
            raise RuntimeError("Pilot runs did not finish within 20 seconds")
    finally:
        engine.stop_worker(timeout=5)
    if not all(run.status == "succeeded" and run.exit_code == 0 for run in runs):
        raise RuntimeError(f"Pilot run failure: {[(run.status, run.error) for run in runs]}")
    overlap = max(run.started_at for run in runs) < min(run.finished_at for run in runs)
    if not overlap:
        raise RuntimeError("Pilot runs did not overlap")
    with sqlite3.connect(db) as copy:
        integrity = copy.execute("PRAGMA integrity_check").fetchone()[0]
        violations = copy.execute("PRAGMA foreign_key_check").fetchall()
    if integrity != "ok" or violations or digest(source) != expected_sha256:
        raise RuntimeError("Pilot source changed or destination integrity failed")
    with sqlite3.connect(f"{identity.as_uri()}?mode=ro", uri=True) as private:
        active_credentials = private.execute(
            "SELECT count(*) FROM identity_credentials WHERE revoked=0"
        ).fetchone()[0]
        active_users = private.execute("SELECT count(*) FROM identity_users WHERE enabled=1").fetchone()[0]
    if active_credentials or active_users:
        raise RuntimeError("Pilot identity cleanup failed")
    report = {"release": str(release), "source_sha256": expected_sha256,
              "root": str(root), "port": port, "simultaneous_sessions": simultaneous_sessions,
              "reads_per_session": reads_per_session,
              "read_count": sum(len(row["own_read_ms"]) for row in reads),
              "read_p95_ms": sorted(value for row in reads for value in row["own_read_ms"])[
                  max(0, (sum(len(row["own_read_ms"]) for row in reads) * 95 + 99) // 100 - 1)],
              "read_median_ms": statistics.median(
                  value for row in reads for value in row["own_read_ms"]),
              "session_reads": reads, "logout": logout,
              "runs": [{"project": run.project_id, "status": run.status,
                        "exit_code": run.exit_code, "output": run.output.strip()}
                       for run in runs], "runs_overlapped": overlap,
              "destination_integrity": integrity, "foreign_key_violations": 0,
              "active_credentials": 0, "active_users": 0,
              "pilot_probe_passed": True, "operationally_qualified": False}
    (root / "qualification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                                              encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--port", type=int, default=20132)
    parser.add_argument("--sessions", type=int, default=5)
    parser.add_argument("--reads-per-session", type=int, default=1)
    args = parser.parse_args()
    print(json.dumps(qualify(args.release, args.source, args.source_sha256,
                             args.root, args.port, args.sessions, args.reads_per_session),
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
