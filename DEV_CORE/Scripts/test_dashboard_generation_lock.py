"""Kernel-lock lifetime tested with isolated roots and owned child processes."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

SCRIPTS = Path(__file__).parent


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    for name in ('DEVCORE_LOCAL_ROOT', 'DEVCORE_DATA_ROOT', 'DEVCORE_PLATFORM_ROOT'):
        monkeypatch.setenv(name, str(tmp_path / name))
    return load_module(SCRIPTS / 'dashboard' / 'generation_lock.py', 'lock_fixture')


def test_exception_releases_lock_and_retains_file(runtime):
    lock = runtime.DashboardLock(wait_timeout=0)
    with pytest.raises(ValueError, match='fixture failed'):
        with lock:
            with pytest.raises(TimeoutError):
                with runtime.DashboardLock(wait_timeout=0):
                    pytest.fail('second writer entered')
            raise ValueError('fixture failed')
    assert lock.lock_path.exists()
    with runtime.DashboardLock(wait_timeout=0):
        pass
    lock.__exit__()  # Repeated cleanup must not unlock a new holder.


@pytest.mark.parametrize('kill_holder', [False, True])
def test_live_old_holder_is_not_stolen_and_process_exit_releases(runtime, tmp_path, kill_holder):
    marker = tmp_path / 'ready'
    env = os.environ.copy()
    env['PYTHONPATH'] = str(SCRIPTS) + os.pathsep + env.get('PYTHONPATH', '')
    program = "from dashboard.generation_lock import DashboardLock; from pathlib import Path; import sys\nwith DashboardLock(wait_timeout=0):\n Path(sys.argv[1]).write_text('ready')\n sys.stdin.readline()"
    holder = subprocess.Popen([sys.executable, '-c', program, str(marker)], env=env,
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        deadline = time.monotonic() + 5
        while not marker.exists() and holder.poll() is None and time.monotonic() < deadline:
            time.sleep(0.02)
        assert marker.exists(), 'owned lock holder did not become ready'
        lock = runtime.DashboardLock(wait_timeout=0.03)
        os.utime(lock.lock_path, (1, 1))
        with pytest.raises(TimeoutError):
            with lock:
                pytest.fail('live old lock stolen')
        contender = subprocess.run([sys.executable, str(SCRIPTS / 'gen_dashboard.py'), '--json', '--skip-token-refresh'],
                                   env=env, capture_output=True, text=True, timeout=5)
        assert contender.returncode != 0
        assert 'generation already in progress' in contender.stderr
        assert contender.stdout == ''
        assert not (Path(env['DEVCORE_LOCAL_ROOT']) / 'Dashboard').exists()
        if kill_holder:
            holder.terminate()
            holder.communicate(timeout=5)
        else:
            holder.communicate('release\n', timeout=5)
        with runtime.DashboardLock(wait_timeout=0):
            pass
        assert lock.lock_path.exists()
    finally:
        if holder.poll() is None:
            holder.terminate()
        holder.communicate(timeout=5)


@pytest.mark.parametrize('json_mode', [False, True])
@pytest.mark.parametrize('fails', [False, True])
def test_main_uses_lock_and_restores_stdout(runtime, monkeypatch, json_mode, fails):
    generator = load_module(SCRIPTS / 'gen_dashboard.py', 'generator_lock_fixture')
    original_stdout = sys.stdout
    argv = ['gen_dashboard.py', '--skip-token-refresh'] + (['--json'] if json_mode else [])
    monkeypatch.setattr(sys, 'argv', argv)
    def generate(args, output):
        assert output is original_stdout
        assert sys.stdout is (sys.stderr if json_mode else original_stdout)
        with pytest.raises(TimeoutError):
            with runtime.DashboardLock(wait_timeout=0):
                pytest.fail('unlocked generation')
        if fails:
            raise ValueError('fixture generation failed')
        return 'generated'
    monkeypatch.setattr(generator, '_generate_dashboard', generate)
    if fails:
        with pytest.raises(ValueError, match='fixture generation failed'):
            generator.main()
    else:
        assert generator.main() == 'generated'
    assert sys.stdout is original_stdout
    with runtime.DashboardLock(wait_timeout=0):
        pass
