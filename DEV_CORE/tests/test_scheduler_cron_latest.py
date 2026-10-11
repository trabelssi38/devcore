"""run_once selects the latest bounded occurrence without a truncated list."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Scheduler'))
import scheduler_contract as contract


NOW = datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc)


def job(expr='* * * * *', last=None):
    return contract.SchedulerJob(id='fixture', name='fixture', timezone='UTC', policy='run_once',
        schedule={'kind': 'cron', 'expr': expr}, command={'type': 'python', 'path': 'unused'},
        state={'last_run_at': last.isoformat() if last else None})


@pytest.mark.parametrize('seconds,expected_seconds', [(0, 0), (30, 0), (59, 0)])
def test_latest_of_thousands_of_missed_slots(monkeypatch, seconds, expected_seconds):
    fixture = job(last=NOW - timedelta(days=2))
    monkeypatch.setattr(contract, 'get_missed_cron_slots', lambda *a: pytest.fail('No enumeration'))
    assert contract.compute_next_run(fixture, NOW + timedelta(seconds=seconds)) == NOW + timedelta(seconds=expected_seconds)


def test_seconds_cron_includes_exact_boundary_without_enumeration(monkeypatch):
    fixture = job('* * * * * *', NOW - timedelta(days=1))
    monkeypatch.setattr(contract, 'get_missed_cron_slots', lambda *a: pytest.fail('No enumeration'))
    assert contract.compute_next_run(fixture, NOW + timedelta(seconds=17)) == NOW + timedelta(seconds=17)


@pytest.mark.parametrize('last,expected', [(NOW, NOW + timedelta(minutes=1)),
    (NOW + timedelta(hours=1), NOW + timedelta(hours=1, minutes=1))])
def test_last_applied_or_future_slot_not_returned_again(last, expected):
    assert contract.compute_next_run(job(last=last), NOW) == expected


def test_old_last_run_with_no_slot_in_window_returns_future_not_old_year():
    fixture = job('0 0 1 1 *', NOW - timedelta(days=700))
    assert contract.compute_next_run(fixture, NOW) == datetime(2027, 1, 1, tzinfo=timezone.utc)


def test_explicit_future_year_without_previous_match_is_supported():
    fixture = job('0 0 1 1 * 0 2027', NOW - timedelta(days=1))
    assert contract.compute_next_run(fixture, NOW) == datetime(2027, 1, 1, tzinfo=timezone.utc)


def test_old_last_run_still_uses_30_day_window():
    assert contract.compute_next_run(job(last=NOW - timedelta(days=700)), NOW) == NOW


def test_no_history_schedules_future_occurrence():
    assert contract.compute_next_run(job(), NOW) == NOW + timedelta(minutes=1)
