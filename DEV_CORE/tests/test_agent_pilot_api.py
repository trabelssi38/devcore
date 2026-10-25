"""Authenticated agent pilot routes on disposable Git and identity stores."""

import json
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

from fastapi.testclient import TestClient


def test_devcore_agent_routes_bind_identity_project_and_patch(tmp_path, monkeypatch):
    local = tmp_path / "local"
    data = tmp_path / "data"
    local.mkdir()
    data.mkdir()
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(local))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(data))
    monkeypatch.setenv("DEVCORE_REQUIRE_AUTH", "1")
    monkeypatch.setenv("DEVCORE_AGENT_PILOT_ENABLED", "1")

    api_root = Path(__file__).resolve().parents[1] / "API"
    monkeypatch.syspath_prepend(str(api_root))

    from Scripts import devcore_agent_pilot as pilot
    from devcore_api import create_app
    from devcore_api.ports import SqliteTaskRepository
    from devcore_engine.db import init_db
    from devcore_engine.runs.models import RunRecord
    from devcore_engine.security.identity import (
        READ, WRITE, add_user, initialize_store, issue_credential, set_membership,
    )
    from devcore_engine.security.browser_sessions import (
        create_session, csrf_for_session, upgrade_session_store,
    )

    repo = tmp_path / "pilot"
    (repo / "DEV_CORE").mkdir(parents=True)
    (repo / "README.md").write_text("DevCore pilot\n")
    target = repo / "DEV_CORE" / "example.txt"
    target.write_text("before\n")
    for cmd in (["git", "init", "-q"], ["git", "config", "core.autocrlf", "false"],
                ["git", "config", "user.name", "Pilot Test"],
                ["git", "config", "user.email", "pilot@example.invalid"],
                ["git", "add", "README.md", "DEV_CORE/example.txt"],
                ["git", "-c", "core.hooksPath=NUL", "commit", "-qm", "fixture"]):
        subprocess.run(cmd, cwd=repo, capture_output=True, check=True)
    monkeypatch.setattr(pilot, "PILOT_REPO", repo)

    identity = local / "Security" / "identity.db"
    identity.parent.mkdir()
    initialize_store(identity)
    upgrade_session_store(identity)
    add_user(identity, "majdi")
    set_membership(identity, "majdi", "devcore", "owner")
    _, writer_token = issue_credential(identity, "majdi", ["devcore"], [READ, WRITE])
    _, browser_secret = create_session(identity, f"Bearer {writer_token}", "devcore",
                                       "http://127.0.0.1:20131")
    browser_cookie = {"devcore_session": browser_secret}
    add_user(identity, "reader")
    set_membership(identity, "reader", "devcore", "reader")
    _, reader_token = issue_credential(identity, "reader", ["devcore"], [READ])
    monkeypatch.setenv("DEVCORE_IDENTITY_STORE", str(identity))
    db = local / "devcore.db"
    init_db(db).close()

    class RunEngine:
        submission = None
        woke = False

        def submit_run(self, submission):
            self.submission = submission
            return RunRecord(id="pilot-test-run", project_id="devcore",
                             title=submission.title, status="queued",
                             command=submission.command), True

        def wake_worker(self):
            self.woke = True

    engine = RunEngine()
    app = create_app(task_repository=SqliteTaskRepository(db_path=db),
                     require_auth=True, run_engine=engine, start_run_worker=False)
    client = TestClient(app, base_url="http://127.0.0.1:20131")
    writer = {"Authorization": f"Bearer {writer_token}", "Idempotency-Key": "pilot-api-test-1"}
    reader = {"Authorization": f"Bearer {reader_token}", "Idempotency-Key": "pilot-api-test-2"}
    body = {"project": "devcore", "file": "DEV_CORE/example.txt", "task": "Change fixture"}

    assert client.post("/api/v1/agent/proposals", json=body).status_code == 401
    assert client.post("/api/v1/agent/proposals", json=body, headers=reader).status_code == 403
    submitted = client.post("/api/v1/agent/proposals", json=body, headers=writer)
    assert submitted.status_code == 202
    assert submitted.json()["run_id"] == "pilot-test-run"
    assert engine.woke is True
    assert engine.submission.actor == "majdi"
    assert engine.submission.project_id == "devcore"
    assert engine.submission.command[-3:] == ["--file", "DEV_CORE/example.txt", "Change fixture"]
    assert target.read_text() == "before\n"
    assert client.get("/agent/pilot", params={"project": "devcore"}).status_code == 401
    page = client.get("/agent/pilot", params={"project": "devcore"}, headers=writer)
    assert page.status_code == 200
    assert 'id="request-form"' in page.text and 'id="approve"' in page.text

    proposal_id = uuid4().hex
    patch = pilot._proposal_patch(repo, {"summary": "Change fixture",
                                          "path": "DEV_CORE/example.txt",
                                          "old": "before\n", "new": "after\n"},
                                  "DEV_CORE/example.txt")
    payload = {"project": "devcore", "base": pilot._git(repo, "rev-parse", "HEAD"),
               "task": "Change fixture", "summary": "Change fixture", "patch": patch}
    digest = pilot._digest(payload)
    state = local / "AgentPilot"
    state.mkdir()
    (state / f"{proposal_id}.json").write_text(json.dumps({**payload, "id": proposal_id,
        "sha256": digest, "paths": ["DEV_CORE/example.txt"], "status": "waiting_approval"}))

    listing = client.get("/api/v1/agent/proposals", params={"project": "devcore"},
                         headers=writer)
    assert listing.status_code == 200
    assert listing.json()["proposals"][0]["id"] == proposal_id
    path = f"/api/v1/agent/proposals/{proposal_id}"
    assert client.get(path, params={"project": "devcore"}).status_code == 401
    viewed = client.get(path, params={"project": "devcore"}, headers=writer)
    assert viewed.status_code == 200
    assert viewed.json()["sha256"] == digest
    assert client.post(path + "/approve", json={"project": "devcore", "sha256": digest},
                       headers=reader).status_code == 403
    assert target.read_text() == "before\n"
    assert client.post(path + "/approve", json={"project": "devcore", "sha256": digest},
                       cookies=browser_cookie).status_code == 403
    assert client.post(path + "/approve", json={"project": "devcore", "sha256": digest},
                       headers={"Origin": "http://127.0.0.1:20131"},
                       cookies=browser_cookie).status_code == 403
    approved = client.post(path + "/approve", json={"project": "devcore", "sha256": digest},
                           headers={"Origin": "http://127.0.0.1:20131",
                                    "X-CSRF-Token": csrf_for_session(browser_secret)},
                           cookies=browser_cookie)
    assert approved.status_code == 200
    assert approved.json()["approved_by"] == "majdi"
    assert target.read_text() == "after\n"
    assert pilot.read_proposal(state, proposal_id)["approval_source"] == "authenticated_project_api"
    assert subprocess.run(["git", "diff", "--cached", "--check"], cwd=repo,
                          capture_output=True).returncode == 0
