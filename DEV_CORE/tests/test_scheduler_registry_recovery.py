"""Committed history must recover JSON state without repeating commands."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Scheduler'))
import scheduler_tick
import scheduler_history
from scheduler_contract import SchedulerJob, SchedulerJobCommand, SchedulerJobSchedule, SchedulerJobState


class EndFixtureLoop(BaseException):
    pass


def one_cycle(tmp_path, monkeypatch):
    def stop(seconds):
        raise EndFixtureLoop()
    monkeypatch.setattr(scheduler_tick.time, 'sleep', stop)
    with pytest.raises(EndFixtureLoop):
        scheduler_tick.main_loop(tmp_path / 'scheduler.db', tmp_path / 'jobs.json', tmp_path / 'scheduler.lock')
    # Separate daemon fixture: lease released explicitly, never active roots.
    (tmp_path / 'scheduler.lock').unlink()


def fixture_job(tmp_path, *, kind='once', already_applied=False):
    scheduled = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    job = SchedulerJob(id='fixture', name='fixture', timezone='UTC', policy='catch_up',
        schedule=SchedulerJobSchedule(kind=kind, expr=scheduled if kind == 'once' else '1'),
        command=SchedulerJobCommand(type='python', path='unused'),
        state=SchedulerJobState(next_run_at=scheduled, completed=4,
            last_run_at=scheduled if already_applied else None))
    scheduler_tick.save_jobs([job], tmp_path / 'jobs.json')
    return job, scheduled


@pytest.mark.parametrize('status,count', [('ok', 5), ('skipped', 4)])
def test_once_terminal_history_recovers_state_and_stops(tmp_path, monkeypatch, status, count):
    job, scheduled = fixture_job(tmp_path)
    path = tmp_path / 'scheduler.db'
    assert scheduler_history.record_run(job.id, scheduled, 'started', 2, status, db_path=path)
    monkeypatch.setattr(scheduler_tick, 'execute_job_command', lambda *a: pytest.fail('No repetition'))
    one_cycle(tmp_path, monkeypatch)
    state = scheduler_tick.load_jobs(tmp_path / 'jobs.json')[0].state
    assert state.next_run_at is None and state.last_run_at == scheduled
    assert state.completed_count == count and state.last_status == status
    one_cycle(tmp_path, monkeypatch)
    assert scheduler_tick.load_jobs(tmp_path / 'jobs.json')[0].state.completed_count == count


def test_already_applied_success_never_counts_twice(tmp_path, monkeypatch):
    job, scheduled = fixture_job(tmp_path, already_applied=True)
    assert scheduler_history.record_run(job.id, scheduled, 'started', 2, 'ok', db_path=tmp_path / 'scheduler.db')
    monkeypatch.setattr(scheduler_tick, 'execute_job_command', lambda *a: pytest.fail('No repetition'))
    one_cycle(tmp_path, monkeypatch)
    assert scheduler_tick.load_jobs(tmp_path / 'jobs.json')[0].state.completed_count == 4


def test_interval_catchup_bases_next_slot_on_recovered_occurrence(tmp_path, monkeypatch):
    job, scheduled = fixture_job(tmp_path, kind='interval')
    assert scheduler_history.record_run(job.id, scheduled, 'started', 2, 'ok', db_path=tmp_path / 'scheduler.db')
    monkeypatch.setattr(scheduler_tick, 'execute_job_command', lambda *a: pytest.fail('No repetition'))
    one_cycle(tmp_path, monkeypatch)
    state = scheduler_tick.load_jobs(tmp_path / 'jobs.json')[0].state
    assert datetime.fromisoformat(state.next_run_at) == datetime.fromisoformat(scheduled) + timedelta(minutes=1)
    assert state.completed_count == 5


def test_success_then_failed_json_publication_recovers_once(tmp_path, monkeypatch, caplog):
    job, scheduled = fixture_job(tmp_path)
    initial = (tmp_path / 'jobs.json').read_bytes()
    executions = []
    monkeypatch.setattr(scheduler_tick, 'execute_job_command', lambda *a: executions.append(1) or (0, '', ''))
    original = scheduler_tick.save_jobs
    def fail(*a):
        raise OSError('fixture publication failure')
    monkeypatch.setattr(scheduler_tick, 'save_jobs', fail)
    one_cycle(tmp_path, monkeypatch)
    assert 'fixture publication failure' in caplog.text
    assert (tmp_path / 'jobs.json').read_bytes() == initial
    assert scheduler_history.is_run_completed(job.id, scheduled, tmp_path / 'scheduler.db')
    monkeypatch.setattr(scheduler_tick, 'save_jobs', original)
    one_cycle(tmp_path, monkeypatch)
    one_cycle(tmp_path, monkeypatch)
    state = scheduler_tick.load_jobs(tmp_path / 'jobs.json')[0].state
    assert executions == [1] and state.completed_count == 5
    assert state.last_run_at == scheduled and state.next_run_at is None
    with sqlite3.connect(tmp_path / 'scheduler.db') as conn:
        assert conn.execute('SELECT count(*) FROM run_history').fetchone()[0] == 1


def test_missing_result_after_completion_check_preserves_registry(tmp_path, monkeypatch, caplog):
    job, scheduled = fixture_job(tmp_path)
    assert scheduler_history.record_run(job.id, scheduled, 'started', 2, 'ok', db_path=tmp_path / 'scheduler.db')
    initial = (tmp_path / 'jobs.json').read_bytes()
    monkeypatch.setattr(scheduler_history, 'get_completed_result', lambda *a: None)
    monkeypatch.setattr(scheduler_tick, 'execute_job_command', lambda *a: pytest.fail('No repetition'))
    one_cycle(tmp_path, monkeypatch)
    assert 'completed result unavailable' in caplog.text
    assert (tmp_path / 'jobs.json').read_bytes() == initial
