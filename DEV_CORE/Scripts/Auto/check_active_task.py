import argparse
import sys
import logging
from pathlib import Path

# Ensure paths can be resolved
auto_dir = Path(__file__).resolve().parent
platform_root = auto_dir.parent.parent
tools_dir = platform_root / "Tools"
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))
if str(platform_root) not in sys.path:
    sys.path.insert(0, str(platform_root))

from devcore.agent_runner import get_agent_runner
from devcore_engine.context import project_from_directory, validate_project_id
from devcore_engine.services.tasks import TaskService

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
logger = logging.getLogger("check_active_task")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Check one project's active SQLite task")
    parser.add_argument("--project")
    args = parser.parse_args(argv)
    project = args.project or project_from_directory()
    if not project:
        parser.error("--project or a local .devcore/project.json is required")
    try:
        project = validate_project_id(project)
    except ValueError as exc:
        parser.error(str(exc))

    service = TaskService()
    try:
        active_task = next((task for task in service.get_board(project)["tasks"]
                            if task["status"] == "in_progress"), None)
    finally:
        service.conn.close()
    if not active_task:
        logger.info("No active task for project %s.", project)
        return 0

    runner = get_agent_runner()
    # Check runner status
    status = runner.report_status()
    if status.get("status") != "OK":
        logger.info(f"Agent runner backend is inactive or disabled: {status.get('error', 'Unknown state')}")
        return 0

    logger.info(f"Found active task: {active_task.get('id')} - {active_task.get('title')}")
    
    # Run the active agent runner
    try:
        receipt = runner.run(active_task)
        logger.info("Task runner returned receipt: %s", receipt)
        return 0 if receipt.get("status") in ("ok", "manual") else 2
    except Exception as e:
        logger.exception(f"Execution failed: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
