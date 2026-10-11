"""Process executor with Windows Job Object tree containment and environment isolation."""

from __future__ import annotations

from collections.abc import Callable
import io
import os
from pathlib import Path
import subprocess
import threading
import time
from typing import Any

from ..db import get_local_data_root
from .models import RunRecord

# Sensitive substrings to strip from child environment
SENSITIVE_ENV_SUBSTRINGS = (
    "SECRET",
    "TOKEN",
    "PASSWORD",
    "CREDENTIAL",
    "API_KEY",
    "APIKEY",
    "PRIVATE_KEY",
    "AUTH_KEY",
)


def build_isolated_environment(
    base_env: dict[str, str] | None = None,
    explicit_env: dict[str, str] | None = None,
    run: RunRecord | None = None,
    workspace_path: Path | None = None,
) -> dict[str, str]:
    """Build scrubbed environment for child process without leaking secrets."""
    source = dict(base_env if base_env is not None else os.environ)
    safe_env: dict[str, str] = {}

    for k, v in source.items():
        k_upper = k.upper()
        if any(substr in k_upper for substr in SENSITIVE_ENV_SUBSTRINGS):
            continue
        safe_env[k] = v

    # Add runtime context
    if run is not None:
        safe_env["DEVCORE_RUN_ID"] = run.id
        safe_env["DEVCORE_PROJECT_ID"] = run.project_id
        safe_env["DEVCORE_TASK_ID"] = run.task_id or ""
    if workspace_path is not None:
        safe_env["DEVCORE_WORKSPACE"] = str(workspace_path)

    # Merge explicit user/run env (allowed explicitly by the caller)
    if explicit_env:
        safe_env.update(explicit_env)

    return safe_env


