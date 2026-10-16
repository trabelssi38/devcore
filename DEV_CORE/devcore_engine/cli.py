"""
cli.py -- DEV_CORE Engine Unified CLI Interface
Usage: python -m devcore_engine <command> [options]
"""

from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

import argparse
import json
import os
from typing import Any

def _execute_task_cli_via_api(api_url: str, args: Any, parser: Any) -> None:
    import urllib.request
    import urllib.error
    from urllib.parse import urlencode

    if args.task_action == "board":
        url = f"{api_url}/api/v1/tasks?" + urlencode({"project": args.project})
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            parser.error(f"API request failed with HTTP {exc.code}")
        except Exception as exc:
            parser.error(f"API request failed: {exc}")
        tasks = data.get("tasks", [])
        current_task = next((t["id"] for t in tasks if t.get("status") in {"active", "in_progress"}), None)
        if getattr(args, "json", False):
            board_dict = {
                "project": args.project,
                "current_task": current_task,
                "tasks": tasks,
            }
            print(json.dumps(board_dict, ensure_ascii=False))
        else:
            print(f"=== TASK BOARD ({args.project}) ===")
            print(f"Current task: {current_task or 'None'}\n")
            for t in tasks:
                status_str = t.get("status", "todo").upper()
                print(f"  [{status_str:11s}] {t['id']}: {t['title']} ({t.get('steps_done', 0)}/{t.get('steps_total', 1)} steps)")

    elif args.task_action == "next":
        url = f"{api_url}/api/v1/tasks/next"
        req = urllib.request.Request(
            url,
            data=json.dumps({"project": args.project}).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                active = data.get("task")
        except Exception as exc:
            parser.error(f"API request failed: {exc}")
        if getattr(args, "json", False):
            print(json.dumps(active, ensure_ascii=False))
        elif active:
            print(f"Active task: [{active['id']}] {active['title']}")
        else:
            print("No pending tasks available.")

    elif args.task_action == "complete":
        url = f"{api_url}/api/done"
        body = json.dumps({"project": args.project, "id": args.task_id, "expected_version": args.expected_version}).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", "Accept": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                print(f"Completed task: [{args.task_id}] {data.get('message', 'done')}")
        except urllib.error.HTTPError as exc:
            err_code = ""
            try:
                payload = json.loads(exc.read().decode("utf-8"))
                detail = payload.get("detail", {})
                err_code = detail.get("code") if isinstance(detail, dict) else payload.get("code", "")
            except Exception:
                pass
            if exc.code == 409 or err_code == "stale_task_version":
                parser.error("stale task version")
            elif exc.code == 404 or err_code == "task_not_found":
                parser.error("task not found or not completable in project")
            else:
                parser.error(f"HTTP {exc.code}")
        except Exception as exc:
            parser.error(str(exc))

    elif args.task_action == "pause":
        url = f"{api_url}/api/pause"
        body = json.dumps({"project": args.project, "id": args.task_id, "expected_version": args.expected_version}).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", "Accept": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                print(f"Paused task: [{args.task_id}]")
        except urllib.error.HTTPError as exc:
            if exc.code == 409:
                parser.error("stale task version")
            elif exc.code == 404:
                parser.error("no matching active task in project")
            else:
                parser.error(f"HTTP {exc.code}")
        except Exception as exc:
            parser.error(str(exc))

    elif args.task_action == "resume":
        url = f"{api_url}/api/resume"
        body = json.dumps({"project": args.project, "id": args.task_id, "expected_version": args.expected_version}).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", "Accept": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                print(f"Resumed task: [{args.task_id}]")
        except urllib.error.HTTPError as exc:
            if exc.code == 409:
                parser.error("stale task version")
            elif exc.code == 404:
                parser.error("no matching paused task in project")
            else:
                parser.error(f"HTTP {exc.code}")
        except Exception as exc:
            parser.error(str(exc))

    elif args.task_action == "add":
        url = f"{api_url}/api/v1/tasks"
        body = json.dumps({
            "project": args.project,
            "title": args.title,
            "mode": getattr(args, "mode", "coding"),
            "steps": getattr(args, "steps", 1),
            "depends_on": getattr(args, "depends_on", None),
        }).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", "Accept": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                t = data.get("task", {})
                print(f"Created task: [{t.get('id', '?')}] {t.get('title', args.title)}")
        except Exception as exc:
            parser.error(str(exc))
    else:
        parser.error(f"task action {args.task_action} via API not supported")


def main() -> None:
    # Dispatch before loading local services, roots or migration adapters.
    if sys.argv[1:2] == ["individual"]:
        from devcore_engine.clients.individual_cli import main as individual_main
        raise SystemExit(individual_main(sys.argv[2:]))

    from devcore_engine.services.memory import MemoryService
    from devcore_engine.services.memory_hierarchy import MemoryHierarchy
    from devcore_engine.services.tasks import TaskService
    from devcore_engine.services.events import EventBus
    from devcore_engine.context import RequestContext, project_from_directory
    from devcore_engine.migrate_to_unified_db import DevCoreMigrator

    parser = argparse.ArgumentParser(prog="devcore", description="DEV_CORE Unified CLI Engine")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")
    subparsers.add_parser("individual", help="Explicit individual API context/tasks/done/delete; no local store")

    diag_p = subparsers.add_parser("diagnose", help="Run system diagnostics")
    diag_p.add_argument("--gate", action="store_true", help="Run gate check mode")
    diag_p.add_argument("--json", action="store_true", help="Output JSON format")
    diag_p.add_argument("--fix", action="store_true", help="Request diagnostic repairs (simulation only)")
    diag_p.add_argument("--dry-run", action="store_true", help="Simulate requested repairs")


    # Skills
    skill_p = subparsers.add_parser("skills", help="Skill operations")
    skill_sub = skill_p.add_subparsers(dest="skill_action")
    skill_sub.add_parser("list", help="List registered skills")

    # Knowledge
    kg_p = subparsers.add_parser("knowledge", help="Knowledge graph operations")
    kg_sub = kg_p.add_subparsers(dest="kg_action")
    kg_sub.add_parser("stats", help="Get graph statistics")

    # Plugins
    plug_p = subparsers.add_parser("plugins", help="Plugin operations")
    plug_sub = plug_p.add_subparsers(dest="plug_action")
    plug_sub.add_parser("list", help="List registered plugins")
    plug_sub.add_parser("health", help="Check plugins health")
    
    p_inst = plug_sub.add_parser("install", help="Install plugin manifest")
    p_inst.add_argument("manifest_path", help="Path to plugin.json")

    p_diag = plug_sub.add_parser("diagnose", help="Diagnose plugin")
    p_diag.add_argument("plugin_id", help="Plugin ID")

    p_chk = plug_sub.add_parser("check", help="Check plugin health")
    p_chk.add_argument("plugin_id", help="Plugin ID")

    p_dis = plug_sub.add_parser("disable", help="Disable plugin")
    p_dis.add_argument("plugin_id", help="Plugin ID")

    # Migrate
    migrate_p = subparsers.add_parser("migrate", help="Run idempotent database migration")

    # Launch
    launch_p = subparsers.add_parser("launch", help="Launch platform services and session")
    launch_p.add_argument("--client", default="auto")
    launch_p.add_argument("--project", required=True)
    launch_p.add_argument("-QuickStart", "-quickstart", "--quickstart", "--quick-start", action="store_true", help="Quick start mode")

    # Session
    sess_p = subparsers.add_parser("session", help="Session lifecycle")
    sess_sub = sess_p.add_subparsers(dest="sess_action")
    s_start = sess_sub.add_parser("start", help="Start session")
    s_start.add_argument("--project")
    s_end = sess_sub.add_parser("end", help="End session")
    s_end.add_argument("--project")

    # EndDay
    endday_p = subparsers.add_parser("endday", help="Run end-of-day maintenance")
    endday_p.add_argument("--project", required=True)

    # Task
    task_p = subparsers.add_parser("task", help="Task board operations")
    task_p.add_argument("--api-url", default=None, help="Optional API URL for active instance routing")
    task_sub = task_p.add_subparsers(dest="task_action")

    board_p = task_sub.add_parser("board", help="Display task board")
    board_p.add_argument("--project", help="Project ID; defaults to the local project manifest")
    board_p.add_argument("--json", action="store_true", help="Return the project board as JSON")

    next_p = task_sub.add_parser("next", help="Select and start next task")
    next_p.add_argument("--project", help="Project ID; defaults to the local project manifest")
    next_p.add_argument("--json", action="store_true", help="Return the selected task as JSON")

    add_p = task_sub.add_parser("add", help="Add new task")
    add_p.add_argument("title", help="Task title")
    add_p.add_argument("--mode", default="coding", choices=["coding", "reasoning", "bulk"])
    add_p.add_argument("--steps", type=int, default=1)
    add_p.add_argument("--project")
    add_p.add_argument("--depends-on", help="Task ID dependency in the same project")

    done_p = task_sub.add_parser("complete", help="Complete active or specified task")
    done_p.add_argument("task_id", nargs="?", default=None)
    done_p.add_argument("--project")
    done_p.add_argument("--expected-version", type=int, help="Reject completion if the task changed since it was read")

    step_p = task_sub.add_parser("step", help="Advance a task by one step or to a step number")
    step_p.add_argument("task_id", nargs="?", default=None)
    step_p.add_argument("--project", required=True)
    step_p.add_argument("--step-number", type=int, default=0)
    step_p.add_argument("--json", action="store_true")
    step_p.add_argument("--expected-version", type=int, help="Reject the step if the task changed since it was read")

    edit_p = task_sub.add_parser("edit", help="Edit a task in one project")
    edit_p.add_argument("task_id")
    edit_p.add_argument("--project", required=True)
    edit_p.add_argument("--title")
    edit_p.add_argument("--mode", choices=["coding", "reasoning", "bulk"])
    edit_p.add_argument("--steps", type=int)
    edit_p.add_argument("--expected-version", type=int, help="Reject the edit if the task changed since it was read")

    pause_p = task_sub.add_parser("pause", help="Pause an active task")
    pause_p.add_argument("task_id", nargs="?")
    pause_p.add_argument("--project", required=True)
    pause_p.add_argument("--expected-version", type=int, help="Reject pause if the task changed since it was read")

    skip_p = task_sub.add_parser("skip", help="Skip an active task")
    skip_p.add_argument("task_id", nargs="?")
    skip_p.add_argument("--project", required=True)
    skip_p.add_argument("--reason", default="")
    skip_p.add_argument("--expected-version", type=int, help="Reject skip if the task changed since it was read")

    resume_p = task_sub.add_parser("resume", help="Resume a paused task")
    resume_p.add_argument("task_id", nargs="?")
    resume_p.add_argument("--project", required=True)
    resume_p.add_argument("--expected-version", type=int, help="Reject resume if the task changed since it was read")

    # Memory
    mem_p = subparsers.add_parser("memory", help="Memory operations")
    mem_sub = mem_p.add_subparsers(dest="mem_action")

    get_p = mem_sub.add_parser("get", help="Get memory content")
    get_p.add_argument("name", choices=["MEMORY", "DECISIONS", "LESSONS", "PATTERNS", "PERSONA", "SCENARIO"])
    get_p.add_argument("--type", default="devcore", help="Scenario task type")

    search_p = mem_sub.add_parser("query", help="Query memory hierarchy")
    search_p.add_argument("query_text", help="Query string")
    search_p.add_argument("--type", default="devcore", help="Scenario task type")

    # Events
    evt_p = subparsers.add_parser("events", help="Event bus operations")
    evt_sub = evt_p.add_subparsers(dest="evt_action")

    tail_p = evt_sub.add_parser("tail", help="Tail recent events")
    tail_p.add_argument("--limit", type=int, default=20)

    pub_p = evt_sub.add_parser("publish", help="Publish event")
    pub_p.add_argument("type", help="Event type")
    pub_p.add_argument("payload", help="JSON payload string")

    args = parser.parse_args()

    if args.command == "diagnose":
        if args.fix and not args.dry_run:
            parser.error("diagnostic repairs are unavailable; use --fix --dry-run to inspect")
        from devcore_engine.infra.diagnose import DiagnosticEngine
        diag = DiagnosticEngine()
        report = diag.run_diagnostics()
        fails = [c for c in report.get("checks", []) if c.get("status") == "FAIL"]
        if getattr(args, "dry_run", False) and not getattr(args, "json", False):
            print("MODE DRY-RUN ACTIVE")
        print(json.dumps(report, indent=2))
        if getattr(args, "gate", False) and fails:
            sys.exit(1)


    elif args.command == "skills":
        from devcore_engine.services.skills import SkillService
        ss = SkillService()
        if args.skill_action == "list":
            skills = ss.list_skills()
            print(json.dumps(skills, indent=2))

    elif args.command == "knowledge":
        from devcore_engine.services.knowledge import KnowledgeGraph
        kg = KnowledgeGraph()
        if args.kg_action == "stats":
            print(json.dumps(kg.get_stats(), indent=2))

    elif args.command == "plugins":
        from devcore_engine.services.plugins import PluginService
        ps = PluginService()
        if args.plug_action == "list":
            print(json.dumps(ps.get_plugin_list_json(), indent=2))
        elif args.plug_action == "health":
            print(json.dumps(ps.health(), indent=2))
        elif args.plug_action == "install":
            print(json.dumps(ps.install(args.manifest_path), indent=2))
        elif args.plug_action == "diagnose":
            print(json.dumps(ps.diagnose(args.plugin_id), indent=2))
        elif args.plug_action == "check":
            print(json.dumps(ps.check(args.plugin_id), indent=2))
        elif args.plug_action == "disable":
            print(json.dumps(ps.disable(args.plugin_id), indent=2))

    elif args.command == "migrate":
        migrator = DevCoreMigrator()
        res = migrator.run_all()
        print(json.dumps(res, indent=2))

    elif args.command == "launch":
        from devcore_engine.lifecycle.launch import PlatformLauncher
        launcher = PlatformLauncher()
        res = launcher.launch(client=args.client, project_id=args.project)
        print(json.dumps(res, indent=2))

    elif args.command == "session":
        from devcore_engine.lifecycle.session import SessionManager
        project_id = args.project or project_from_directory()
        if not project_id:
            print(json.dumps({"status": "skipped", "reason": "project context unavailable"}))
            return
        sm = SessionManager()
        context = RequestContext(project_id=project_id)
        if args.sess_action == "start":
            res = sm.start_session(context)
        else:
            res = sm.end_session(context)
        print(json.dumps(res, indent=2))

    elif args.command == "endday":
        from devcore_engine.lifecycle.endday import EndDayManager
        edm = EndDayManager()
        context = RequestContext(project_id=args.project)
        res = edm.run_endday(context)
        print(json.dumps(res, indent=2))

    elif args.command == "task":
        if args.task_action is None:
            parser.error("task action is required")
        project_id = args.project or project_from_directory()
        if not project_id:
            parser.error("task requires --project or a .devcore/project.json in the working directory")
        args.project = project_id
        api_url = getattr(args, "api_url", None) or os.environ.get("DEVCORE_API_URL")
        if os.environ.get("DEVCORE_CLIENT_MODE") == "1" and not api_url:
            parser.error("Direct database access is forbidden in client mode; configure --api-url or DEVCORE_API_URL")
        if api_url:
            _execute_task_cli_via_api(api_url.rstrip("/"), args, parser)
            return
        ts = TaskService()
        if args.task_action == "board":
            board = ts.get_board(args.project)
            if args.json:
                print(json.dumps(board, ensure_ascii=False))
            else:
                print(f"=== TASK BOARD ({board['project']}) ===")
                print(f"Current task: {board['current_task'] or 'None'}\n")
                for t in board["tasks"]:
                    print(f"  [{t['status'].upper():11s}] {t['id']}: {t['title']} ({t['steps_done']}/{t['steps_total']} steps)")

        elif args.task_action == "next":
            active = ts.next_task(args.project)
            if args.json:
                print(json.dumps(active, ensure_ascii=False))
            elif active:
                print(f"Active task: [{active['id']}] {active['title']}")
            else:
                print("No pending tasks available.")

        elif args.task_action == "add":
            t = ts.add_task(args.title, mode=args.mode, steps=args.steps,
                            project_id=args.project, depends_on=args.depends_on)
            print(f"Created task: [{t['id']}] {t['title']}")

        elif args.task_action == "complete":
            try:
                comp = ts.complete_task(args.task_id, project_id=args.project,
                                        expected_version=args.expected_version)
            except ValueError as exc:
                parser.error(str(exc))
            if comp:
                print(f"Completed task: [{comp['id']}] {comp['title']}")
            elif args.task_id:
                parser.error("task not found or not completable in project")
            else:
                print("No active task to complete.")

        elif args.task_action == "step":
            if args.step_number < 0:
                parser.error("--step-number must be zero or positive")
            try:
                task = ts.step_task(
                    args.task_id,
                    step_number=args.step_number or None,
                    project_id=args.project,
                    expected_version=args.expected_version,
                )
            except ValueError as exc:
                parser.error(str(exc))
            if args.json:
                print(json.dumps({"task": task, "complete": bool(task and task["status"] == "done")}, ensure_ascii=False))
            elif task:
                print(f"Task [{task['id']}] {task['steps_done']}/{task['steps_total']} ({task['status']})")
            else:
                print("No pending or active task available.")

        elif args.task_action == "edit":
            if all(value is None for value in (args.title, args.mode, args.steps)):
                parser.error("task edit requires --title, --mode or --steps")
            try:
                task = ts.edit_task(args.task_id, title=args.title, mode=args.mode,
                                    steps_total=args.steps, project_id=args.project,
                                    expected_version=args.expected_version)
            except ValueError as exc:
                parser.error(str(exc))
            if task is None:
                parser.error("task not found in project")
            print(f"Edited task: [{task['id']}] {task['title']}")

        elif args.task_action == "pause":
            try:
                task = ts.pause_task(args.task_id, project_id=args.project,
                                     expected_version=args.expected_version)
            except ValueError as exc:
                parser.error(str(exc))
            if task is None:
                parser.error("no matching active task in project")
            print(f"Paused task: [{task['id']}] {task['title']}")

        elif args.task_action == "skip":
            try:
                task = ts.skip_task(args.task_id, reason=args.reason, project_id=args.project,
                                    expected_version=args.expected_version)
            except ValueError as exc:
                parser.error(str(exc))
            if task is None:
                parser.error("no matching active task in project")
            print(f"Skipped task: [{task['id']}] {task['title']}")

        elif args.task_action == "resume":
            try:
                task = ts.resume_task(args.task_id, project_id=args.project,
                                      expected_version=args.expected_version)
            except ValueError as exc:
                parser.error(str(exc))
            if task is None:
                parser.error("no matching paused task in project")
            print(f"Resumed task: [{task['id']}] {task['title']}")

    elif args.command == "memory":
        if args.mem_action == "get":
            ms = MemoryService()
            print(ms.get_text(args.name, args.type))
        elif args.mem_action == "query":
            mh = MemoryHierarchy()
            print(mh.query(args.query_text, args.type))

    elif args.command == "events":
        bus = EventBus()
        if args.evt_action == "tail":
            evts = bus.tail(args.limit)
            for e in evts:
                print(f"[{e['created_at']}] [{e['source']}] {e['event_type']}: {e['payload']}")
        elif args.evt_action == "publish":
            try:
                payload_obj = json.loads(args.payload)
            except Exception:
                payload_obj = args.payload
            eid = bus.publish(args.type, payload_obj)
            print(f"Published event: {eid}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
