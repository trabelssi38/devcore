"""Explicit individual API client for context, tasks, audit and conditional mutations."""

import argparse
from pathlib import Path
import sys

from devcore_engine.clients.individual_tasks import IndividualApiClient
from devcore_engine.services.project_context import encode_context


def output(result):
    sys.stdout.buffer.write((encode_context(result) + "\n").encode("utf-8"))


class ClientParser(argparse.ArgumentParser):
    def error(self, message):
        # Never echo rejected arguments, paths or accidentally supplied secret values.
        output({"success": False, "code": "invalid_arguments",
                "error": "Explicit API origin, credential file, project and valid command arguments required"})
        self.exit(2)


def main(argv=None):
    parser = ClientParser(description=__doc__)
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--credential-file", type=Path, required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--context-max-bytes", type=int, default=12000)
    parser.add_argument("--timeout-seconds", type=int, default=10)
    commands = parser.add_subparsers(dest="command", required=True, parser_class=ClientParser)
    context = commands.add_parser("context", help="Read the bounded project card and applicable decisions")
    context.add_argument("--budget-bytes", type=int)
    context.add_argument("--query", default="")
    tasks = commands.add_parser("tasks", help="Read one authorized page; no global count")
    tasks.add_argument("--limit", type=int, default=20)
    tasks.add_argument("--offset", type=int, default=0)
    audit = commands.add_parser("audit", help="Read one authorized audit page; project owner and task.audit.read required")
    audit.add_argument("--limit", type=int, default=20)
    audit.add_argument("--task-id")
    audit.add_argument("--before-id")
    done = commands.add_parser("done", help="Complete the named task conditionally; no automatic retry")
    done.add_argument("--task-id", required=True)
    done.add_argument("--expected-version", type=int, required=True)
    deletion = commands.add_parser("delete", help="Hide the named task conditionally, retaining history; no retry")
    deletion.add_argument("--task-id", required=True)
    deletion.add_argument("--expected-version", type=int, required=True)
    for command in ("pause", "resume"):
        transition = commands.add_parser(command, help="Conditional named transition; no retry")
        transition.add_argument("--task-id", required=True)
        transition.add_argument("--expected-version", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        access = {"context": "disabled", "audit": "disabled", "tasks": "read", "done": "write", "delete": "write", "pause": "write", "resume": "write"}[args.command]
        client = IndividualApiClient(args.api_url, args.credential_file, args.project,
                                     max_bytes=args.context_max_bytes, timeout=args.timeout_seconds,
                                     task_access=access, delete_enabled=args.command == "delete", audit_enabled=args.command == "audit", transitions_enabled=args.command in {"pause", "resume"})
    except (OSError, ValueError, TypeError):
        output({"success": False, "code": "invalid_configuration", "error": "Invalid explicit individual API configuration"})
        return 2
    arguments = {"project": args.project}
    if args.command == "context":
        arguments["query"] = args.query
        if args.budget_bytes is not None:
            arguments["budget_bytes"] = args.budget_bytes
        tool = "devcore_project_context"
    elif args.command == "tasks":
        arguments.update(limit=args.limit, offset=args.offset)
        tool = "devcore_task_status"
    elif args.command == "audit":
        arguments["limit"] = args.limit
        if args.task_id is not None:
            arguments["task_id"] = args.task_id
        if args.before_id is not None:
            arguments["before_id"] = args.before_id
        tool = "devcore_task_audit"
    else:
        arguments.update(task_id=args.task_id, expected_version=args.expected_version)
        tool = "devcore_task_" + args.command
    result = client.call(tool, arguments)
    output(result)
    if result.get("code") in {"invalid_arguments", "invalid_configuration"}:
        return 2
    return 1 if result.get("success") is False or "error" in result else 0


if __name__ == "__main__":
    raise SystemExit(main())
