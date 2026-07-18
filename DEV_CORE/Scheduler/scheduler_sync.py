import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Setup paths dynamically
scheduler_dir = Path(__file__).resolve().parent
platform_root = scheduler_dir.parent
tools_dir = platform_root / "Tools"
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))

from devcore.paths import get_paths
from scheduler_contract import SchedulerJob, compute_next_run

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
logger = logging.getLogger("scheduler_sync")


def sync_registry(platform_dir: Path, data_dir: Path) -> None:
    """Synchronize static jobs.devcore.json definitions with dynamic jobs.json state."""
    static_path = platform_dir / "Scheduler" / "jobs.devcore.json"
    dynamic_path = data_dir / "Scheduler" / "jobs.json"

    if not static_path.exists():
        logger.error(f"Static jobs file not found at {static_path}")
        return

    logger.info(f"Syncing scheduler registry. Static: {static_path} | Dynamic: {dynamic_path}")

    # 1. Load static definitions
    with open(static_path, "r", encoding="utf-8") as f:
        static_data = json.load(f)

    # 2. Load dynamic states if exist
    dynamic_jobs_map: Dict[str, Dict[str, Any]] = {}
    if dynamic_path.exists():
        try:
            with open(dynamic_path, "r", encoding="utf-8") as f:
                dynamic_data = json.load(f)
            for item in dynamic_data:
                dynamic_jobs_map[item["id"]] = item
        except Exception as e:
            logger.error(f"Failed to load dynamic jobs.json: {e}. Starting fresh state.")

    # 3. Merge
    merged_jobs: List[Dict[str, Any]] = []
    now = datetime.now()

    for static_item in static_data:
        job_id = static_item["id"]
        # Convert statics relative paths to platform relative paths inside command
        # Ensure commands point to correct environment path prefix
        if "command" in static_item:
            # Clean path to be repository-relative or host-relative depending on OS
            path = static_item["command"]["path"]
            # If path doesn't start with /app or C:/ and is relative, we can prepend platform root path format
            # But wait: if it's running inside the container, platform_root is /app/DEV_CORE
            # We keep repository-relative paths inside jobs.json and let run_job.py resolve them!
            # That is the cleanest way!

        job = SchedulerJob(**static_item)

        # Merge state if exists
        if job_id in dynamic_jobs_map:
            dyn_item = dynamic_jobs_map[job_id]
            if "state" in dyn_item:
                job.state = SchedulerJobState_dict_to_model(dyn_item["state"])
        else:
            # Initial run calculation for new job
            next_run = compute_next_run(job, now)
            if next_run:
                job.state.next_run_at = next_run.isoformat()

        # Recalculate next_run_at if empty
        if not job.state.next_run_at:
            next_run = compute_next_run(job, now)
            if next_run:
                job.state.next_run_at = next_run.isoformat()

        merged_jobs.append(job.model_dump(by_alias=True))

    # 4. Save merged jobs atomically
    dynamic_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = dynamic_path.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(merged_jobs, f, indent=2)

    if dynamic_path.exists():
        os.remove(dynamic_path)
    os.rename(temp_path, dynamic_path)
    logger.info(f"Successfully synchronized {len(merged_jobs)} jobs.")


def SchedulerJobState_dict_to_model(state_dict: Dict[str, Any]) -> Any:
    """Helper to convert state dict to SchedulerJobState model."""
    from scheduler_contract import SchedulerJobState
    # Convert alias completed -> completed_count
    data = dict(state_dict)
    if "completed" in data:
        data["completed_count"] = data.pop("completed")
    return SchedulerJobState(**data)


if __name__ == "__main__":
    paths = get_paths()
    sync_registry(paths.platform_root, paths.data_root)
