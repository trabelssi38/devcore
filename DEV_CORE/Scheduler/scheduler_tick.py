import sys
import os
import time
import socket
import uuid
import json
import logging
import subprocess
import threading
import yaml
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple, Optional

# Setup sys.path to import devcore modules
scheduler_dir = Path(__file__).resolve().parent
if str(scheduler_dir) not in sys.path:
    sys.path.insert(0, str(scheduler_dir))
platform_root = scheduler_dir.parent
tools_dir = platform_root / "Tools"
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))

from devcore.paths import get_paths
from scheduler_contract import SchedulerJob, SchedulerJobSchedule, SchedulerJobCommand, SchedulerJobState, compute_next_run, _ensure_aware
import scheduler_history
import scheduler_lock
import scheduler_logs
from windows_job import WindowsJob
from scheduler_storage import write_json
from scheduler_presence import instance_guard, publish_ready, clear_ready, validate_launch_token
from stop_scheduler import stop_requested, stop_path, idle_wait
from scheduler_control import is_paused

logger = logging.getLogger("scheduler")


def bootstrap_jobs(yaml_path: Path, jobs_json_path: Path) -> None:
    """Bootstrap jobs.json from hermes_cron.yaml if jobs.json doesn't exist."""
    if jobs_json_path.exists():
        return

    logger.info("jobs.json not found. Bootstrapping from hermes_cron.yaml...")
    if not yaml_path.exists():
        logger.warning(f"hermes_cron.yaml not found at {yaml_path}. Starting with empty jobs config.")
        jobs_json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(jobs_json_path, "w", encoding="utf-8") as f:
            json.dump([], f)
        return

    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        tasks = config.get("cron_tasks", [])
        jobs = []

        for t in tasks:
            # Skip if disabled
            if not t.get("enabled", True):
                continue

            # Convert catchup
            policy = "catch_up" if t.get("catchup") else "skip"
            timezone_str = t.get("timezone", "Europe/Paris")

            # Command path resolution (map Windows paths to container-safe relative path)
            script = t.get("script", "")
            # We look for scripts in DEV_CORE/Scripts/Auto/ or .hermes/scripts/
            # For container compatibility, we check if they exist under app/DEV_CORE/Scripts/Auto/
            script_path = str(platform_root / "Scripts" / "Auto" / script)
            if not os.path.exists(script_path):
                # Fallback to general scripts folder
                script_path = str(platform_root / "Scripts" / script)

            command = SchedulerJobCommand(
                type="python",
                path=script_path,
                args=[]
            )

            job = SchedulerJob(
                schema_version=1,
                id=t["id"],
                name=t["name"],
                enabled=True,
                no_agent=t.get("no_agent", True),
                schedule=SchedulerJobSchedule(kind="cron", expr=t["schedule"]),
                command=command,
                state=SchedulerJobState(),
                policy=policy,
                timezone=timezone_str
            )
            # Calculate next run initially
            initial_next = compute_next_run(job, datetime.now())
            if initial_next:
                job.state.next_run_at = initial_next.isoformat()

            jobs.append(job.model_dump(by_alias=True))

        jobs_json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(jobs_json_path, "w", encoding="utf-8") as f:
            json.dump(jobs, f, indent=2)
        logger.info(f"Successfully bootstrapped {len(jobs)} jobs into {jobs_json_path}")
    except Exception as e:
        logger.exception(f"Error bootstrapping jobs from yaml: {e}")
        # Write empty array on failure
        with open(jobs_json_path, "w", encoding="utf-8") as f:
            json.dump([], f)


