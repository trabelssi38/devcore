"""Scheduler leases use disposable files and isolated Python child processes."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import time
import os

import pytest

SCHEDULER = Path(__file__).resolve().parents[1] / "Scheduler"
sys.path.insert(0, str(SCHEDULER))
from scheduler_lock import SchedulerLeaseLock


def child(path, owner, operation="acquire"):
    script = """import sys, os
sys.path.insert(0, sys.argv[1])
from scheduler_lock import SchedulerLeaseLock
lock = SchedulerLeaseLock(sys.argv[2], sys.argv[3])
if sys.argv[4] == 'crash':
    with lock._guard():
        os._exit(0)
else:
    print(lock.acquire())
"""
    return subprocess.run([sys.executable, "-I", "-c", script, str(SCHEDULER),
        str(path), owner, operation], capture_output=True, text=True, timeout=8)


def test_concurrent_processes_have_single_owner(tmp_path):
    path = tmp_path / "scheduler.lock"
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda owner: child(path, owner), ["a", "b", "c", "d"]))
    assert all(result.returncode == 0 for result in results)
    assert sum(result.stdout.strip() == "True" for result in results) == 1
    assert SchedulerLeaseLock(path, "observer").get_owner() in {"a", "b", "c", "d"}


def test_guard_contention_is_nonblocking_and_crash_releases_os_lock(tmp_path):
    path = tmp_path / "scheduler.lock"
    lock = SchedulerLeaseLock(path, "parent")
    with lock._guard():
        result = child(path, "child")
        assert result.returncode == 0 and result.stdout.strip() == "False"
    assert child(path, "crashed", "crash").returncode == 0
    assert lock.acquire()


@pytest.mark.parametrize("raw", [b"broken", b"[]", b'{}', b"x" * 65537],
    ids=["invalid-json", "array", "missing-fields", "oversized"])
def test_corruption_is_preserved_and_cannot_grant_lease(tmp_path, raw):
    path = tmp_path / "scheduler.lock"
    path.write_bytes(raw)
    lock = SchedulerLeaseLock(path, "a")
    assert not lock.acquire() and not lock.renew() and not lock.release()
    assert path.read_bytes() == raw


def test_expired_renew_and_foreign_release_cannot_overwrite_owner(tmp_path):
    path = tmp_path / "scheduler.lock"
    path.write_text(json.dumps({"owner": "a", "expires_at":
        (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()}))
    a, b = SchedulerLeaseLock(path, "a"), SchedulerLeaseLock(path, "b")
    assert not a.renew()
    assert b.acquire()
    before = path.read_bytes()
    assert not a.release() and not a.renew() and not a.acquire()
    assert path.read_bytes() == before
    assert b.renew() and b.release()
    assert not path.exists()


def test_failed_atomic_replace_preserves_old_lease(tmp_path, monkeypatch):
    import scheduler_lock
    path = tmp_path / "scheduler.lock"
    lock = SchedulerLeaseLock(path, "a")
    assert lock.acquire()
    before = path.read_bytes()
    def fail(*args):
        raise OSError("fixture publication failure")
    monkeypatch.setattr(scheduler_lock.os, "replace", fail)
    assert not lock.renew()
    assert path.read_bytes() == before
    assert not list(tmp_path.glob("*.tmp"))


def test_execution_scope_excludes_peer_after_timed_lease_expiry(tmp_path):
    path = tmp_path / "scheduler.lock"
    lock = SchedulerLeaseLock(path, "a", lease_duration_seconds=1)
    assert lock.acquire()
    with lock.hold():
        time.sleep(1.2)
        assert child(path, "b").stdout.strip() == "False"
    assert lock.get_owner() == "a"  # Lease renewed before releasing OS guard.
    assert lock.release()
    assert child(path, "b").stdout.strip() == "True"


def test_foreign_execution_scope_cannot_enter(tmp_path):
    path = tmp_path / "scheduler.lock"
    assert SchedulerLeaseLock(path, "a").acquire()
    with pytest.raises(RuntimeError):
        with SchedulerLeaseLock(path, "b").hold():
            pytest.fail("Foreign owner cannot execute")


def test_execution_exception_releases_guard_without_renewing_expired_lease(tmp_path):
    path = tmp_path / "scheduler.lock"
    lock = SchedulerLeaseLock(path, "a", lease_duration_seconds=1)
    assert lock.acquire()
    with pytest.raises(RuntimeError, match="fixture"):
        with lock.hold():
            time.sleep(1.2)
            raise RuntimeError("fixture job failure")
    assert child(path, "b").stdout.strip() == "True"


def test_scheduler_cycle_holds_guard_through_command_history_and_save(tmp_path, monkeypatch):
    import scheduler_tick
    from types import SimpleNamespace
    path = tmp_path / "scheduler.lock"
    class EndFixtureLoop(BaseException):
        pass
    job = SimpleNamespace(id="fixture", enabled=True, timezone="UTC", command=None,
        state=SimpleNamespace(next_run_at=datetime.now(timezone.utc).isoformat(), completed_count=0))
    monkeypatch.setattr(scheduler_tick, "load_jobs", lambda path: [job])
    monkeypatch.setattr(scheduler_tick, "_ensure_aware", lambda now, tz: datetime.now(timezone.utc))
    monkeypatch.setattr(scheduler_tick, "compute_next_run", lambda *a: datetime.now(timezone.utc) + timedelta(hours=1))
    monkeypatch.setattr(scheduler_tick.scheduler_history, "init_db", lambda *a: None)
    monkeypatch.setattr(scheduler_tick.scheduler_history, "is_run_completed", lambda *a: False)
    monkeypatch.setattr(scheduler_tick.scheduler_history, "record_run", lambda **k: True)
    stages = []
    def peer_refused(stage):
        result = child(path, "peer")
        assert result.returncode == 0 and result.stdout.strip() == "False"
        stages.append(stage)
    def execute(command):
        peer_refused("command")
        return 0, "fixture", ""
    monkeypatch.setattr(scheduler_tick, "execute_job_command", execute)
    monkeypatch.setattr(scheduler_tick.scheduler_history, "update_run", lambda **k: peer_refused("history") or True)
    monkeypatch.setattr(scheduler_tick, "save_jobs", lambda *a: peer_refused("save"))
    def stop(seconds):
        raise EndFixtureLoop()
    monkeypatch.setattr(scheduler_tick.time, "sleep", stop)
    with pytest.raises(EndFixtureLoop):
        scheduler_tick.main_loop(tmp_path / "history.db", tmp_path / "jobs.json", path)
    assert stages == ["command", "history", "save"]
    assert job.state.completed_count == 1


def registry_fixture(tmp_path):
    platform, local = tmp_path / "platform", tmp_path / "local"
    (platform / "Scheduler").mkdir(parents=True)
    (platform / "Scheduler/jobs.devcore.json").write_text("[]")
    (local / "Scheduler").mkdir(parents=True)
    return platform, local


def test_registry_sync_refuses_busy_execution_guard(tmp_path):
    import scheduler_sync
    platform, local = registry_fixture(tmp_path)
    dynamic = local / "Scheduler/jobs.json"
    dynamic.write_text("[]")
    lock = SchedulerLeaseLock(local / "Scheduler/scheduler.lock", "worker")
    assert lock.acquire()
    with lock.hold():
        assert scheduler_sync.sync_registry(platform, local) is False
        assert dynamic.read_text() == "[]"
    assert scheduler_sync.sync_registry(platform, local) is True


@pytest.mark.parametrize("raw", ["broken", "{}", '[{"state": {}}]', '[{"id":"a"},{"id":"a"}]'])
def test_registry_sync_preserves_invalid_existing_state(tmp_path, raw):
    import scheduler_sync
    platform, local = registry_fixture(tmp_path)
    dynamic = local / "Scheduler/jobs.json"
    dynamic.write_text(raw)
    assert scheduler_sync.sync_registry(platform, local) is False
    assert dynamic.read_text() == raw


def test_registry_publication_failure_preserves_existing_file(tmp_path, monkeypatch):
    import scheduler_sync, scheduler_storage
    platform, local = registry_fixture(tmp_path)
    dynamic = local / "Scheduler/jobs.json"
    dynamic.write_text("[ ]")
    def fail(*args):
        raise OSError("fixture replacement failure")
    monkeypatch.setattr(scheduler_storage.os, "replace", fail)
    assert scheduler_sync.sync_registry(platform, local) is False
    assert dynamic.read_text() == "[ ]"
    assert not list(dynamic.parent.glob("*.tmp"))


def test_registry_cli_updates_only_local_root(tmp_path):
    platform, local = registry_fixture(tmp_path)
    shared = tmp_path / "shared"
    (shared / "Scheduler").mkdir(parents=True)
    shared_file = shared / "Scheduler/jobs.json"
    shared_file.write_text("shared-sentinel")
    env = dict(os.environ, DEVCORE_PLATFORM_ROOT=str(platform),
        DEVCORE_LOCAL_ROOT=str(local), DEVCORE_DATA_ROOT=str(shared))
    result = subprocess.run([sys.executable, "-I", str(SCHEDULER / "scheduler_sync.py")],
        env=env, capture_output=True, text=True, timeout=8)
    assert result.returncode == 0, result.stderr
    assert json.loads((local / "Scheduler/jobs.json").read_text()) == []
    assert shared_file.read_text() == "shared-sentinel"


def test_scheduler_startup_refuses_sync_failure_without_bootstrap(tmp_path, monkeypatch):
    import runpy, scheduler_sync
    platform, local = registry_fixture(tmp_path)
    monkeypatch.setenv("DEVCORE_PLATFORM_ROOT", str(platform))
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(local))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(tmp_path / "shared"))
    monkeypatch.setattr(scheduler_sync, "sync_registry", lambda *a: False)
    with pytest.raises(SystemExit) as result:
        runpy.run_path(str(SCHEDULER / "scheduler_tick.py"), run_name="__main__")
    assert result.value.code == 1
    assert not (local / "Scheduler/jobs.json").exists()


@pytest.mark.parametrize("raw", [None, "broken", "{}", '[{"id":"incomplete"}]'])
def test_invalid_jobs_raise_instead_of_becoming_empty_schedule(tmp_path, raw):
    import scheduler_tick
    path = tmp_path / "jobs.json"
    if raw is not None:
        path.write_text(raw)
    with pytest.raises((OSError, ValueError, TypeError)):
        scheduler_tick.load_jobs(path)
    if raw is not None:
        assert path.read_text() == raw


def test_save_jobs_failure_propagates_and_preserves_existing_state(tmp_path, monkeypatch):
    import scheduler_tick, scheduler_storage
    path = tmp_path / "jobs.json"
    path.write_text("[ ]")
    def fail(*args):
        raise OSError("fixture disk failure")
    monkeypatch.setattr(scheduler_storage.os, "replace", fail)
    with pytest.raises(OSError, match="fixture disk failure"):
        scheduler_tick.save_jobs([], path)
    assert path.read_text() == "[ ]"
    assert not list(tmp_path.glob("*.tmp"))


def test_load_failure_aborts_cycle_without_execution_or_lease_renewal(tmp_path, monkeypatch):
    import scheduler_tick
    path = tmp_path / "scheduler.lock"
    writes = []
    original = scheduler_tick.scheduler_lock.SchedulerLeaseLock._write_lock
    class EndFixtureLoop(BaseException):
        pass
    def broken(*args):
        raise ValueError("fixture corrupt registry")
    monkeypatch.setattr(scheduler_tick, "load_jobs", broken)
    monkeypatch.setattr(scheduler_tick.scheduler_history, "init_db", lambda *a: None)
    monkeypatch.setattr(scheduler_tick, "execute_job_command", lambda *a: pytest.fail("Corrupt registry must not execute"))
    monkeypatch.setattr(scheduler_tick.scheduler_lock.SchedulerLeaseLock, "_write_lock",
        lambda self: writes.append(self.owner_id) or original(self))
    def stop(seconds):
        raise EndFixtureLoop()
    monkeypatch.setattr(scheduler_tick.time, "sleep", stop)
    with pytest.raises(EndFixtureLoop):
        scheduler_tick.main_loop(tmp_path / "history.db", tmp_path / "jobs.json", path)
    assert len(writes) == 1  # Acquire only; failed hold does not renew.
