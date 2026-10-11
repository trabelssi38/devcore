"""Comprehensive qualification test suite for Lot L5:
Durable, concurrent, and interruptible execution engine.

Strictly follows:
- Temporary isolated roots (DEVCORE_LOCAL_ROOT, DEVCORE_DATA_ROOT).
- Zero production data, Dropbox, or live index fixtures.
- Pure Python 3.13 verification on Windows.
- Windows Job Object process tree containment and timeout handling.
- Multi-tenant fair scheduling and backpressure.
- External effects deduplication and fencing tokens.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from fastapi.testclient import TestClient
import pytest

DEVCORE_DIR = Path(__file__).resolve().parents[1]
if str(DEVCORE_DIR / "API") not in sys.path:
    sys.path.insert(0, str(DEVCORE_DIR / "API"))
if str(DEVCORE_DIR) not in sys.path:
    sys.path.insert(0, str(DEVCORE_DIR))

from devcore_api import create_app
from devcore_api.run_state import RunStateMachine
from devcore_engine.runs import (
    DurableRunEngine,
    EffectAlreadyInProgressError,
    EffectIdempotencyStore,
    FairRunScheduler,
    ProcessRunExecutor,
    RunBackpressureError,
    RunFencingError,
    RunNotFoundError,
    RunQuotaConfig,
    RunRecord,
    RunSubmission,
    RunTransitionError,
    SqliteRunStore,
)
from devcore_engine.runners.hermes_runner import HermesRunner
from devcore_engine.security.identity import (
    READ,
    WRITE,
    add_user,
    initialize_store,
    issue_credential,
    set_membership,
)


def win_pid_exited(pid: int) -> bool:
    """Check if a Windows PID has terminated."""
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return False
        except OSError:
            return True
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    api.OpenProcess.restype = wintypes.HANDLE
    api.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    api.WaitForSingleObject.restype = wintypes.DWORD
    api.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = api.OpenProcess(0x100000, False, pid)  # SYNCHRONIZE
    if not handle:
        return ctypes.get_last_error() == 87  # PID no longer exists
    try:
        return api.WaitForSingleObject(handle, 3000) == 0
    finally:
        api.CloseHandle(handle)


@pytest.fixture
def run_env(tmp_path, monkeypatch):
    """Setup an isolated environment for runs."""
    local_root = tmp_path / "local"
    data_root = tmp_path / "data"
    local_root.mkdir(parents=True)
    data_root.mkdir(parents=True)

    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(local_root))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(data_root))

    identity_dir = local_root / "security"
    identity_dir.mkdir(parents=True)
    ident_store = identity_dir / "identity.db"
    initialize_store(ident_store)
    monkeypatch.setenv("DEVCORE_IDENTITY_STORE", str(ident_store))

    runs_db = local_root / "runs" / "runs.db"
    store = SqliteRunStore(db_path=runs_db)
    quota = RunQuotaConfig(
        global_max_running=2,
        project_max_running=1,
        max_queued_per_project=5,
        heartbeat_interval_seconds=0.5,
        heartbeat_timeout_seconds=2.0,
        output_limit_bytes=4096,
    )
    engine = DurableRunEngine(
        store=store,
        quota_config=quota,
        local_root=local_root,
    )

    return {
        "local_root": local_root,
        "data_root": data_root,
        "ident_store": ident_store,
        "store": store,
        "engine": engine,
        "quota": quota,
    }


def test_dbos_absence_and_native_engine_qualification():
    """Verify DBOS is not in runtime and native durable engine replaces it."""
    # Check dbos module is not present in runtime environment
    with pytest.raises(ModuleNotFoundError):
        import dbos  # noqa: F401

    # Native DurableRunEngine provides ACID runs on SQLite/PostgreSQL
    assert DurableRunEngine is not None
    assert SqliteRunStore is not None


def test_full_8_state_machine_transitions_and_rejections():
    """Verify the 8-state machine transitions: queued, running, waiting_approval, paused, succeeded, failed, timed_out, cancelled."""
    sm = RunStateMachine()

    # Normal success path
    assert sm.transition("queued", "start") == "running"
    assert sm.transition("running", "succeed") == "succeeded"

    # Failure path
    assert sm.transition("running", "fail") == "failed"

    # Timeout path
    assert sm.transition("running", "timeout") == "timed_out"

    # Cancellation from queued and running
    assert sm.transition("queued", "cancel") == "cancelled"
    assert sm.transition("running", "cancel") == "cancelled"

    # Pause and resume
    assert sm.transition("queued", "pause") == "paused"
    assert sm.transition("running", "pause") == "paused"
    assert sm.transition("paused", "resume") == "running"
    assert sm.transition("paused", "cancel") == "cancelled"

    # Human-in-the-loop approval
    assert sm.transition("running", "request_approval") == "waiting_approval"
    assert sm.transition("waiting_approval", "approve") == "running"
    assert sm.transition("waiting_approval", "cancel") == "cancelled"

    # Terminal states reject transitions
    for term in ["succeeded", "failed", "cancelled", "timed_out"]:
        assert sm.is_terminal(term) is True
        with pytest.raises(ValueError):
            sm.transition(term, "start")


def test_worker_token_fencing_prevents_delayed_worker(run_env):
    """Verify fencing token prevents an outdated/zombie worker from validating a reallocated run."""
    store: SqliteRunStore = run_env["store"]

    submission = RunSubmission(
        project_id="proj-fence",
        title="Fencing Test",
        command=["python", "-c", "print('hello')"],
    )
    run, _ = store.save_submission(submission)

    # Worker 1 claims run
    wtoken1 = "worker-1"
    claimed = store.claim_run(run.id, wtoken1)
    assert claimed is not None
    assert claimed.worker_token == wtoken1
    assert claimed.attempt_number == 1

    # Worker 1 sends heartbeat
    assert store.record_heartbeat(run.id, wtoken1) is True

    # Simulate crash/interruption: heartbeat expires and recovery resets run to queued
    # Backdate heartbeat
    with store._connect() as conn:
        conn.execute(
            "UPDATE runs SET heartbeat_at = '2020-01-01T00:00:00+00:00' WHERE id = ?",
            (run.id,),
        )
    recovered = store.recover_stale_or_interrupted(heartbeat_timeout_seconds=1.0)
    assert run.id in recovered

    refreshed = store.get_run(run.id)
    assert refreshed.status == "queued"
    assert refreshed.worker_token is None

    # Worker 2 claims run
    wtoken2 = "worker-2"
    claimed2 = store.claim_run(run.id, wtoken2)
    assert claimed2 is not None
    assert claimed2.worker_token == wtoken2
    assert claimed2.attempt_number == 2

    # Delayed Worker 1 tries to send heartbeat or complete run -> FENCING ERROR!
    assert store.record_heartbeat(run.id, wtoken1) is False
    with pytest.raises(RunFencingError):
        store.complete_run(run.id, wtoken1, exit_code=0, output="Late output")

    # Worker 2 successfully completes
    final_run = store.complete_run(run.id, wtoken2, exit_code=0, output="Good output")
    assert final_run.status == "succeeded"
    assert final_run.output == "Good output"


def test_idempotent_run_submission_and_http_202(run_env):
    """Verify POST /api/v1/runs returns HTTP 202 with Location header and deduplicates identical idempotency_key."""
    engine = run_env["engine"]
    app = create_app(require_auth=False, run_engine=engine)
    client = TestClient(app, base_url="http://127.0.0.1:20131")

    payload = {
        "project_id": "proj-idemp",
        "title": "Idempotent Task",
        "command": ["python", "-c", "print('run')"],
        "idempotency_key": "idemp-key-12345",
    }

    # First submit -> 202 Accepted
    resp1 = client.post("/api/v1/runs", json=payload)
    assert resp1.status_code == 202
    assert "Location" in resp1.headers
    data1 = resp1.json()
    run_id1 = data1["run_id"]
    assert data1["status"] == "queued"
    assert resp1.headers["Location"] == f"/api/v1/runs/{run_id1}"

    # Second submit with same idempotency_key -> 202 with identical run_id
    resp2 = client.post("/api/v1/runs", json=payload)
    assert resp2.status_code == 202
    data2 = resp2.json()
    assert data2["run_id"] == run_id1

    # Store has exactly 1 run for this project
    runs, total = run_env["store"].list_runs(project_id="proj-idemp")
    assert total == 1
    assert runs[0].id == run_id1


def test_fair_scheduling_multi_tenant_rotation_and_backpressure(run_env):
    """Verify 2 global slots, max 1 per project: Project A does not starve Project B."""
    engine = run_env["engine"]
    store: SqliteRunStore = run_env["store"]
    scheduler: FairRunScheduler = engine.scheduler

    # Project A submits 3 runs
    for i in range(3):
        store.save_submission(
            RunSubmission(project_id="proj-A", title=f"Task A-{i}", command=["python", "-c", "pass"])
        )

    # Project B submits 1 run
    store.save_submission(
        RunSubmission(project_id="proj-B", title="Task B-0", command=["python", "-c", "pass"])
    )

    # First pick: should pick A-0
    cand1 = scheduler.select_next_run()
    assert cand1 is not None
    assert cand1.project_id == "proj-A"
    store.claim_run(cand1.id, "worker-a")

    # Second pick: Project A is already running 1 job (limit=1/proj).
    # Scheduler MUST pick Project B even though Project A has more queued jobs!
    cand2 = scheduler.select_next_run()
    assert cand2 is not None
    assert cand2.project_id == "proj-B"
    store.claim_run(cand2.id, "worker-b")

    # Third pick: Both slots are running (2 global max). Scheduler returns None!
    assert scheduler.select_next_run() is None

    # Complete Project A job: now Project A can run its next job
    store.complete_run(cand1.id, "worker-a", exit_code=0)
    cand3 = scheduler.select_next_run()
    assert cand3 is not None
    assert cand3.project_id == "proj-A"

    # Test backpressure: quota max_queued_per_project is 5
    for i in range(10):
        try:
            engine.submit_run(
                RunSubmission(project_id="proj-flood", title=f"Flood {i}", command=["python", "-c", "pass"])
            )
        except RunBackpressureError:
            # Backpressure triggered as expected
            break
    else:
        pytest.fail("RunBackpressureError was not triggered despite queue flood")


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object containment test")
def test_windows_job_object_process_tree_containment_and_timeout(run_env):
    """Verify child spawning a grandchild is completely terminated on timeout without orphan processes."""
    local_root: Path = run_env["local_root"]
    pid_file = local_root / "grandchild.pid"

    # Python script that spawns a grandchild sleeping for 30s, writes its PID to file, and sleeps 30s
    spawn_code = (
        "import subprocess, sys, time; from pathlib import Path; "
        "p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)']); "
        f"Path({repr(str(pid_file))}).write_text(str(p.pid)); "
        "time.sleep(30)"
    )

    store: SqliteRunStore = run_env["store"]
    sub = RunSubmission(
        project_id="proj-tree",
        title="Tree Containment Test",
        command=[sys.executable, "-c", spawn_code],
        timeout_seconds=2.0,  # Strict 2 second timeout
    )
    run, _ = store.save_submission(sub)

    executor = ProcessRunExecutor(local_root=local_root)
    worker_token = "worker-tree"
    store.claim_run(run.id, worker_token)

    start_t = time.monotonic()
    outcome, exit_code, stdout, stderr = executor.execute(
        run,
        worker_token=worker_token,
    )
    duration = time.monotonic() - start_t

    assert outcome == "timed_out"
    assert duration < 7.0  # Finished promptly around timeout
    assert pid_file.exists()

    grandchild_pid = int(pid_file.read_text().strip())
    # Crucial acceptance check: grandchild MUST be dead!
    assert win_pid_exited(grandchild_pid) is True


def test_bounded_output_and_environment_scrubbing(run_env):
    """Verify output flood is bounded and sensitive credentials are scrubbed from environment."""
    local_root: Path = run_env["local_root"]
    store: SqliteRunStore = run_env["store"]

    # Test output flood truncation
    flood_script = "import sys; sys.stdout.write('X' * 20000); sys.stdout.flush()"
    sub = RunSubmission(
        project_id="proj-bound",
        title="Output Bound Test",
        command=[sys.executable, "-c", flood_script],
        timeout_seconds=5.0,
    )
    run, _ = store.save_submission(sub)

    executor = ProcessRunExecutor(local_root=local_root, output_limit_bytes=2048)
    outcome, exit_code, stdout, stderr = executor.execute(
        run,
        worker_token="worker-bound",
    )
    assert outcome == "completed"
    assert exit_code == 0
    assert len(stdout.encode()) <= 2048 + 150  # Bounded at 2048 plus truncation notice
    assert "[Output truncated" in stdout

    # Test environment scrubbing: sensitive vars in parent are NOT inherited by child
    os.environ["GEMINI_API_KEY"] = "super-secret-gemini-key"
    os.environ["DEVCORE_SECRET_TOKEN"] = "devcore-token-xyz"
    try:
        check_script = (
            "import os, sys; "
            "leaks = [k for k in os.environ if 'SECRET' in k or 'API_KEY' in k]; "
            "sys.exit(len(leaks))"
        )
        sub_sec = RunSubmission(
            project_id="proj-sec",
            title="Secret Scrubbing Test",
            command=[sys.executable, "-c", check_script],
            timeout_seconds=5.0,
        )
        run_sec, _ = store.save_submission(sub_sec)
        outcome, code, _, _ = executor.execute(run_sec, worker_token="worker-sec")
        assert outcome == "completed"
        assert code == 0  # No leaked sensitive keys!
    finally:
        os.environ.pop("GEMINI_API_KEY", None)
        os.environ.pop("DEVCORE_SECRET_TOKEN", None)


def test_external_effect_idempotency(run_env):
    """Verify external side effects are executed at most once with cached results on replay."""
    effects: EffectIdempotencyStore = run_env["engine"].effects

    call_count = 0

    def create_pull_request(repo: str, branch: str) -> dict:
        nonlocal call_count
        call_count += 1
        return {"pr_number": 42, "repo": repo, "branch": branch}

    # First call -> executes function
    res1, executed1 = effects.execute_idempotent_effect(
        "proj-effect", "req-pr-101", "github.create_pr", create_pull_request, "myorg/myrepo", "feature"
    )
    assert executed1 is True
    assert call_count == 1
    assert res1["pr_number"] == 42

    # Second call with same idempotency key -> returns cached result, does NOT re-execute!
    res2, executed2 = effects.execute_idempotent_effect(
        "proj-effect", "req-pr-101", "github.create_pr", create_pull_request, "myorg/myrepo", "feature"
    )
    assert executed2 is False
    assert call_count == 1
    assert res2 == res1


@pytest.mark.anyio
async def test_hermes_runner_reports_backend_status():
    """Verify Hermes runner cleanly reports DOWN health and explicit error when backend is unimplemented."""
    runner = HermesRunner()
    status = await runner.report_status()
    assert status.health == "DOWN"
    assert status.backend_type == "hermes"

    from devcore_engine.runners.agent_runner import TaskSpec
    spec = TaskSpec(id="T-100", project="proj-h", title="Hermes Task")
    exec_res = await runner.run(spec)
    assert exec_res.status == "failed"
    assert "not implemented" in exec_res.error.lower()


def test_api_runs_authorization_and_actor_attribution(run_env):
    """Verify API Gateway enforces project authorization, roles, and attributes actor to authenticated principal."""
    ident_store = run_env["ident_store"]
    engine = run_env["engine"]

    add_user(ident_store, "usr_alice")
    add_user(ident_store, "usr_bob")

    # Alice is contributor on proj-auth
    set_membership(ident_store, "usr_alice", "proj-auth", "contributor")
    _, token_alice = issue_credential(ident_store, "usr_alice", ["proj-auth"], [READ, WRITE], ttl_seconds=3600)

    # Bob is reader only on proj-auth
    set_membership(ident_store, "usr_bob", "proj-auth", "reader")
    _, token_bob = issue_credential(ident_store, "usr_bob", ["proj-auth"], [READ], ttl_seconds=3600)

    app = create_app(require_auth=True, run_engine=engine)
    client = TestClient(app, base_url="http://127.0.0.1:20131")

    # 1. Unauthenticated submission -> 401
    resp_unauth = client.post(
        "/api/v1/runs",
        json={"project_id": "proj-auth", "title": "Test", "command": ["echo", "hi"]},
    )
    assert resp_unauth.status_code == 401

    # 2. Bob (reader only) tries to submit run (mutation) -> 403 Forbidden
    resp_bob_submit = client.post(
        "/api/v1/runs",
        json={"project_id": "proj-auth", "title": "Test", "command": ["echo", "hi"]},
        headers={"Authorization": f"Bearer {token_bob}"},
    )
    assert resp_bob_submit.status_code == 403

    # 3. Alice (contributor) submits run -> 202 Accepted
    resp_alice_submit = client.post(
        "/api/v1/runs",
        json={"project_id": "proj-auth", "title": "Alice Task", "command": ["echo", "hi"]},
        headers={"Authorization": f"Bearer {token_alice}"},
    )
    assert resp_alice_submit.status_code == 202
    data_alice = resp_alice_submit.json()
    assert data_alice["actor"] == "usr_alice"
    run_id = data_alice["run_id"]

    # 4. Bob (reader) can read run list and run details -> 200 OK
    resp_bob_list = client.get(
        "/api/v1/runs?project=proj-auth",
        headers={"Authorization": f"Bearer {token_bob}"},
    )
    assert resp_bob_list.status_code == 200
    assert resp_bob_list.json()["total_count"] == 1

    resp_bob_get = client.get(
        f"/api/v1/runs/{run_id}?project=proj-auth",
        headers={"Authorization": f"Bearer {token_bob}"},
    )
    assert resp_bob_get.status_code == 200
    assert resp_bob_get.json()["actor"] == "usr_alice"

    # 5. Alice pauses and cancels run -> 200 OK
    resp_pause = client.post(
        f"/api/v1/runs/{run_id}/pause?project=proj-auth",
        headers={"Authorization": f"Bearer {token_alice}"},
    )
    assert resp_pause.status_code == 200
    assert resp_pause.json()["status"] == "paused"

    resp_cancel = client.post(
        f"/api/v1/runs/{run_id}/cancel?project=proj-auth",
        headers={"Authorization": f"Bearer {token_alice}"},
    )
    assert resp_cancel.status_code == 200
    assert resp_cancel.json()["status"] == "cancelled"


def test_idempotent_replay_bypasses_backpressure(run_env):
    """P2: Idempotent replay of an admitted run must succeed even if queue is at backpressure limit."""
    quota = RunQuotaConfig(max_queued_per_project=2)
    engine = DurableRunEngine(quota_config=quota)

    # Submit 2 runs up to quota
    r1, created1 = engine.submit_run(
        RunSubmission(project_id="proj-idemp", title="R1", command=["echo", "1"], idempotency_key="key-1")
    )
    assert created1 is True
    r2, created2 = engine.submit_run(
        RunSubmission(project_id="proj-idemp", title="R2", command=["echo", "2"], idempotency_key="key-2")
    )
    assert created2 is True

    # Third new run exceeds queue backpressure -> RunBackpressureError
    with pytest.raises(RunBackpressureError):
        engine.submit_run(
            RunSubmission(project_id="proj-idemp", title="R3", command=["echo", "3"], idempotency_key="key-3")
        )

    # Replaying existing admitted run (key-1) MUST succeed without RunBackpressureError
    replayed, created = engine.submit_run(
        RunSubmission(project_id="proj-idemp", title="R1 retry", command=["echo", "1"], idempotency_key="key-1")
    )
    assert created is False
    assert replayed.id == r1.id


def test_pause_terminates_process_and_prevents_completion(run_env):
    """P1 states: Pausing a running run must terminate child process and prevent transition to succeeded."""
    engine = DurableRunEngine()
    long_cmd = [sys.executable, "-c", "import time; time.sleep(10)"]
    sub = RunSubmission(project_id="proj-pause", title="Long Run", command=long_cmd)
    record, _ = engine.submit_run(sub)

    import threading
    step_thread = threading.Thread(target=engine.step, daemon=True)
    step_thread.start()

    # Wait until run status is 'running'
    current = None
    for _ in range(50):
        current = engine.get_run(record.id)
        if current and current.status == "running":
            break
        time.sleep(0.05)
    assert current is not None and current.status == "running"

    # Pause run while executing
    paused = engine.pause_run(record.id)
    assert paused.status == "paused"

    step_thread.join(timeout=3.0)
    assert not step_thread.is_alive()

    # Run remains paused
    final_record = engine.get_run(record.id)
    assert final_record.status == "paused"

    # Attempting to complete_run on paused run MUST raise RunTransitionError
    with pytest.raises(RunTransitionError):
        engine.store.complete_run(record.id, "bogus_token", exit_code=0)


def test_background_worker_lifecycle(run_env):
    """P1 execution: background worker thread drains submitted runs without manual step()."""
    engine = DurableRunEngine()
    engine.start_worker(poll_interval=0.05)
    try:
        sub = RunSubmission(
            project_id="proj-worker",
            title="Auto worker task",
            command=[sys.executable, "-c", "print('worker processed')"],
        )
        rec, _ = engine.submit_run(sub)
        assert rec.status == "queued"
        engine.wake_worker()

        # Poll until finished
        updated = None
        for _ in range(60):
            updated = engine.get_run(rec.id)
            if updated and updated.is_terminal():
                break
            time.sleep(0.05)

        assert updated is not None and updated.status == "succeeded"
        assert "worker processed" in updated.output
    finally:
        engine.stop_worker()


def test_windows_job_failure_containment(run_env):
    """P1 confinement: executor terminates spawned process if Job assignment fails."""
    executor = ProcessRunExecutor()
    sub = RunRecord(
        id="run-fail-job",
        project_id="proj-fail",
        title="Fail Job",
        status="running",
        command=[sys.executable, "-c", "import time; time.sleep(10)"],
    )

    from unittest.mock import patch
    if os.name == "nt":
        with patch("devcore_engine.infra.windows_job.WindowsJob.assign", side_effect=RuntimeError("Job assignment failed")):
            outcome, exit_code, stdout, stderr = executor.execute(sub, worker_token="tok")
            assert outcome == "failed"
            assert "Failed to assign process" in stderr


def test_worker_concurrent_parallel_execution(run_env):
    """P1 execution: background worker drains multiple projects concurrently in parallel."""
    engine = DurableRunEngine()
    # Submit 2 runs from different projects that each take ~0.5s
    sub1 = RunSubmission(
        project_id="proj-concurrent-1",
        title="Concurrent Job 1",
        command=[sys.executable, "-c", "import time; time.sleep(0.5); print('done 1')"],
    )
    sub2 = RunSubmission(
        project_id="proj-concurrent-2",
        title="Concurrent Job 2",
        command=[sys.executable, "-c", "import time; time.sleep(0.5); print('done 2')"],
    )
    r1, _ = engine.submit_run(sub1)
    r2, _ = engine.submit_run(sub2)

    engine.start_worker(poll_interval=0.02)
    try:
        # Check that both runs are executing simultaneously (both reach 'running' at the same time)
        both_running = False
        start_time = time.time()
        while time.time() - start_time < 3.0:
            rec1 = engine.get_run(r1.id)
            rec2 = engine.get_run(r2.id)
            if rec1 and rec2 and rec1.status == "running" and rec2.status == "running":
                both_running = True
                break
            if (rec1 and rec1.is_terminal()) and (rec2 and rec2.is_terminal()):
                break
            time.sleep(0.02)

        assert both_running, "Both runs should have been executing concurrently in parallel slots"

        # Wait for both to complete
        for _ in range(60):
            rec1 = engine.get_run(r1.id)
            rec2 = engine.get_run(r2.id)
            if rec1 and rec2 and rec1.is_terminal() and rec2.is_terminal():
                break
            time.sleep(0.05)

        assert rec1.status == "succeeded"
        assert rec2.status == "succeeded"
        assert "done 1" in rec1.output
        assert "done 2" in rec2.output
    finally:
        engine.stop_worker()


def test_api_lifespan_starts_and_stops_worker(run_env):
    """Worker API lifecycle: FastAPI lifespan connects worker start on startup and stop on shutdown."""
    engine = DurableRunEngine()
    app = create_app(require_auth=False, run_engine=engine, start_run_worker=True)

    assert not engine._worker_running

    with TestClient(app) as client:
        # Startup event triggered: worker should now be running
        assert engine._worker_running

        # Submit run via API
        resp = client.post(
            "/api/v1/runs?project=proj-life",
            json={
                "project_id": "proj-life",
                "title": "Lifespan managed run",
                "command": [sys.executable, "-c", "print('lifespan auto executed')"],
            },
        )
        assert resp.status_code == 202
        run_id = resp.json()["run_id"]

        # Worker automatically processes the run without manual step()
        finished = None
        for _ in range(60):
            get_resp = client.get(f"/api/v1/runs/{run_id}?project=proj-life")
            assert get_resp.status_code == 200
            data = get_resp.json()
            if data["status"] in {"succeeded", "failed"}:
                finished = data
                break
            time.sleep(0.05)

        assert finished is not None
        assert finished["status"] == "succeeded"
        assert "lifespan auto executed" in finished["output"]

    # Shutdown event triggered: worker must be stopped
    assert not engine._worker_running


def test_stop_worker_interrupts_active_runs_within_timeout(run_env):
    """P1 lifecycle: stop_worker() interrupts active runs and returns within timeout."""
    engine = DurableRunEngine()
    # Submit a run with a long duration (sleep 30s)
    sub = RunSubmission(
        project_id="proj-interrupt",
        title="Very Long Run",
        command=[sys.executable, "-c", "import time; time.sleep(30)"],
    )
    rec, _ = engine.submit_run(sub)

    engine.start_worker(poll_interval=0.02)

    # Wait until the run is running
    running = False
    for _ in range(50):
        current = engine.get_run(rec.id)
        if current and current.status == "running":
            running = True
            break
        time.sleep(0.05)
    assert running, "Run should have transitioned to running"

    # Call stop_worker with a small timeout (1.5s)
    # It MUST interrupt the run immediately and return within the timeout
    stop_start = time.monotonic()
    engine.stop_worker(timeout=1.5)
    stop_duration = time.monotonic() - stop_start

    # Verify stop_worker returned well within the timeout and did NOT wait for sleep(30)
    assert stop_duration < 2.0, f"stop_worker took {stop_duration:.2f}s, expected < 2.0s"
    assert not engine._worker_running

    # Verify that the active run was terminated and marked cancelled
    final_rec = engine.get_run(rec.id)
    assert final_rec is not None
    assert final_rec.status in {"cancelled", "failed"}