class ProcessRunExecutor:
    """Executes run commands with workspace isolation and Windows Job Object containment."""

    def __init__(
        self,
        local_root: Path | None = None,
        output_limit_bytes: int = 65536,
    ):
        self.local_root = local_root or get_local_data_root()
        self.workspaces_dir = self.local_root / "workspaces"
        self.workspaces_dir.mkdir(parents=True, exist_ok=True)
        self.output_limit_bytes = output_limit_bytes
        self._active_processes: set[subprocess.Popen] = set()
        self._proc_lock = threading.Lock()

    def interrupt_all(self) -> None:
        """Immediately terminate all currently running child processes."""
        with self._proc_lock:
            procs = list(self._active_processes)
        for proc in procs:
            try:
                proc.kill()
            except Exception:
                pass

    def get_workspace_dir(self, run_id: str) -> Path:
        ws = self.workspaces_dir / run_id
        ws.mkdir(parents=True, exist_ok=True)
        return ws

    def execute(
        self,
        run: RunRecord,
        *,
        worker_token: str,
        heartbeat_callback: Callable[[], bool] | None = None,
        heartbeat_interval_seconds: float = 2.0,
        check_cancellation_callback: Callable[[], bool] | None = None,
        check_pause_callback: Callable[[], bool] | None = None,
    ) -> tuple[str, int, str, str]:
        """Execute run process.

        Returns:
            (outcome, exit_code, stdout_str, stderr_str)
            outcome in {"completed", "timed_out", "cancelled", "failed", "paused"}
        """
        workspace_dir = self.get_workspace_dir(run.id)
        safe_env = build_isolated_environment(
            explicit_env=run.env,
            run=run,
            workspace_path=workspace_dir,
        )

        job_object = None
        if os.name == "nt":
            try:
                from ..infra.windows_job import WindowsJob
                job_object = WindowsJob()
            except Exception as exc:
                return "failed", 1, "", f"Windows Job Object containment unavailable: {exc}"

        stdout_buf = io.BytesIO()
        stderr_buf = io.BytesIO()
        stdout_truncated = False
        stderr_truncated = False

        def _drain_stream(stream, buf, limit):
            nonlocal stdout_truncated, stderr_truncated
            try:
                while True:
                    chunk = stream.read(4096)
                    if not chunk:
                        break
                    current_len = buf.tell()
                    if current_len < limit:
                        allowed = limit - current_len
                        buf.write(chunk[:allowed])
                        if len(chunk) > allowed:
                            if buf is stdout_buf:
                                stdout_truncated = True
                            else:
                                stderr_truncated = True
                    else:
                        if buf is stdout_buf:
                            stdout_truncated = True
                        else:
                            stderr_truncated = True
            except Exception:
                pass
            finally:
                try:
                    stream.close()
                except Exception:
                    pass

        creation_flags = 0
        if os.name == "nt":
            creation_flags = subprocess.CREATE_NO_WINDOW

        proc = None
        try:
            cmd = run.command
            if not cmd:
                return "failed", 1, "", "No command specified"

            proc = subprocess.Popen(
                cmd,
                cwd=str(workspace_dir),
                env=safe_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=creation_flags,
            )
            with self._proc_lock:
                self._active_processes.add(proc)


            if job_object is not None and proc.pid:
                try:
                    job_object.assign(proc.pid)
                except Exception as exc:
                    try:
                        proc.kill()
                        proc.wait(timeout=2.0)
                    except Exception:
                        pass
                    return "failed", 1, "", f"Failed to assign process {proc.pid} to Windows Job Object: {exc}"

            t_out = threading.Thread(
                target=_drain_stream,
                args=(proc.stdout, stdout_buf, self.output_limit_bytes),
                daemon=True,
            )
            t_err = threading.Thread(
                target=_drain_stream,
                args=(proc.stderr, stderr_buf, self.output_limit_bytes),
                daemon=True,
            )
            t_out.start()
            t_err.start()

            start_time = time.monotonic()
            last_heartbeat = start_time
            deadline = start_time + max(1.0, float(run.timeout_seconds))

            outcome = "completed"
            exit_code = 0

            while True:
                ret = proc.poll()
                now = time.monotonic()

                if ret is not None:
                    exit_code = ret
                    outcome = "completed"
                    break

                if now >= deadline:
                    outcome = "timed_out"
                    exit_code = -9
                    break

                if check_cancellation_callback and check_cancellation_callback():
                    outcome = "cancelled"
                    exit_code = -15
                    break

                if check_pause_callback and check_pause_callback():
                    outcome = "paused"
                    exit_code = -1
                    break

                if heartbeat_callback and (now - last_heartbeat >= heartbeat_interval_seconds):
                    alive = heartbeat_callback()
                    if not alive:
                        if check_pause_callback and check_pause_callback():
                            outcome = "paused"
                            exit_code = -1
                            break
                        outcome = "failed"
                        exit_code = -1
                        break
                    last_heartbeat = now

                time.sleep(0.05)

            if outcome in {"timed_out", "cancelled", "failed", "paused"}:
                if job_object is not None:
                    try:
                        job_object.close()
                    except Exception:
                        pass
                    job_object = None

                try:
                    proc.kill()
                except Exception:
                    pass

            try:
                proc.wait(timeout=3.0)
            except Exception:
                pass

            t_out.join(timeout=1.0)
            t_err.join(timeout=1.0)

            out_str = stdout_buf.getvalue().decode("utf-8", errors="replace")
            err_str = stderr_buf.getvalue().decode("utf-8", errors="replace")

            if stdout_truncated:
                out_str += f"\n[Output truncated at {self.output_limit_bytes} bytes]"
            if stderr_truncated:
                err_str += f"\n[Output truncated at {self.output_limit_bytes} bytes]"

            return outcome, exit_code, out_str, err_str

        except Exception as exc:
            return "failed", 1, "", f"Failed to execute process: {exc}"
        finally:
            if proc is not None:
                with self._proc_lock:
                    self._active_processes.discard(proc)
                if proc.poll() is None:
                    try:
                        proc.kill()
                        proc.wait(timeout=2.0)
                    except Exception:
                        pass
            if job_object is not None:
                try:
                    job_object.close()
                except Exception:
                    pass