def load_jobs(jobs_json_path: Path) -> List[SchedulerJob]:
    """Load jobs list from jobs.json."""
    try:
        with open(jobs_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("Scheduler jobs must be a list")
        jobs = [SchedulerJob(**item) for item in data]
        if len({job.id for job in jobs}) != len(jobs):
            raise ValueError("Duplicate scheduler job id")
        return jobs
    except Exception as e:
        logger.error(f"Error loading jobs.json: {e}")
        raise


def save_jobs(jobs: List[SchedulerJob], jobs_json_path: Path) -> None:
    """Save jobs list atomically to jobs.json."""
    try:
        data = [job.model_dump(by_alias=True) for job in jobs]
        write_json(jobs_json_path, data)
    except Exception as e:
        logger.error(f"Error saving jobs.json atomically: {e}")
        raise


def execute_job_command(command: SchedulerJobCommand, timeout: int = 300, *, output_limit: int = 1048576) -> Tuple[int, str, str]:
    """Execute a Windows-contained job with bounded stdout and stderr in bytes."""
    run_job_script = scheduler_dir / "run_job.py"
    if type(timeout) not in (int, float) or not 0 < timeout <= 3600:
        raise ValueError("Job timeout must be positive and at most one hour")
    if type(output_limit) is not int or not 1 <= output_limit <= 16777216:
        raise ValueError("Output limit must be 1..16 MiB per stream")
    cmd_args = [sys.executable, str(run_job_script), "--devcore-gated", command.type, command.path] + command.args

    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if os.name == "nt" else 0
    proc, job = None, None
    buffers = [bytearray(), bytearray()]
    overflow, read_failed = threading.Event(), threading.Event()
    readers = []
    deadline = time.monotonic() + timeout
    cleanup_deadline = None
    def check_deadline():
        if time.monotonic() >= deadline:
            raise TimeoutError("Scheduler startup/execution deadline expired")
    def drain(stream, buffer):
        try:
            while chunk := stream.read(65536):
                room = output_limit - len(buffer)
                buffer.extend(chunk[:max(0, room)])
                if len(chunk) > room:
                    overflow.set()
        except (OSError, ValueError):
            read_failed.set()
    try:
        job = WindowsJob()  # Fail closed if containment is unavailable.
        check_deadline()
        proc = subprocess.Popen(
            cmd_args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
            creationflags=creationflags
        )
        job.assign(proc.pid)
        check_deadline()  # Gate stays closed if startup consumed the budget.
        for stream, buffer in zip((proc.stdout, proc.stderr), buffers):
            reader = threading.Thread(target=drain, args=(stream, buffer), daemon=True)
            reader.start()
            readers.append(reader)
        check_deadline()
        proc.stdin.write(b"START\n")
        proc.stdin.close()
        status, reason = None, ""
        while True:
            if overflow.is_set():
                status, reason = -10, f"Job output exceeded {output_limit} bytes per stream. "
                break
            if read_failed.is_set():
                status, reason = -1, "Job output collection failed. "
                break
            if time.monotonic() >= deadline:
                status, reason = -9, f"Job timed out after {timeout} seconds. "
                break
            if proc.poll() is not None:
                break
            time.sleep(min(.02, max(0, deadline - time.monotonic())))
        job.close()  # Stop all descendants, including inherited pipe holders.
        cleanup_deadline = time.monotonic() + 5
        proc.wait(timeout=max(.001, cleanup_deadline - time.monotonic()))
        for reader in readers:
            reader.join(timeout=max(0, cleanup_deadline - time.monotonic()))
        if any(reader.is_alive() for reader in readers):
            return -1, "", "Job output cleanup did not finish within five seconds"
        # Fast-exiting jobs may exceed the cap during the final drain.
        if overflow.is_set() and status is None:
            status, reason = -10, f"Job output exceeded {output_limit} bytes per stream. "
        if read_failed.is_set() and status is None:
            status, reason = -1, "Job output collection failed. "
        return (proc.returncode if status is None else status,
                buffers[0].decode("utf-8", errors="replace"),
                reason + buffers[1].decode("utf-8", errors="replace"))
    except TimeoutError:
        return (-9, "", f"Job timed out after {timeout} seconds during startup/execution")
    except Exception as e:
        return (-1, "", f"Failed to execute command: {e}")
    finally:
        if job is not None:
            job.close()
        if proc is not None:
            if cleanup_deadline is None:
                cleanup_deadline = time.monotonic() + 5
            if proc.poll() is None:
                proc.kill()  # Assignment failure: wrapper is still behind the gate.
            proc.wait(timeout=max(.001, cleanup_deadline - time.monotonic()))
            for reader in readers:
                reader.join(timeout=max(0, cleanup_deadline - time.monotonic()))
            for stream in (proc.stdin, proc.stdout, proc.stderr):
                if stream is not None:
                    stream.close()


def main_loop(db_path: Path, jobs_json_path: Path, lock_path: Path, ready_callback=None, unready_callback=None, stop_callback=None) -> None:
    """Main scheduler tick loop."""
    hostname = socket.gethostname()
    owner_id = f"scheduler_{hostname}_{os.getpid()}_{uuid.uuid4().hex[:6]}"

    # Initialize locks and historical DB
    lock = scheduler_lock.SchedulerLeaseLock(lock_path, owner_id, lease_duration_seconds=30)
    scheduler_history.init_db(db_path)

    logger.info(f"Starting DevCore Scheduler Tick Daemon. Owner ID: {owner_id}")
    shadow_log_counter = 0

    while True:
        try:
            if stop_callback is not None and stop_callback():
                lock.release()  # Only our own lease; foreign leases preserved.
                logger.info('Scheduler cooperative shutdown after current job/cycle')
                return
            # 1. Acquire / Renew Lock
            has_lock = lock.acquire()

            if not has_lock:
                # Shadow Mode
                if shadow_log_counter % 6 == 0:
                    current_owner = lock.get_owner()
                    logger.info(f"[SHADOW MODE] Lock held by owner: {current_owner}. Idle observation.")
                shadow_log_counter += 1
                idle_wait(stop_callback)
                continue

            # Active Mode
            shadow_log_counter = 0
            with lock.hold():
                jobs = load_jobs(jobs_json_path)
                if ready_callback is not None:
                    ready_callback()
                now = datetime.now()
                needs_save = False

                for job in jobs:
                    if stop_callback is not None and stop_callback():
                        break  # Persist earlier results before leaving the cycle.
                    if not job.enabled:
                        continue

                    next_run_dt = None
                    if job.state.next_run_at:
                        try:
                            next_run_dt = datetime.fromisoformat(job.state.next_run_at)
                            if next_run_dt.tzinfo is None:
                                next_run_dt = _ensure_aware(next_run_dt, job.timezone)
                        except Exception:
                            pass

                    # If next_run_at is empty or malformed, calculate it initially
                    if not next_run_dt:
                        next_run_dt = compute_next_run(job, now)
                        if next_run_dt:
                            job.state.next_run_at = next_run_dt.isoformat()
                            needs_save = True
                        continue

                    # Check if job is due
                    now_job_tz = _ensure_aware(now, job.timezone)
                    if next_run_dt <= now_job_tz:
                        # Preserve the historical occurrence key, including its offset
                        # or naive representation. Normalize only for comparison.
                        scheduled_at_str = datetime.fromisoformat(job.state.next_run_at).isoformat()

                        # 2. Check Idempotency constraint
                        if scheduler_history.is_run_completed(job.id, scheduled_at_str, db_path):
                            result = scheduler_history.get_completed_result(job.id, scheduled_at_str, db_path.resolve())
                            if result is None:
                                raise RuntimeError(f"Job '{job.id}' completed result unavailable; schedule not advanced")
                            status, err_msg = result
                            # JSON may lag a committed result after a crash/save failure.
                            # Publish marker, count and next slot together in jobs.json.
                            if job.state.last_run_at != scheduled_at_str:
                                if status == 'ok':
                                    job.state.completed_count += 1
                            job.state.last_run_at = scheduled_at_str
                            job.state.last_status = status
                            job.state.last_error = err_msg
                            new_next = compute_next_run(job, now)
                            job.state.next_run_at = new_next.isoformat() if new_next else None
                            needs_save = True
                            continue

                        # 3. Claim the job execution slot
                        claim_success = scheduler_history.record_run(
                            job_id=job.id,
                            scheduled_at=scheduled_at_str,
                            run_at=datetime.now().isoformat(),
                            duration=0.0,
                            status="running",
                            db_path=db_path
                        )

                        if not claim_success:
                            # Existing running/error claim is not a completed occurrence.
                            logger.warning(f"Job '{job.id}' slot {scheduled_at_str} already claimed; schedule retained pending reconciliation")
                            continue

                        # 4. Execute command
                        logger.info(f"Running job '{job.id}' scheduled for {scheduled_at_str}")
                        start_time = time.time()
                        ret_code, stdout, stderr = execute_job_command(job.command)
                        elapsed = time.time() - start_time

                        status = "ok" if ret_code == 0 else "error"
                        err_msg = stderr if ret_code != 0 else None

                        # Log output
                        if ret_code == 0:
                            logger.info(f"Command for job '{job.id}' exited with code 0 in {elapsed:.2f}s; persisting result")
                        else:
                            logger.error(f"Job '{job.id}' failed (code {ret_code}) in {elapsed:.2f}s. Stderr: {stderr}")

                        # 5. Record run history result
                        result_saved = scheduler_history.update_run(
                            job_id=job.id,
                            scheduled_at=scheduled_at_str,
                            duration=elapsed,
                            status=status,
                            error=err_msg,
                            db_path=db_path
                        )
                        if not result_saved:
                            raise RuntimeError(f"Job '{job.id}' result could not be persisted; schedule not advanced")

                        # Update job state
                        job.state.last_run_at = scheduled_at_str
                        job.state.last_status = status
                        job.state.last_error = err_msg
                        if status == "ok":
                            job.state.completed_count += 1

                        # Recompute next scheduled run
                        new_next = compute_next_run(job, now)
                        job.state.next_run_at = new_next.isoformat() if new_next else None
                        needs_save = True

                if needs_save:
                    save_jobs(jobs, jobs_json_path)

        except Exception as e:
            if unready_callback is not None:
                try:
                    unready_callback()
                except Exception:
                    logger.exception('Could not invalidate scheduler readiness')
            logger.exception(f"Unexpected error in scheduler tick loop: {e}")

        idle_wait(stop_callback)


def run_daemon():
    paths = get_paths()
    db_path = paths.local_root / "Scheduler" / "scheduler.db"
    jobs_json_path = paths.local_root / "Scheduler" / "jobs.json"
    lock_path = paths.local_root / "Scheduler" / "scheduler.lock"
    log_dir = paths.local_root / "Logs" / "scheduler"

    # Init logging
    scheduler_logs.setup_scheduler_logging(log_dir)

    # Lifetime guard also covers initialization/synchronization and idle sleeps.
    with instance_guard(paths.local_root):
        start_daemon(paths, db_path, jobs_json_path, lock_path)


def start_daemon(paths, db_path, jobs_json_path, lock_path):
    if is_paused(paths.local_root):
        raise RuntimeError('Scheduler restart inhibited; explicit resume required')
    token = os.environ.get('DEVCORE_SCHEDULER_START_TOKEN')
    if token is None:
        token = uuid.uuid4().hex  # Standalone daemon, no global environment mutation.
    validate_launch_token(token)  # Explicit invalid configuration fails before sync.
    # Initial Sync/Bootstrap from jobs.devcore.json
    try:
        import scheduler_sync
        if not scheduler_sync.sync_registry(paths.platform_root, paths.local_root):
            logger.error("Scheduler startup refused: registry synchronization failed or busy")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to synchronize jobs registry on startup: {e}")
        sys.exit(1)

    # Start loop
    ready = lambda: publish_ready(paths.local_root, token,
        data_root=paths.data_root, platform_root=paths.platform_root)
    unready = lambda: clear_ready(paths.local_root, token)
    stop = lambda: stop_requested(paths.local_root, token)
    try:
        main_loop(db_path, jobs_json_path, lock_path, ready_callback=ready, unready_callback=unready, stop_callback=stop)
    finally:
        unready()
        stop_path(paths.local_root, token).unlink(missing_ok=True)


if __name__ == '__main__':
    run_daemon()
