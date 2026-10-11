"""Only short-lived fixture children; no active services or job registry."""
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

SCHEDULER = Path(__file__).resolve().parents[1] / "Scheduler"
sys.path.insert(0, str(SCHEDULER))
import scheduler_tick
from scheduler_contract import SchedulerJobCommand

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows Job Object acceptance")


def exited(pid):
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    api.OpenProcess.restype = wintypes.HANDLE
    api.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    api.WaitForSingleObject.restype = wintypes.DWORD
    api.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = api.OpenProcess(0x100000, False, pid)  # SYNCHRONIZE, no mutation.
    if not handle:
        return ctypes.get_last_error() == 87  # PID no longer exists.
    try:
        return api.WaitForSingleObject(handle, 3000) == 0
    finally:
        api.CloseHandle(handle)


def spawn_code(pid_file):
    return "import subprocess,sys;from pathlib import Path;p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)']);Path(" + repr(str(pid_file)) + ").write_text(str(p.pid));import time;time.sleep(30)"


def test_timeout_terminates_real_grandchild(tmp_path):
    pid_file = tmp_path / "child.pid"
    command = SchedulerJobCommand(type="python", path="-c", args=[spawn_code(pid_file)])
    started = time.monotonic()
    code, stdout, stderr = scheduler_tick.execute_job_command(command, timeout=2)
    assert code == -9 and "timed out" in stderr
    assert time.monotonic() - started < 7
    assert pid_file.exists()
    assert exited(int(pid_file.read_text()))


def test_assignment_failure_prevents_command_execution(tmp_path, monkeypatch):
    marker = tmp_path / "must-not-exist"
    def deny(self, pid):
        raise OSError("fixture containment denied")
    monkeypatch.setattr(scheduler_tick.WindowsJob, "assign", deny)
    command = SchedulerJobCommand(type="python", path="-c",
        args=["from pathlib import Path;Path(" + repr(str(marker)) + ").write_text('ran')"])
    code, _, error = scheduler_tick.execute_job_command(command, timeout=2)
    assert code == -1 and "containment denied" in error
    assert not marker.exists()


def test_parent_crash_closes_job_and_terminates_descendants(tmp_path):
    pid_file = tmp_path / "child.pid"
    worker = tmp_path / "worker.py"
    worker.write_text("""import sys,subprocess,time,os
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from windows_job import WindowsJob
job=WindowsJob()
p=subprocess.Popen([sys.executable,str(Path(sys.argv[1])/'run_job.py'),'--devcore-gated','python','-c',sys.argv[3]],stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
job.assign(p.pid)
p.stdin.write('START\\n');p.stdin.flush()
deadline=time.monotonic()+5
while not Path(sys.argv[2]).exists() and time.monotonic()<deadline: time.sleep(.02)
os._exit(0 if Path(sys.argv[2]).exists() else 1)
""", encoding="utf-8")
    result = subprocess.run([sys.executable, "-I", str(worker), str(SCHEDULER),
        str(pid_file), spawn_code(pid_file)], capture_output=True, text=True, timeout=8)
    assert result.returncode == 0, result.stderr
    assert exited(int(pid_file.read_text()))


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), 3601])
def test_invalid_timeout_rejected_before_launch(monkeypatch, timeout):
    monkeypatch.setattr(scheduler_tick.subprocess, "Popen", lambda *a, **k: pytest.fail("No launch"))
    with pytest.raises(ValueError):
        scheduler_tick.execute_job_command(SchedulerJobCommand(type="python", path="-c", args=[]), timeout)


@pytest.mark.parametrize("stream", ["stdout", "stderr"])
def test_output_flood_is_bounded_and_terminates_descendants(tmp_path, stream):
    pid_file = tmp_path / "child.pid"
    script = spawn_code(pid_file).rsplit(";import time;time.sleep(30)", 1)[0] + \
        f";sys.{stream}.buffer.write(b'x'*2097152);sys.{stream}.flush();import time;time.sleep(30)"
    command = SchedulerJobCommand(type="python", path="-c", args=[script])
    started = time.monotonic()
    code, out, err = scheduler_tick.execute_job_command(command, timeout=8, output_limit=65536)
    assert code == -10 and "output exceeded" in err
    assert len(out.encode()) <= 65536
    assert len(err.encode()) <= 65536 + 100
    assert time.monotonic() - started < 7
    assert exited(int(pid_file.read_text()))


def test_both_streams_are_drained_without_deadlock():
    script = "import sys;sys.stdout.buffer.write(b'A'*4096);sys.stderr.buffer.write(b'B'*4096)"
    command = SchedulerJobCommand(type="python", path="-c", args=[script])
    code, out, err = scheduler_tick.execute_job_command(command, timeout=3, output_limit=8192)
    assert code == 0 and "A" * 4096 in out and err == "B" * 4096


@pytest.mark.parametrize("limit", [0, -1, True, 16777217])
def test_invalid_output_limit_rejected_before_launch(monkeypatch, limit):
    monkeypatch.setattr(scheduler_tick.subprocess, "Popen", lambda *a, **k: pytest.fail("No launch"))
    with pytest.raises(ValueError):
        scheduler_tick.execute_job_command(SchedulerJobCommand(type="python", path="-c", args=[]), output_limit=limit)


def test_slow_job_creation_spends_deadline_before_process_launch(monkeypatch):
    from types import SimpleNamespace
    closed = []
    def slow():
        time.sleep(.05)
        return SimpleNamespace(close=lambda: closed.append(True))
    monkeypatch.setattr(scheduler_tick, "WindowsJob", slow)
    monkeypatch.setattr(scheduler_tick.subprocess, "Popen", lambda *a, **k: pytest.fail("Expired startup must not launch"))
    command = SchedulerJobCommand(type="python", path="-c", args=[])
    code, _, error = scheduler_tick.execute_job_command(command, timeout=.02)
    assert code == -9 and "startup" in error and closed == [True]


def test_slow_assignment_does_not_open_execution_gate(tmp_path, monkeypatch):
    original = scheduler_tick.WindowsJob.assign
    marker = tmp_path / "must-not-run"
    def slow(self, pid):
        original(self, pid)
        time.sleep(.2)
    monkeypatch.setattr(scheduler_tick.WindowsJob, "assign", slow)
    command = SchedulerJobCommand(type="python", path="-c",
        args=["from pathlib import Path;Path(" + repr(str(marker)) + ").write_text('ran')"])
    code, _, error = scheduler_tick.execute_job_command(command, timeout=.1)
    assert code == -9 and "startup" in error
    assert not marker.exists()
