"""Shared probe scheduling and local SQLite WAL metadata contract."""
import asyncio
import importlib.util
import os
from pathlib import Path
import sys
import threading

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from dashboard.input_watcher import InputWatcher, ProbeCooldownError, ProbeTimeoutError


def test_twenty_subscribers_share_one_probe_and_cached_revision():
    async def scenario():
        watcher = InputWatcher(interval=60)
        started, release = threading.Event(), threading.Event()
        calls = []
        def probe():
            calls.append(1)
            started.set()
            assert release.wait(3)
            return ('same',)
        tasks = [asyncio.create_task(watcher.revision(probe)) for _ in range(20)]
        assert await asyncio.to_thread(started.wait, 3)
        await asyncio.sleep(0.01)
        tasks[0].cancel()
        with pytest.raises(asyncio.CancelledError):
            await tasks[0]
        release.set()
        assert await asyncio.gather(*tasks[1:]) == [1] * 19
        assert await watcher.revision(probe) == 1
        assert calls == [1]
    asyncio.run(scenario())


@pytest.mark.parametrize('timeout', [0, -1, True, None, float('nan'), float('inf'), '5'])
def test_invalid_wait_deadline_rejected(timeout):
    with pytest.raises(ValueError, match='timeout'):
        InputWatcher(timeout=timeout)


def test_blocked_probe_times_out_waiters_without_restarting_thread_or_blocking_other_work():
    async def scenario():
        watcher = InputWatcher(interval=60, timeout=0.05)
        started, release = threading.Event(), threading.Event()
        calls = []
        def probe():
            calls.append(1)
            started.set()
            assert release.wait(3)
            return 'recovered'
        waiters = [asyncio.create_task(watcher.snapshot(probe)) for _ in range(20)]
        try:
            assert await asyncio.to_thread(started.wait, 3)
            other = InputWatcher(timeout=1)
            assert await other.snapshot(lambda: 'other-project') == (1, 'other-project')
            results = await asyncio.wait_for(asyncio.gather(*waiters, return_exceptions=True), 1)
            assert all(isinstance(result, ProbeTimeoutError) for result in results)
            results = await asyncio.wait_for(asyncio.gather(
                *(watcher.snapshot(probe) for _ in range(20)), return_exceptions=True), 1)
            assert all(isinstance(result, ProbeTimeoutError) for result in results)
            assert calls == [1]
            release.set()
            assert await watcher.snapshot(probe) == (1, 'recovered')
            assert calls == [1]
        finally:
            release.set()
            await asyncio.gather(*waiters, return_exceptions=True)
    asyncio.run(scenario())


def test_probe_own_timeout_is_preserved_and_does_not_become_wait_deadline():
    async def scenario():
        watcher = InputWatcher(interval=0, timeout=1)
        def probe():
            raise TimeoutError('OS fixture deadline')
        with pytest.raises(TimeoutError, match='OS fixture deadline') as error:
            await watcher.snapshot(probe)
        assert not isinstance(error.value, ProbeTimeoutError)
        assert await watcher.snapshot(lambda: 'recovered') == (1, 'recovered')
    asyncio.run(scenario())


def test_equal_signature_keeps_revision_decrease_or_removal_advances_it():
    async def scenario():
        watcher = InputWatcher(interval=0)
        for signature, expected in [(100, 1), (100, 1), (50, 2), (None, 3)]:
            assert await watcher.revision(lambda: signature) == expected
    asyncio.run(scenario())


def test_shared_snapshot_returns_value_and_revision_despite_waiter_cancellation():
    async def scenario():
        watcher = InputWatcher(interval=60)
        started, release = threading.Event(), threading.Event()
        calls = []
        def probe():
            calls.append(1)
            started.set()
            assert release.wait(3)
            return 'snapshot:' + 'a' * 32
        tasks = [asyncio.create_task(watcher.snapshot(probe)) for _ in range(20)]
        assert await asyncio.to_thread(started.wait, 3)
        tasks[0].cancel()
        with pytest.raises(asyncio.CancelledError):
            await tasks[0]
        release.set()
        expected = (1, 'snapshot:' + 'a' * 32)
        assert await asyncio.gather(*tasks[1:]) == [expected] * 19
        assert await watcher.snapshot(probe) == expected
        assert calls == [1]
    asyncio.run(scenario())


