import argparse
import json
import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parent
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))
PLATFORM_ROOT = API_ROOT.parent
if str(PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(PLATFORM_ROOT))

from devcore_api.ports import FileTaskRepository, SqliteTaskRepository, TaskBoardNotFound
from devcore_engine.db import get_db_path


def truncate(value: str, max_length: int = 40) -> str:
    return value if len(value) <= max_length else value[: max_length - 3] + "..."


def render_table(project: str, tasks: list) -> str:
    lines = [
        "",
        "  DEV_CORE -- Backlog (todo)",
        "  -------------------------------------------------------",
        f"  {'ID':<6} {'Mode':<12} {'Status':<10} Titre",
        "  -------------------------------------------------------",
    ]
    for task in tasks:
        if task.status not in {"todo", "active", "paused"}:
            continue
        icon = {"active": "[active]", "paused": "[paused]"}.get(task.status, "[todo]  ")
        prefix = ">" if task.status == "active" else " "
        lines.append(f"{prefix} {task.id:<6} {task.mode:<12} {icon:<10} {truncate(task.title)}")
    lines.extend(["  -------------------------------------------------------", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="DEV_CORE task list compatibility adapter")
    parser.add_argument("--project", required=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--legacy-json", action="store_true", help="Read the historical tasks.json explicitly")
    args = parser.parse_args()

    if args.legacy_json:
        repository = FileTaskRepository()
    else:
        db_path = get_db_path()
        if not db_path.is_file():
            parser.error(f"Local task database not found: {db_path}")
        repository = SqliteTaskRepository(db_path)
    try:
        tasks = repository.list_tasks(project=args.project)
    except TaskBoardNotFound:
        if args.json:
            print(json.dumps({"schema_version": 1, "project": args.project, "tasks": []}, ensure_ascii=False))
        else:
            print("  Aucun tasks.json historique.")
        return 0

    visible = [task for task in tasks if task.status in {"todo", "active", "paused", "in_progress"}]
    if args.json:
        print(
            json.dumps(
                {
                    "schema_version": 1,
                    "project": args.project,
                    "tasks": [task.model_dump(mode="json") for task in visible],
                },
                ensure_ascii=False,
            )
        )
    else:
        print(render_table(args.project, visible))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
