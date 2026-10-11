"""Launcher preflight refuses incomplete inputs before server imports/listening."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import socket
import time

import pytest

from Scripts import launch_individual_candidate as launcher
from Scripts.build_individual_bundle import build


@pytest.mark.parametrize("pin,port", [("", 20129), ("F" * 64, 20129), ("0" * 64, 0), ("0" * 64, 65536)])
def test_invalid_pin_or_port_rejected_before_paths(tmp_path, pin, port):
    with pytest.raises(ValueError):
        launcher.prepare(tmp_path / "absent", pin, tmp_path, tmp_path, tmp_path / "absent.db", port)
    assert not (tmp_path / "absent").exists()


def test_wrong_trusted_pin_refused_before_state_roots(tmp_path):
    bundle = tmp_path / "bundle"
    build(Path(__file__).resolve().parents[1], bundle)
    with pytest.raises(ValueError, match="trusted pin"):
        launcher.prepare(bundle, "0" * 64, tmp_path / "local", tmp_path / "data", tmp_path / "db", 20129)
    assert not (tmp_path / "local").exists()


@pytest.mark.parametrize("overlap", ["same", "nested", "identity-outside", "code-inside"])
def test_root_conflicts_fail_before_engine_import(tmp_path, monkeypatch, overlap):
    bundle, local, data = tmp_path / "bundle", tmp_path / "local", tmp_path / "data"
    build(Path(__file__).resolve().parents[1], bundle)
    local.mkdir(); data.mkdir()
    identity = local / "identity.db"
    identity.write_bytes(b"sentinel")
    if overlap == "same": data = local
    if overlap == "nested": data = local / "nested"; data.mkdir()
    if overlap == "identity-outside": identity = data / "identity.db"; identity.write_bytes(b"sentinel")
    if overlap == "code-inside": data = bundle
    def never_import(): raise AssertionError("engine import must follow path validation")
    monkeypatch.setattr(launcher, "installed_engine", never_import)
    pin = hashlib.sha256((bundle / "manifest.json").read_bytes()).hexdigest()
    with pytest.raises(ValueError): launcher.prepare(bundle, pin, local, data, identity, 20129)
    assert identity.read_bytes() == b"sentinel"


def test_cli_without_config_refuses_without_creating_stores(tmp_path):
    env = {**os.environ, "DEVCORE_LOCAL_ROOT": str(tmp_path / "local"), "DEVCORE_DATA_ROOT": str(tmp_path / "data")}
    result = subprocess.run([sys.executable, "-I", launcher.__file__, "--check"], env=env, capture_output=True, timeout=15)
    assert result.returncode == 2
    assert not (tmp_path / "local").exists() and not (tmp_path / "data").exists()


@pytest.mark.skipif(os.name != "nt", reason="Real private NTFS store and installed candidate runtime")
def test_isolated_preflight_forces_individual_and_keeps_private_store_unchanged(tmp_path):
    bundle = tmp_path / "bundle"
    build(Path(__file__).resolve().parents[1], bundle)
    local, data = tmp_path / "local", tmp_path / "data"
    local.mkdir(); data.mkdir()
    identity = local / "Security" / "identity.db"
    identity.parent.mkdir()
    env = {**os.environ, "DEVCORE_LOCAL_ROOT": str(local), "DEVCORE_DATA_ROOT": str(data),
           "DEVCORE_DASHBOARD_AUTH_PROFILE": "legacy", "DEVCORE_DASHBOARD_BIND": "0.0.0.0"}
    provision = subprocess.run([sys.executable, "-I", "-c",
        "import sys; from devcore_engine.security.private_store import initialize_private_store; initialize_private_store(sys.argv[1])",
        str(identity)], env=env, capture_output=True, timeout=30)
    assert provision.returncode == 0, "private fixture creation failed"
    before = hashlib.sha256(identity.read_bytes()).hexdigest()
    pin = hashlib.sha256((bundle / "manifest.json").read_bytes()).hexdigest()
    result = subprocess.run([sys.executable, "-I", launcher.__file__, "--check", "--bundle", str(bundle),
        "--manifest-sha256", pin, "--local-root", str(local), "--data-root", str(data),
        "--identity-store", str(identity), "--port", "54321"], env=env, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    report = json.loads(result.stdout)
    assert report["profile"] == "individual" and report["bind"] == "127.0.0.1"
    assert report["operationally_qualified"] is False
    assert "site-packages" in report["engine"]
    assert before == hashlib.sha256(identity.read_bytes()).hexdigest()
    assert not list(data.iterdir())
    assert not (local / "devcore.db").exists()
    from Scripts.build_individual_bundle import verify
    assert verify(bundle)


@pytest.mark.skipif(os.name != "nt", reason="Native private NTFS fixture")
def test_launched_snapshot_authenticates_projects_and_records_actor(tmp_path):
    import httpx
    from contextlib import closing
    from devcore_engine.db import init_db
    from devcore_engine.security.private_store import initialize_private_store
    from devcore_engine.security.identity import add_user, set_membership, issue_credential, READ, WRITE, AUDIT_READ

    bundle, local, data = tmp_path / "bundle", tmp_path / "local", tmp_path / "data"
    build(Path(__file__).resolve().parents[1], bundle)
    local.mkdir(); data.mkdir()
    identity = local / "Security" / "identity.db"
    identity.parent.mkdir()
    initialize_private_store(identity)
    add_user(identity, "alice")
    set_membership(identity, "alice", "alpha", "owner")
    _, secret = issue_credential(identity, "alice", ["alpha"], [READ, WRITE, AUDIT_READ])
    with closing(init_db(local / "devcore.db")) as connection:
        for project in ("alpha", "beta"):
            connection.execute("INSERT INTO projects(id,name,root_path) VALUES (?,?,'.')", (project, project))
            connection.execute("INSERT INTO tasks(id,project_id,title,status) VALUES ('T-01',?,?,'todo')", (project, project))
        connection.commit()
    with closing(socket.socket()) as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    pin = hashlib.sha256((bundle / "manifest.json").read_bytes()).hexdigest()
    env = {**os.environ, "DEVCORE_LOCAL_ROOT": str(local), "DEVCORE_DATA_ROOT": str(data),
           "DEVCORE_DASHBOARD_AUTH_PROFILE": "legacy", "DEVCORE_DASHBOARD_BIND": "0.0.0.0"}
    command = [sys.executable, "-I", launcher.__file__, "--bundle", str(bundle), "--manifest-sha256", pin,
               "--local-root", str(local), "--data-root", str(data), "--identity-store", str(identity), "--port", str(port)]
    with (tmp_path / "server.txt").open("wb") as log:
        process = subprocess.Popen(command, env=env, cwd=tmp_path, stdout=log, stderr=log)
        try:
            with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=5, trust_env=False) as client:
                deadline = time.monotonic() + 20
                while True:
                    try:
                        if client.get("/project").status_code == 200: break
                    except httpx.TransportError:
                        pass
                    assert process.poll() is None, "candidate process exited before readiness"
                    assert time.monotonic() < deadline, "candidate startup exceeded recipe deadline"
                    time.sleep(0.1)
                headers = {"Authorization": "Bearer " + secret}
                assert client.get("/api/settings", headers=headers).status_code == 403
                assert client.get("/api/dashboard/tasks?project=beta", headers=headers).status_code == 403
                response = client.get("/api/dashboard/tasks?project=alpha", headers=headers)
                assert response.status_code == 200 and response.json()[0]["title"] == "alpha"
                from devcore_engine.services.tasks import TaskService
                with closing(__import__("sqlite3").connect(local / "devcore.db")) as conn:
                    conn.row_factory = __import__("sqlite3").Row
                    TaskService(conn).next_task("alpha")
                for route, version in [("pause", 2), ("resume", 3)]:
                    reply = client.post("/api/" + route, headers=headers,
                                        json={"project": "alpha", "id": "T-01", "expected_version": version})
                    assert reply.status_code == 200
                    assert client.post("/api/" + route, headers=headers,
                                       json={"project": "alpha", "id": "T-01", "expected_version": version}).status_code == 409
                response = client.post("/api/done", headers=headers,
                                       json={"project": "alpha", "id": "T-01", "expected_version": 4})
                assert response.status_code == 200
                history = client.get("/api/project/task-audit?project=alpha", headers=headers)
                assert history.status_code == 200
                event = history.json()["events"][0]
                assert [e["action"] for e in history.json()["events"]] == ["task.complete", "task.resume", "task.pause"]
                assert event["actor"] == "alice" and event["after"] == {"status": "done", "version": 5}
        finally:
            process.terminate()
            try: process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait(timeout=5)
    import sqlite3
    with closing(sqlite3.connect(local / "devcore.db")) as connection:
        assert connection.execute("SELECT status,version FROM tasks WHERE project_id='beta'").fetchone() == ("todo", 1)
    assert not list(data.iterdir())
