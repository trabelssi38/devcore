import os
import sys
import json
import logging
from pathlib import Path

# Ensure paths can be resolved
auto_dir = Path(__file__).resolve().parent
platform_root = auto_dir.parent.parent
tools_dir = platform_root / "Tools"
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))

from devcore.paths import get_paths
from devcore.agent_runner import get_agent_runner

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
logger = logging.getLogger("check_active_task")


def main() -> None:
    paths = get_paths()
    runner = get_agent_runner()
    
    # Check runner status
    status = runner.report_status()
    if status.get("status") != "OK":
        logger.info(f"Agent runner backend is inactive or disabled: {status.get('error', 'Unknown state')}")
        sys.exit(0)

    # Resolve active task
    from dc import get_active_project
    proj = get_active_project()
    tasks_file = paths.data_root / "Memory" / proj / "tasks.json"

    if not tasks_file.exists():
        logger.info("No active task database found.")
        sys.exit(0)

    try:
        board = json.loads(tasks_file.read_text(encoding="utf-8-sig"))
    except Exception as e:
        logger.error(f"Failed to read tasks.json: {e}")
        sys.exit(1)

    tasks = board.get("tasks", [])
    active_task = next((t for t in tasks if t.get("status") == "active"), None)

    if not active_task:
        logger.info("No active task currently running.")
        sys.exit(0)

    logger.info(f"Found active task: {active_task.get('id')} - {active_task.get('title')}")
    
    # Run the active agent runner
    try:
        receipt = runner.run(active_task)
        logger.info(f"Task runner completed with receipt: {receipt}")
    except Exception as e:
        logger.exception(f"Execution failed: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
