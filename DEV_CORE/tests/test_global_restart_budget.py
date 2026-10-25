"""A failed global stack cannot spin forever under the five-minute tick."""

import importlib.util
import json
from pathlib import Path
import sys

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "Scripts"


def load_budget(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(tmp_path / "local"))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(tmp_path / "data"))
    spec = importlib.util.spec_from_file_location("global_restart_budget", SCRIPTS / "global_restart_budget.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.RestartBudget(tmp_path / "local" / "GlobalStack")


def test_three_fast_failures_latch_until_explicit_reset(tmp_path, monkeypatch):
    budget = load_budget(tmp_path, monkeypatch)
    for at in (1000, 1300, 1600):
        state = budget.record_failure(started_at=at - 2, finished_at=at,
                                      phase="supervisor", exit_code=1)
    assert state["exhausted"] is True
    assert state["alert"]["requires_operator"] is True
    assert budget.allow() is False
    assert type(budget)(budget.path.parent).allow() is False
    with pytest.raises(ValueError, match="reason"):
        budget.reset(reason="", at=2000)
    budget.reset(reason="operator inspected the failure", at=2000)
    assert budget.allow() is True
    assert budget.read()["failures"] == []


def test_long_healthy_run_breaks_failure_streak(tmp_path, monkeypatch):
    budget = load_budget(tmp_path, monkeypatch)
    budget.record_failure(started_at=100, finished_at=110, phase="schema", exit_code=1)
    budget.record_failure(started_at=200, finished_at=210, phase="schema", exit_code=1)
    state = budget.record_failure(started_at=300, finished_at=300 + 1800,
                                  phase="supervisor", exit_code=1)
    assert state["exhausted"] is False
    assert len(state["failures"]) == 1
    budget.record_success()
    assert budget.read()["failures"] == []


def test_corrupt_budget_refuses_launch(tmp_path, monkeypatch):
    budget = load_budget(tmp_path, monkeypatch)
    budget.path.parent.mkdir(parents=True)
    budget.path.write_text(json.dumps({"version": 1, "failures": "invalid", "exhausted": False}))
    with pytest.raises(ValueError, match="Invalid restart budget"):
        budget.allow()


def test_exhausted_budget_blocks_wrapper_before_source_or_database(tmp_path, monkeypatch, capsys):
    budget = load_budget(tmp_path, monkeypatch)
    for at in (1000, 1300, 1600):
        budget.record_failure(started_at=at - 1, finished_at=at, phase="supervisor")
    release = tmp_path / "runtime" / "releases" / "release"
    expected = release.parent.parent / "state" / "local" / "GlobalStack"
    expected.mkdir(parents=True)
    (expected / "restart-budget.json").write_bytes(budget.path.read_bytes())
    monkeypatch.syspath_prepend(str(SCRIPTS))
    spec = importlib.util.spec_from_file_location("global_stack_wrapper_budget_test", SCRIPTS / "run_global_postgres_stack.py")
    wrapper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wrapper)
    monkeypatch.setattr(wrapper, "_snapshot", lambda *args: pytest.fail("source opened after budget exhausted"))
    monkeypatch.setattr(sys, "argv", ["wrapper", "--source", str(tmp_path / "source"),
                                     "--expected-commit", "fixed", "--release", str(release),
                                     "--config", str(release / "individual-service.json")])
    assert wrapper.main() == 75
    assert "global_restart_budget_exhausted" in capsys.readouterr().out


def test_repeated_schema_failures_stop_before_fourth_preflight(tmp_path, monkeypatch):
    load_budget(tmp_path, monkeypatch)
    release = tmp_path / "runtime" / "releases" / "release"
    release.mkdir(parents=True)
    python = release / "Scripts" / "python.exe"
    python.parent.mkdir()
    python.write_bytes(b"fixture")
    monkeypatch.syspath_prepend(str(SCRIPTS))
    spec = importlib.util.spec_from_file_location("global_stack_wrapper_streak_test", SCRIPTS / "run_global_postgres_stack.py")
    wrapper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wrapper)
    preflights = []
    monkeypatch.setattr(wrapper, "_snapshot", lambda *args: preflights.append(1) or
                        (tmp_path / "source" / "Scripts" / "global_postgres_stack.py"))
    monkeypatch.setattr(wrapper, "_profile", lambda *args: (python, {"DEVCORE_LOCAL_ROOT": str(tmp_path / "local")}))
    monkeypatch.setattr(wrapper, "_check_schema", lambda *args: (1, "schema unavailable", 1))
    monkeypatch.setattr(sys, "argv", ["wrapper", "--source", str(tmp_path / "source"),
                                     "--expected-commit", "fixed", "--release", str(release),
                                     "--config", str(release / "individual-service.json")])
    for _ in range(3):
        assert wrapper.main() == 1
    assert len(preflights) == 3
    assert wrapper.main() == 75
    assert len(preflights) == 3
    state = json.loads((tmp_path / "runtime" / "state" / "local" / "GlobalStack" /
                        "restart-budget.json").read_text())
    assert state["exhausted"] is True
    assert state["alert"]["code"] == "global_restart_budget_exhausted"


def test_operator_reset_requires_profile_and_reason(tmp_path, monkeypatch, capsys):
    budget = load_budget(tmp_path, monkeypatch)
    for at in (1000, 1300, 1600):
        budget.record_failure(started_at=at - 1, finished_at=at, phase="supervisor")
    release = tmp_path / "runtime" / "releases" / "release"
    target = release.parent.parent / "state" / "local" / "GlobalStack"
    target.mkdir(parents=True)
    (target / "restart-budget.json").write_bytes(budget.path.read_bytes())
    monkeypatch.syspath_prepend(str(SCRIPTS))
    spec = importlib.util.spec_from_file_location("global_stack_wrapper_reset_test", SCRIPTS / "run_global_postgres_stack.py")
    wrapper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wrapper)
    checked = []
    monkeypatch.setattr(wrapper, "_profile", lambda *args: checked.append(1) or
                        (release / "Scripts" / "python.exe", {}))
    monkeypatch.setattr(sys, "argv", ["wrapper", "--source", str(tmp_path / "source"),
                                     "--expected-commit", "fixed", "--release", str(release),
                                     "--config", str(release / "individual-service.json"),
                                     "--reset-restart-budget", "--reason", "verified by operator"])
    assert wrapper.main() == 0
    assert checked == [1]
    assert json.loads(capsys.readouterr().out)["budget"]["exhausted"] is False
