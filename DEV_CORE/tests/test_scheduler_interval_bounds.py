"""Invalid durations fail before execution; interval planning does not enumerate gaps."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Scheduler'))
import scheduler_contract as contract
import scheduler_tick


def job(expr='1', policy='skip', last=None):
    return contract.SchedulerJob(id='fixture', name='fixture', timezone='UTC', policy=policy,
        schedule={'kind': 'interval', 'expr': expr}, command={'type': 'python', 'path': 'unused'},
        state={'last_run_at': last.isoformat() if last else None})


@pytest.mark.parametrize('expr', ['0', '-1', '1.5', 'broken', '525601', '9' * 65])
def test_invalid_interval_refused_at_model_boundary(expr):
    with pytest.raises(ValueError, match='Interval must'):
        job(expr)


@pytest.mark.parametrize('value', [0, -1, True, 525601])
def test_direct_missed_slot_helper_rejects_invalid_interval(value):
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError, match='Interval must'):
        contract.get_missed_interval_slots(value, now, now, 'UTC')


def test_mutated_interval_is_revalidated_at_calculation():
    fixture = job()
    fixture.schedule.expr = '0'
    with pytest.raises(ValueError, match='Interval must'):
        contract.compute_next_run(fixture, datetime.now(timezone.utc))


@pytest.mark.parametrize('policy,expected', [('skip', 1), ('run_once', 0), ('catch_up', -43199)])
def test_huge_gap_uses_bounded_arithmetic_not_slot_enumeration(monkeypatch, policy, expected):
    now = datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc)
    fixture = job(policy=policy, last=datetime(1900, 1, 1, tzinfo=timezone.utc))
    monkeypatch.setattr(contract, 'get_missed_interval_slots', lambda *a: pytest.fail('No gap enumeration'))
    assert contract.compute_next_run(fixture, now) == now + timedelta(minutes=expected)


def test_run_once_returns_latest_slot_beyond_1000_missed_occurrences():
    now = datetime(2026, 10, 4, 12, 0, 30, tzinfo=timezone.utc)
    last = now - timedelta(days=2, seconds=30)
    assert contract.compute_next_run(job(policy='run_once', last=last), now) == now - timedelta(seconds=30)


@pytest.mark.parametrize('policy', ['skip', 'run_once', 'catch_up'])
def test_future_last_run_keeps_future_slot(policy):
    now = datetime(2026, 10, 4, tzinfo=timezone.utc)
    last = now + timedelta(hours=1)
    assert contract.compute_next_run(job('60', policy, last), now) == last + timedelta(hours=1)


def test_invalid_due_registry_refused_before_command(tmp_path, monkeypatch, caplog):
    class EndFixtureLoop(BaseException):
        pass
    fixture = job().model_dump(by_alias=True)
    fixture['schedule']['expr'] = '0'
    fixture['state']['next_run_at'] = datetime.now(timezone.utc).isoformat()
    path = tmp_path / 'jobs.json'
    original = json.dumps([fixture]).encode()
    path.write_bytes(original)
    monkeypatch.setattr(scheduler_tick, 'execute_job_command', lambda *a: pytest.fail('Invalid registry must not execute'))
    def stop(seconds):
        raise EndFixtureLoop()
    monkeypatch.setattr(scheduler_tick.time, 'sleep', stop)
    with pytest.raises(EndFixtureLoop):
        scheduler_tick.main_loop(tmp_path / 'scheduler.db', path, tmp_path / 'scheduler.lock')
    assert path.read_bytes() == original and 'Interval must' in caplog.text
