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
from typing import Any

from devcore_engine.services.memory import MemoryService
from devcore_engine.services.memory_hierarchy import MemoryHierarchy
from devcore_engine.services.tasks import TaskService
from devcore_engine.services.events import EventBus
from devcore_engine.migrate_to_unified_db import DevCoreMigrator


def main() -> None:
    parser = argparse.ArgumentParser(prog="devcore", description="DEV_CORE Unified CLI Engine")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Diagnose
    diag_p = subparsers.add_parser("diagnose", help="Run system diagnostics")

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
    launch_p.add_argument("--project", default="devcore")

    # Session
    sess_p = subparsers.add_parser("session", help="Session lifecycle")
    sess_sub = sess_p.add_subparsers(dest="sess_action")
    s_start = sess_sub.add_parser("start", help="Start session")
    s_start.add_argument("--project", default="devcore")
    s_end = sess_sub.add_parser("end", help="End session")
    s_end.add_argument("--project", default="devcore")

    # EndDay
    endday_p = subparsers.add_parser("endday", help="Run end-of-day maintenance")
    endday_p.add_argument("--project", default="devcore")

    # Task
    task_p = subparsers.add_parser("task", help="Task board operations")
    task_sub = task_p.add_subparsers(dest="task_action")

    board_p = task_sub.add_parser("board", help="Display task board")
    board_p.add_argument("--project", default="devcore", help="Project ID")

    next_p = task_sub.add_parser("next", help="Select and start next task")
    next_p.add_argument("--project", default="devcore", help="Project ID")

    add_p = task_sub.add_parser("add", help="Add new task")
    add_p.add_argument("title", help="Task title")
    add_p.add_argument("--mode", default="coding", choices=["coding", "reasoning", "bulk"])
    add_p.add_argument("--steps", type=int, default=1)
    add_p.add_argument("--project", default="devcore")

    done_p = task_sub.add_parser("complete", help="Complete active or specified task")
    done_p.add_argument("task_id", nargs="?", default=None)
    done_p.add_argument("--project", default="devcore")

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
        from devcore_engine.infra.diagnose import DiagnosticEngine
        diag = DiagnosticEngine()
        report = diag.run_diagnostics()
        print(json.dumps(report, indent=2))

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
        sm = SessionManager()
        if args.sess_action == "start":
            res = sm.start_session(args.project)
        else:
            res = sm.end_session(args.project)
        print(json.dumps(res, indent=2))

    elif args.command == "endday":
        from devcore_engine.lifecycle.endday import EndDayManager
        edm = EndDayManager()
        res = edm.run_endday(args.project)
        print(json.dumps(res, indent=2))

    elif args.command == "task":
        ts = TaskService()
        if args.task_action == "board":
            board = ts.get_board(args.project)
            print(f"=== TASK BOARD ({board['project']}) ===")
            print(f"Current task: {board['current_task'] or 'None'}\n")
            for t in board["tasks"]:
                print(f"  [{t['status'].upper():11s}] {t['id']}: {t['title']} ({t['steps_done']}/{t['steps_total']} steps)")

        elif args.task_action == "next":
            active = ts.next_task(args.project)
            if active:
                print(f"Active task: [{active['id']}] {active['title']}")
            else:
                print("No pending tasks available.")

        elif args.task_action == "add":
            t = ts.add_task(args.title, mode=args.mode, steps=args.steps, project_id=args.project)
            print(f"Created task: [{t['id']}] {t['title']}")

        elif args.task_action == "complete":
            comp = ts.complete_task(args.task_id, project_id=args.project)
            if comp:
                print(f"Completed task: [{comp['id']}] {comp['title']}")
            else:
                print("No active task to complete.")

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
