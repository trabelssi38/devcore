"""No real services or active databases: restart limits and concurrent claims."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import threading
from types import SimpleNamespace

import pytest
from devcore_engine.infra.restart_budget import RestartBudget
from devcore_engine.infra import system_watcher


def test_budget_persists_across_instances_and_backoff(tmp_path):
    path = tmp_path / "local/Runtime/restarts.db"
    for now, blocked_time, delay in [(100, 101, 5), (105, 106, 10), (115, 116, 20)]:
        budget = RestartBudget(path)
        owner, reason = budget.reserve("127.0.0.1:8787", now=now)
        assert owner and reason == "restart_reserved"
        assert RestartBudget(path).reserve("127.0.0.1:8787", now=blocked_time)[1] == "restart_in_progress"
        budget.release("127.0.0.1:8787", owner)
        reason = RestartBudget(path).reserve("127.0.0.1:8787", now=blocked_time)[1]
        assert reason == ("restart_budget_exhausted" if now == 115 else "restart_backoff")
    assert RestartBudget(path).reserve("127.0.0.1:8787", now=699)[1] == "restart_budget_exhausted"
    assert RestartBudget(path).reserve("127.0.0.1:8787", now=700)[0]
    assert RestartBudget(path).reserve("127.0.0.1:8789", now=120)[0]


def test_abandoned_lease_and_foreign_release(tmp_path):
    budget = RestartBudget(tmp_path / "restarts.db")
    owner, _ = budget.reserve("native", now=100)
    budget.release("native", "wrong-owner")
    assert budget.reserve("native", now=159)[1] == "restart_in_progress"
    next_owner, _ = budget.reserve("native", now=160)
    assert next_owner and next_owner != owner
    budget.release("native", owner)
    assert budget.reserve("native", now=161)[1] == "restart_in_progress"


def test_parallel_watchers_get_only_one_lease(tmp_path):
    path = tmp_path / "restarts.db"
    owner, _ = RestartBudget(path).reserve("initialize", now=100)
    barrier = threading.Barrier(2)
    def reserve():
        barrier.wait()
        return RestartBudget(path).reserve("native", now=100)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: reserve(), range(2)))
    assert sum(owner is not None for owner, _ in results) == 1
    assert any(reason == "restart_in_progress" for _, reason in results)


@pytest.mark.parametrize("column,value", [
    ("attempts", -1), ("attempts", 0), ("attempts", 4),
    ("window_start", -1), ("next_attempt", 99),
    ("lease_until", 99), ("lease_until", float("inf")),
    ("next_attempt", "broken"),
])
def test_corrupt_restart_state_is_preserved_and_denies_reservation(tmp_path, column, value):
    import sqlite3
    budget = RestartBudget(tmp_path / "restarts.db")
    budget.reserve("native", now=100)
    with sqlite3.connect(budget.path) as conn:
        # Column names are a fixed test allowlist, never external input.
        conn.execute(f"UPDATE restart_budget SET {column}=? WHERE service='native'", (value,))
        before = conn.execute("SELECT * FROM restart_budget").fetchall()
    assert budget.reserve("native", now=1000) == (None, "restart_state_invalid")
    with sqlite3.connect(budget.path) as conn:
        assert conn.execute("SELECT * FROM restart_budget").fetchall() == before


@pytest.mark.parametrize("now", [float("nan"), float("inf"), -1, True, "100"])
def test_invalid_clock_does_not_create_store(tmp_path, now):
    path = tmp_path / "not-created/restarts.db"
    with pytest.raises(ValueError):
        RestartBudget(path).reserve("native", now=now)
    assert not path.parent.exists()


def watcher(tmp_path, monkeypatch):
    for key, leaf in (("DEVCORE_LOCAL_ROOT", "local"), ("DEVCORE_DATA_ROOT", "data")):
        monkeypatch.setenv(key, str(tmp_path / leaf))
    instance = system_watcher.SystemWatcher.__new__(system_watcher.SystemWatcher)
    instance.local_root = tmp_path / "local"
    instance.data_root = tmp_path / "data"
    instance.log = lambda message: None
    instance.event_bus = type("Bus", (), {"publish": lambda *a, **k: None})()
    return instance


def test_failed_launch_spends_budget_and_releases_lock(tmp_path, monkeypatch):
    instance = watcher(tmp_path, monkeypatch)
    monkeypatch.setattr(system_watcher, "check_port", lambda *a: False)
    def fail(*a, **kw):
        raise OSError("fixture launch failure")
    monkeypatch.setattr(system_watcher.subprocess, "Popen", fail)
    assert not instance.check_and_heal_service("native", "127.0.0.1", 8787, ["fixture"])
    budget = RestartBudget(instance.local_root / "Runtime/service_restarts.sqlite3")
    import time
    assert budget.reserve("127.0.0.1:8787", now=time.time())[1] == "restart_backoff"


def test_online_service_does_not_create_restart_state(tmp_path, monkeypatch):
    instance = watcher(tmp_path, monkeypatch)
    monkeypatch.setattr(system_watcher, "check_port", lambda *a: True)
    monkeypatch.setattr(system_watcher, "probe_headroom_health", lambda route: True)
    monkeypatch.setattr(system_watcher.subprocess, "Popen", lambda *a, **k: pytest.fail("No launch"))
    assert instance.check_and_heal_service("native", "127.0.0.1", 8787, ["fixture"])
    assert not (instance.local_root / "Runtime/service_restarts.sqlite3").exists()
    assert (instance.local_root / "Runtime/services.launch.guard").exists()


def test_wrong_active_route_neither_restarts_nor_publishes_healed(tmp_path, monkeypatch):
    instance = watcher(tmp_path, monkeypatch)
    monkeypatch.setattr(system_watcher, "check_port", lambda *a: True)
    monkeypatch.setattr(system_watcher, "probe_headroom_health", lambda route: False)
    monkeypatch.setattr(system_watcher.subprocess, "Popen", lambda *a, **k: pytest.fail("Occupied port must not restart"))
    instance.event_bus.publish = lambda *a, **k: pytest.fail("Wrong profile must not be healed")
    assert not instance.check_and_heal_service("Headroom native", "127.0.0.1", 8787, ["fixture"])
    assert not (instance.local_root / "Runtime/service_restarts.sqlite3").exists()
    assert (instance.local_root / "Runtime/services.launch.guard").exists()


@pytest.mark.parametrize("ready", [False, True])
def test_recovery_event_requires_route_readiness(tmp_path, monkeypatch, ready):
    instance = watcher(tmp_path, monkeypatch)
    calls, events = [False, False], []
    def port(*args, **kwargs):
        return calls.pop(0) if calls else True
    monkeypatch.setattr(system_watcher, "check_port", port)
    clock = [0.0]
    monkeypatch.setattr(system_watcher.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(system_watcher.time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds))
    def health(route, timeout):
        assert route == "native" and 0 < timeout <= 3
        return ready
    monkeypatch.setattr(system_watcher, "probe_headroom_health", health)
    monkeypatch.setattr(system_watcher.subprocess, "Popen", lambda *a, **k: SimpleNamespace(poll=lambda: None))
    instance.event_bus.publish = lambda *a, **k: events.append(a)
    assert instance.check_and_heal_service("native", "127.0.0.1", 8787, ["fixture"], wait_timeout=2) is ready
    assert len(events) == int(ready)
    if ready:
        assert events[0][1]["status"] == "READY"
        assert events[0][1]["verification"] == "route_contract"


def test_unavailable_reservation_never_launches(tmp_path, monkeypatch):
    instance = watcher(tmp_path, monkeypatch)
    instance.local_root.mkdir()
    (instance.local_root / "Runtime").write_text("fixture blocking directory")
    monkeypatch.setattr(system_watcher, "check_port", lambda *a: False)
    monkeypatch.setattr(system_watcher.subprocess, "Popen", lambda *a, **k: pytest.fail("No launch without reservation"))
    assert not instance.check_and_heal_service("native", "127.0.0.1", 8787, ["fixture"])


@pytest.mark.parametrize("wait", [0, -1, 31])
def test_invalid_wait_rejected_before_service_probe(tmp_path, monkeypatch, wait):
    instance = watcher(tmp_path, monkeypatch)
    monkeypatch.setattr(system_watcher, "check_port", lambda *a: pytest.fail("No probe"))
    with pytest.raises(ValueError):
        instance.check_and_heal_service("native", "127.0.0.1", 8787, ["fixture"], wait_timeout=wait)


def test_startup_poll_uses_total_deadline(tmp_path, monkeypatch):
    instance = watcher(tmp_path, monkeypatch)
    clock = [0.0]
    monkeypatch.setattr(system_watcher.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(system_watcher.time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds))
    def probe(host, port, timeout=0.5):
        clock[0] += timeout
        return False
    monkeypatch.setattr(system_watcher, "check_port", probe)
    monkeypatch.setattr(system_watcher.subprocess, "Popen", lambda *a, **k: SimpleNamespace(poll=lambda: None))
    assert not instance.check_and_heal_service("fixture", "127.0.0.1", 11111, ["fixture"], wait_timeout=3)
    assert clock[0] <= 4  # Two initial socket checks plus the 3 s total startup wait.


def test_stalled_health_probe_is_killed_at_global_deadline(tmp_path, monkeypatch):
    watcher(tmp_path, monkeypatch)  # Set disposable child roots before launching.
    stalled = tmp_path / "stalled.py"
    stalled.write_text("import time;time.sleep(60)", encoding="utf-8")
    monkeypatch.setattr(system_watcher, "HEALTH_PROBE_SCRIPT", stalled)
    import time
    started = time.monotonic()
    assert not system_watcher.probe_headroom_health("native")
    assert time.monotonic() - started < 6


@pytest.mark.parametrize("port", [11111, 8787])
def test_success_after_startup_deadline_is_not_published(tmp_path, monkeypatch, port):
    instance = watcher(tmp_path, monkeypatch)
    clock, checks = [0.0], [False, False]
    monkeypatch.setattr(system_watcher.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(system_watcher.time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds))
    def probe(*args, **kwargs):
        if checks:
            return checks.pop(0)
        if port == 11111:
            clock[0] = 2.0
        return True
    def health(*args, **kwargs):
        clock[0] = 2.0
        return True
    monkeypatch.setattr(system_watcher, "check_port", probe)
    monkeypatch.setattr(system_watcher, "probe_headroom_health", health)
    monkeypatch.setattr(system_watcher.subprocess, "Popen", lambda *a, **k: SimpleNamespace(poll=lambda: None))
    instance.event_bus.publish = lambda *a, **k: pytest.fail("Late readiness cannot declare recovery")
    assert not instance.check_and_heal_service("fixture", "127.0.0.1", port, ["fixture"], wait_timeout=2)


def test_health_probe_validates_result_and_failed_execution(tmp_path, monkeypatch):
    watcher(tmp_path, monkeypatch)
    from types import SimpleNamespace
    import json
    from devcore_engine.infra.llm_route_contract import profile
    payload = {"service": "headroom-devcore", "route": "native", "status": "ready", "port": 8787, "profile": profile("native")}
    def run(command, **kwargs):
        assert kwargs["timeout"] == 3 and "-I" in command
        return SimpleNamespace(returncode=0, stdout=json.dumps(payload))
    monkeypatch.setattr(system_watcher.subprocess, "run", run)
    assert system_watcher.probe_headroom_health("native")
    payload["profile"]["openai_api_url"] = "http://127.0.0.1:20130"
    assert not system_watcher.probe_headroom_health("native")
    monkeypatch.setattr(system_watcher.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=1, stdout=""))
    assert not system_watcher.probe_headroom_health("native")


@pytest.mark.parametrize("exit_stage", ["initial", "after_readiness"])
@pytest.mark.parametrize("code", [0, 17])
def test_exited_child_cannot_publish_recovery(tmp_path, monkeypatch, exit_stage, code):
    instance = watcher(tmp_path, monkeypatch)
    checks, logs = [False, False], []
    instance.log = logs.append
    monkeypatch.setattr(system_watcher, "check_port", lambda *a, **k: checks.pop(0) if checks else True)
    process = SimpleNamespace(returncode=None)
    polls = [code] if exit_stage == "initial" else [None, code]
    def poll():
        process.returncode = polls.pop(0)
        return process.returncode
    process.poll = poll
    monkeypatch.setattr(system_watcher.subprocess, "Popen", lambda *a, **k: process)
    monkeypatch.setattr(system_watcher, "probe_headroom_health", lambda *a, **k: True)
    monkeypatch.setattr(system_watcher.time, "sleep", lambda seconds: None)
    instance.event_bus.publish = lambda *a, **k: pytest.fail("Exited child cannot declare recovery")
    assert not instance.check_and_heal_service("native", "127.0.0.1", 8787, ["fixture"], wait_timeout=2)
    assert any(f"code {code}" in line for line in logs)
    import time
    budget = RestartBudget(instance.local_root / "Runtime/service_restarts.sqlite3")
    assert budget.reserve("127.0.0.1:8787", now=time.time())[1] == "restart_backoff"
