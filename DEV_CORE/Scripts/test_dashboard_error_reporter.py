"""Repeated storage faults must not log once per connected subscriber."""
import asyncio
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from dashboard.error_reporter import SseErrorReporter


@pytest.mark.parametrize('interval', [0, -1, True, None, float('nan'), float('inf'), '30'])
def test_invalid_interval_refused(interval):
    with pytest.raises(ValueError):
        SseErrorReporter(interval=interval)


def test_burst_is_coalesced_and_next_message_reports_suppression(monkeypatch):
    messages = []
    reporter = SseErrorReporter(interval=30, emit=messages.append)
    async def scenario():
        clock = [100.0]
        monkeypatch.setattr(asyncio.get_running_loop(), 'time', lambda: clock[0])
        assert reporter.report('loop', OSError('first')) is True
        for _ in range(99):
            assert reporter.report('loop', OSError('repeated')) is False
        assert len(messages) == 1
        # Distinct producer diagnostics get their own bounded slot.
        assert reporter.report('cache', OSError('producer')) is True
        clock[0] += 30
        assert reporter.report('loop', OSError('still failing')) is True
        assert 'suppressed=99' in messages[-1]
    asyncio.run(scenario())


def test_diagnostic_is_bounded_single_line_and_new_loop_is_independent():
    messages = []
    reporter = SseErrorReporter(emit=messages.append)
    async def scenario():
        assert reporter.report('loop', OSError('\r\n' * 2000)) is True
        assert len(messages[-1]) < 2200
        assert '\n' not in messages[-1] and '\r' not in messages[-1]
        assert reporter.report('loop', OSError('again')) is False
        with pytest.raises(ValueError):
            reporter.report('arbitrary-user-key', OSError('no'))
    asyncio.run(scenario())
    asyncio.run(scenario())
    assert len(messages) == 2


def test_broken_sink_does_not_replace_recovery_error():
    def broken(_):
        raise OSError('stdout unavailable')
    async def scenario():
        reporter = SseErrorReporter(emit=broken)
        assert reporter.report('loop', OSError('storage error')) is False
        assert reporter.report('loop', OSError('storage error')) is False
    asyncio.run(scenario())
