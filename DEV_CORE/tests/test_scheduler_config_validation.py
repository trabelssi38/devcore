"""Reject invalid scheduling metadata before commands or registry publication."""
from datetime import datetime, timezone
from pathlib import Path
import json
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Scheduler'))
import scheduler_contract as contract
import scheduler_tick
import scheduler_sync


def fixture_job():
    return {'id': 'fixture', 'name': 'fixture', 'timezone': 'UTC',
        'schedule': {'kind': 'cron', 'expr': '* * * * *'},
        'command': {'type': 'python', 'path': 'unused'},
        'state': {'next_run_at': datetime.now(timezone.utc).isoformat()}}


@pytest.mark.parametrize('changes', [
    {'schedule': {'kind': 'unknown', 'expr': '1'}},
    {'schedule': {'kind': 'cron', 'expr': '61 * * * *'}},
    {'schedule': {'kind': 'cron', 'expr': 'x' * 257}},
    {'schedule': {'kind': 'once', 'expr': 'invalid'}},
    {'policy': 'unknown'}, {'timezone': 'Unknown/Fixture'},
    {'state': {'last_run_at': 'broken'}}, {'state': {'next_run_at': 'broken'}},
    {'state': {'completed': -1}}, {'state': {'completed': True}},
])
def test_invalid_registry_preserved_before_execution(tmp_path, monkeypatch, caplog, changes):
    class EndFixtureLoop(BaseException):
        pass
    data = dict(fixture_job(), **changes)
    path = tmp_path / 'jobs.json'
    original = json.dumps([data]).encode()
    path.write_bytes(original)
    monkeypatch.setattr(scheduler_tick, 'execute_job_command', lambda *a: pytest.fail('Invalid metadata must not execute'))
    def stop(seconds):
        raise EndFixtureLoop()
    monkeypatch.setattr(scheduler_tick.time, 'sleep', stop)
    with pytest.raises(EndFixtureLoop):
        scheduler_tick.main_loop(tmp_path / 'scheduler.db', path, tmp_path / 'scheduler.lock')
    assert path.read_bytes() == original and 'Error loading jobs.json' in caplog.text


def test_invalid_static_definition_does_not_replace_registry(tmp_path):
    platform = tmp_path / 'platform'
    local = tmp_path / 'local'
    (platform / 'Scheduler').mkdir(parents=True)
    (local / 'Scheduler').mkdir(parents=True)
    data = fixture_job()
    data['policy'] = 'broken'
    (platform / 'Scheduler/jobs.devcore.json').write_text(json.dumps([data]))
    dynamic = local / 'Scheduler/jobs.json'
    dynamic.write_bytes(b'[ ]')
    assert scheduler_sync.sync_registry(platform, local) is False
    assert dynamic.read_bytes() == b'[ ]'


def test_missing_croniter_never_becomes_empty_schedule(monkeypatch):
    fixture = contract.SchedulerJob(**fixture_job())
    monkeypatch.setattr(contract, 'HAS_CRONITER', False)
    with pytest.raises(ValueError, match='Cron requires'):
        contract.SchedulerJob(**fixture_job())
    with pytest.raises(ValueError, match='Cron requires'):
        contract.compute_next_run(fixture, datetime.now(timezone.utc))


def test_sparse_cron_search_has_explicit_year_limit(monkeypatch):
    fixture = contract.SchedulerJob(**fixture_job())
    original = contract.croniter
    bounds = []
    def checked(*a, **kw):
        bounds.append(kw.get('max_years_between_matches'))
        return original(*a, **kw)
    monkeypatch.setattr(contract, 'croniter', checked)
    for policy in ('skip', 'run_once', 'catch_up'):
        fixture.policy = policy
        contract.compute_next_run(fixture, datetime.now(timezone.utc))
    assert bounds and set(bounds) == {8}


def test_naive_due_timestamp_is_interpreted_as_utc(tmp_path, monkeypatch):
    class EndFixtureLoop(BaseException):
        pass
    data = fixture_job()
    data['state']['next_run_at'] = '2020-01-01T00:00:00'
    path = tmp_path / 'jobs.json'
    path.write_text(json.dumps([data]))
    calls = []
    monkeypatch.setattr(scheduler_tick, 'execute_job_command', lambda *a: calls.append(1) or (0, '', ''))
    def stop(seconds):
        raise EndFixtureLoop()
    monkeypatch.setattr(scheduler_tick.time, 'sleep', stop)
    with pytest.raises(EndFixtureLoop):
        scheduler_tick.main_loop(tmp_path / 'scheduler.db', path, tmp_path / 'scheduler.lock')
    state = scheduler_tick.load_jobs(path)[0].state
    assert calls == [1] and state.last_run_at == '2020-01-01T00:00:00'


@pytest.mark.parametrize('scheduled', ['2020-01-01T00:00:00', '2020-01-01T01:00:00+01:00'])
def test_occurrence_key_not_changed_by_comparison_timezone(tmp_path, monkeypatch, scheduled):
    import scheduler_history
    class EndFixtureLoop(BaseException):
        pass
    data = fixture_job()
    data['state']['next_run_at'] = scheduled
    path = tmp_path / 'jobs.json'
    original = json.dumps([data]).encode()
    path.write_bytes(original)
    assert scheduler_history.record_run('fixture', scheduled, 'started', 0, 'running', db_path=tmp_path / 'scheduler.db')
    monkeypatch.setattr(scheduler_tick, 'execute_job_command', lambda *a: pytest.fail('Existing occurrence must not repeat'))
    def stop(seconds):
        raise EndFixtureLoop()
    monkeypatch.setattr(scheduler_tick.time, 'sleep', stop)
    with pytest.raises(EndFixtureLoop):
        scheduler_tick.main_loop(tmp_path / 'scheduler.db', path, tmp_path / 'scheduler.lock')
    assert path.read_bytes() == original
