"""Atomic usage updates on temporary files; failure preserves the snapshot."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import threading
import os
import subprocess

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Scripts'))
from router import providers, stats_store


def test_alert_failure_after_commit_does_not_repeat_usage(monkeypatch, tmp_path, capsys):
    path = tmp_path / 'stats.json'
    monkeypatch.setattr(providers, 'STATS_PATH', path)
    def refuse_alert(*args):
        raise RuntimeError('PRIVATE alert details')
    monkeypatch.setattr(providers, 'check_and_trigger_alerts', refuse_alert)
    assert providers.record_tokens('T-1', 'summary', 7, 3) is True
    stats = stats_store.read_stats(path)
    assert stats['total_tokens'] == 10 and stats['tasks']['T-1']['calls'] == 1
    assert 'PRIVATE' not in capsys.readouterr().err


def test_failed_atomic_replace_preserves_old_bytes_and_cleans_temp(monkeypatch, tmp_path):
    path = tmp_path / 'stats.json'
    stats_store.update_stats(path, 'T-1', 'summary', 7, 3)
    previous = path.read_bytes()
    original = stats_store.os.replace
    def refuse(*args):
        raise PermissionError('fixture')
    monkeypatch.setattr(stats_store.os, 'replace', refuse)
    with pytest.raises(PermissionError):
        stats_store.update_stats(path, 'T-1', 'summary', 7, 3)
    assert path.read_bytes() == previous and list(tmp_path.glob('*.tmp')) == []
    monkeypatch.setattr(stats_store.os, 'replace', original)
    stats_store.update_stats(path, 'T-1', 'summary', 7, 3)
    assert stats_store.read_stats(path)['tasks']['T-1']['calls'] == 2


@pytest.mark.parametrize('raw', [b'{PRIVATE', b'[]', b'x' * (stats_store.MAX_BYTES + 1),
    b'{"tasks":{},"total_tokens":1}'], ids=['syntax', 'root', 'oversized', 'inconsistent'])
def test_invalid_or_oversized_snapshot_is_preserved(monkeypatch, tmp_path, capsys, raw):
    path = tmp_path / 'stats.json'
    path.write_bytes(raw)
    monkeypatch.setattr(providers, 'STATS_PATH', path)
    assert providers.record_tokens('T-1', 'summary', 7, 3) is False
    assert path.read_bytes() == raw and not providers.has_budget_alert('T-1')
    assert 'PRIVATE' not in capsys.readouterr().err


def test_concurrent_writer_refuses_without_waiting_and_readers_see_old_snapshot(monkeypatch, tmp_path):
    path = tmp_path / 'stats.json'
    stats_store.update_stats(path, 'T-1', 'summary', 1, 1)
    entered, release = threading.Event(), threading.Event()
    original = stats_store.os.replace
    def pause_replace(*args):
        entered.set()
        assert release.wait(5)
        return original(*args)
    monkeypatch.setattr(stats_store.os, 'replace', pause_replace)
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending = pool.submit(stats_store.update_stats, path, 'T-1', 'summary', 7, 3)
        try:
            assert entered.wait(5)
            assert stats_store.read_stats(path)['total_tokens'] == 2
            competing = pool.submit(stats_store.update_stats, path, 'T-2', 'summary', 7, 3)
            with pytest.raises(ValueError, match='busy'):
                competing.result(timeout=1)
        finally:
            release.set()
        assert pending.result(timeout=5) == 12
    assert stats_store.read_stats(path)['tasks']['T-1']['calls'] == 2


def test_task_capacity_and_counter_overflow_leave_snapshot_unchanged(monkeypatch, tmp_path):
    path = tmp_path / 'stats.json'
    monkeypatch.setattr(stats_store, 'MAX_TASKS', 1)
    stats_store.update_stats(path, 'T-1', 'summary', 1, 1)
    previous = path.read_bytes()
    for args in [('T-2', 'summary', 1, 1), ('T-1', 'summary', stats_store.MAX_COUNTER, 1)]:
        with pytest.raises(ValueError):
            stats_store.update_stats(path, *args)
        assert path.read_bytes() == previous


@pytest.mark.parametrize('stop', ['exit', 'crash'])
def test_other_process_lock_refuses_update_and_os_releases_after_stop(tmp_path, stop):
    path = tmp_path / 'stats.json'
    stats_store.update_stats(path, 'T-1', 'summary', 1, 1)
    previous = path.read_bytes()
    script = """import sys
from router.stats_store import usage_file_lock
with usage_file_lock(sys.argv[1]):
    print('locked', flush=True)
    sys.stdin.readline()
"""
    env = dict(os.environ)
    env['PYTHONPATH'] = str(Path(__file__).resolve().parents[1] / 'Scripts')
    env['DEVCORE_LOCAL_ROOT'] = str(tmp_path / 'local')
    env['DEVCORE_DATA_ROOT'] = str(tmp_path / 'data')
    env['DEVCORE_PLATFORM_ROOT'] = str(tmp_path / 'platform')
    process = subprocess.Popen([sys.executable, '-c', script, str(path)], env=env,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        pool = ThreadPoolExecutor(max_workers=1)
        try:
            assert pool.submit(process.stdout.readline).result(timeout=5).strip() == 'locked'
        finally:
            pool.shutdown(wait=False, cancel_futures=True)
        with pytest.raises(ValueError, match='busy'):
            stats_store.update_stats(path, 'T-1', 'summary', 7, 3)
        assert path.read_bytes() == previous
        if stop == 'crash':
            process.kill()  # Only the fixture process created immediately above.
        else:
            process.stdin.close()
        process.wait(timeout=5)
        stats_store.update_stats(path, 'T-1', 'summary', 7, 3)
        assert stats_store.read_stats(path)['total_tokens'] == 12
        assert stats_store.read_stats(path)['tasks']['T-1']['calls'] == 2
        assert path.with_name(path.name + '.lock').exists()
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream and not stream.closed:
                stream.close()