def test_snapshot_failure_and_none_do_not_confuse_revision():
    watcher = InputWatcher(interval=0)
    async def scenario():
        assert await watcher.snapshot(lambda: None) == (1, None)
        def failure():
            raise OSError('fixture failed')
        with pytest.raises(OSError):
            await watcher.snapshot(failure)
        assert await watcher.snapshot(lambda: None) == (1, None)
        assert await watcher.snapshot(lambda: 'B') == (2, 'B')
    asyncio.run(scenario())
    # A new event loop owns an independent baseline, not the previous value.
    assert asyncio.run(watcher.snapshot(lambda: 'C')) == (1, 'C')


def test_probe_failure_does_not_cache_a_sample_or_advance_revision():
    async def scenario():
        watcher = InputWatcher(interval=0)
        assert await watcher.revision(lambda: 'previous') == 1
        def failure():
            raise OSError('fixture input unavailable')
        with pytest.raises(OSError):
            await watcher.revision(failure)
        assert await watcher.revision(lambda: 'previous') == 1
        assert await watcher.revision(lambda: 'next') == 2
    asyncio.run(scenario())


@pytest.mark.parametrize('has_previous', [False, True])
def test_failed_shared_probe_throttles_later_subscribers_without_returning_old_value(has_previous):
    async def scenario():
        watcher = InputWatcher(interval=0)
        if has_previous:
            assert await watcher.snapshot(lambda: 'A') == (1, 'A')
        calls = []
        def failure():
            calls.append(1)
            raise OSError('x' * 2000)
        # First failure is not suppressed by a successful sample's interval.
        with pytest.raises(OSError):
            await watcher.snapshot(failure)
        watcher.interval = 60
        for _ in range(100):
            with pytest.raises(ProbeCooldownError) as error:
                await watcher.snapshot(failure)
            assert len(str(error.value)) == 1024
        # Both views of the sample refuse to return the previous good value.
        with pytest.raises(ProbeCooldownError):
            await watcher.revision(failure)
        assert calls == [1]
        watcher.interval = 0  # Permit next retry deterministically.
        assert await watcher.snapshot(lambda: 'B') == (2 if has_previous else 1, 'B')
        watcher.interval = 60
        assert await watcher.snapshot(lambda: pytest.fail('unexpected new probe')) == (2 if has_previous else 1, 'B')
    asyncio.run(scenario())


def test_failure_interval_expires_and_twenty_waiters_share_retry():
    async def scenario():
        watcher = InputWatcher(interval=0.05)
        calls = []
        def probe():
            calls.append(1)
            if len(calls) == 1:
                raise OSError('fixture unavailable')
            return 'recovered'
        with pytest.raises(OSError):
            await watcher.snapshot(probe)
        with pytest.raises(ProbeCooldownError):
            await watcher.snapshot(probe)
        await asyncio.sleep(0.06)
        results = await asyncio.gather(*(watcher.snapshot(probe) for _ in range(20)))
        assert results == [(1, 'recovered')] * 20
        assert calls == [1, 1]
    asyncio.run(scenario())


def test_probe_tracks_wal_size_even_with_unchanged_timestamp_and_missing_file(tmp_path, monkeypatch):
    for name in ('DEVCORE_LOCAL_ROOT', 'DEVCORE_DATA_ROOT', 'DEVCORE_PLATFORM_ROOT'):
        monkeypatch.setenv(name, str(tmp_path / name))
    spec = importlib.util.spec_from_file_location('input_watcher_api_fixture', Path(__file__).with_name('dashboard_api.py'))
    api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api)
    monkeypatch.setattr(api.subprocess, 'run', lambda *args, **kwargs: pytest.fail('watcher launched subprocess'))
    baseline = api.get_dashboard_input_signature()
    wal = api.get_local_path('devcore.db-wal')
    wal.parent.mkdir(parents=True)
    wal.write_bytes(b'fixture')
    os.utime(wal, ns=(1000000000, 1000000000))
    created = api.get_dashboard_input_signature()
    wal.write_bytes(b'fixture appended')
    os.utime(wal, ns=(1000000000, 1000000000))
    appended = api.get_dashboard_input_signature()
    wal.unlink()
    assert baseline != created != appended
    assert api.get_dashboard_input_signature() == baseline
    wal.mkdir()
    with pytest.raises(RuntimeError, match='regular file'):
        api.get_dashboard_input_signature()
