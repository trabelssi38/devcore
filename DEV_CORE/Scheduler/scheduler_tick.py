import sys
import os
import time
import socket
import uuid
import json
import logging
import subprocess
import yaml
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple, Optional

# Setup sys.path to import devcore modules
scheduler_dir = Path(__file__).resolve().parent
platform_root = scheduler_dir.parent
tools_dir = platform_root / "Tools"
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))

from devcore.paths import get_paths
from scheduler_contract import SchedulerJob, SchedulerJobSchedule, SchedulerJobCommand, SchedulerJobState, compute_next_run, _ensure_aware
import scheduler_history
import scheduler_lock
import scheduler_logs

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
    if not jobs_json_path.exists():
        return []
    try:
        with open(jobs_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [SchedulerJob(**item) for item in data]
    except Exception as e:
        logger.error(f"Error loading jobs.json: {e}")
        return []


def save_jobs(jobs: List[SchedulerJob], jobs_json_path: Path) -> None:
    """Save jobs list atomically to jobs.json."""
    temp_path = jobs_json_path.with_suffix(".tmp")
    try:
        data = [job.model_dump(by_alias=True) for job in jobs]
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        if jobs_json_path.exists():
            os.remove(jobs_json_path)
        os.rename(temp_path, jobs_json_path)
    except Exception as e:
        logger.error(f"Error saving jobs.json atomically: {e}")


def execute_job_command(command: SchedulerJobCommand, timeout: int = 300) -> Tuple[int, str, str]:
    """Execute the job command via run_job.py to ensure cross-platform compatibility."""
    run_job_script = scheduler_dir / "run_job.py"
    cmd_args = [sys.executable, str(run_job_script), command.type, command.path] + command.args

    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if os.name == "nt" else 0
    try:
        proc = subprocess.run(
            cmd_args,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=creationflags
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as te:
        return (-9, te.stdout or "", f"Job timed out after {timeout} seconds. {te.stderr or ''}")
    except Exception as e:
        return (-1, "", f"Failed to execute command: {e}")


def main_loop(db_path: Path, jobs_json_path: Path, lock_path: Path) -> None:
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
            # 1. Acquire / Renew Lock
            has_lock = lock.acquire()
            
            if not has_lock:
                # Shadow Mode
                if shadow_log_counter % 6 == 0:
                    current_owner = lock.get_owner()
                    logger.info(f"[SHADOW MODE] Lock held by owner: {current_owner}. Idle observation.")
                shadow_log_counter += 1
                time.sleep(10)
                continue

            # Active Mode
            shadow_log_counter = 0
            jobs = load_jobs(jobs_json_path)
            now = datetime.now()
            needs_save = False

            for job in jobs:
                if not job.enabled:
                    continue

                next_run_dt = None
                if job.state.next_run_at:
                    try:
                        next_run_dt = datetime.fromisoformat(job.state.next_run_at)
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
                    scheduled_at_str = next_run_dt.isoformat()
                    
                    # 2. Check Idempotency constraint
                    if scheduler_history.is_run_completed(job.id, scheduled_at_str, db_path):
                        # Already run, compute next run time
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
                        # Double-trigger claim check failed
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
                        logger.info(f"Job '{job.id}' completed successfully in {elapsed:.2f}s")
                    else:
                        logger.error(f"Job '{job.id}' failed (code {ret_code}) in {elapsed:.2f}s. Stderr: {stderr}")

                    # 5. Record run history result
                    scheduler_history.update_run(
                        job_id=job.id,
                        scheduled_at=scheduled_at_str,
                        duration=elapsed,
                        status=status,
                        error=err_msg,
                        db_path=db_path
                    )

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
            logger.exception(f"Unexpected error in scheduler tick loop: {e}")

        time.sleep(10)


if __name__ == "__main__":
    paths = get_paths()
    db_path = paths.local_root / "Scheduler" / "scheduler.db"
    jobs_json_path = paths.local_root / "Scheduler" / "jobs.json"
    lock_path = paths.local_root / "Scheduler" / "scheduler.lock"
    log_dir = paths.local_root / "Logs" / "scheduler"
    
    # Init logging
    scheduler_logs.setup_scheduler_logging(log_dir)

    # Initial Sync/Bootstrap from jobs.devcore.json
    try:
        import scheduler_sync
        scheduler_sync.sync_registry(platform_root, paths.local_root)
    except Exception as e:
        logger.error(f"Failed to synchronize jobs registry on startup: {e}")
        # Fallback to bootstrap if sync_registry fails
        yaml_path = platform_root / "Scripts" / "hermes_cron.yaml"
        bootstrap_jobs(yaml_path, jobs_json_path)

    # Start loop
    main_loop(db_path, jobs_json_path, lock_path)
