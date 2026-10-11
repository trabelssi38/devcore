"""Launch pinned individual MCP snapshot over stdio; never load legacy hooks."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import runpy
import sys

sys.dont_write_bytecode = True
from urllib.parse import urlsplit


def prepare(bundle: Path, pin: str, origin: str, credential: Path, project: str,
            access="disabled", audit=False, delete=False, budget=12000, timeout=10, *, transitions=False) -> dict:
    if access not in {"disabled", "read", "write"} or type(audit) is not bool or type(delete) is not bool or type(transitions) is not bool:
        raise ValueError("Explicit capabilities required")
    if delete and access != "write":
        raise ValueError("Deletion requires explicit write access")
    if transitions and access != "write":
        raise ValueError("Transitions require explicit write access")
    parsed = urlsplit(origin)
    if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or parsed.port is None:
        raise ValueError("Candidate API requires an explicit 127.0.0.1 HTTP port")
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("candidate_launch_checks", Path(__file__).with_name("launch_individual_candidate.py"))
    checks = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checks)
    bundle = checks.verified_bundle(bundle, pin)
    engine = checks.installed_engine()
    credential = checks.checked_path(credential, directory=False)
    from devcore_engine.clients.individual_tasks import IndividualApiClient
    client = IndividualApiClient(origin, credential, project, task_access=access,
                                 audit_enabled=audit, delete_enabled=delete, transitions_enabled=transitions, max_bytes=budget, timeout=timeout)
    client._authorization()  # NTFS and shape checked before MCP admission; never logged.
    os.environ.update({
        "DEVCORE_MCP_AUTH_PROFILE": "individual", "DEVCORE_MCP_API_URL": client.origin,
        "DEVCORE_MCP_CREDENTIAL_FILE": str(credential), "DEVCORE_MCP_PROJECT": client.project,
        "DEVCORE_MCP_TASK_ACCESS": access, "DEVCORE_MCP_TASK_AUDIT": "1" if audit else "0",
        "DEVCORE_MCP_TASK_DELETE": "1" if delete else "0",
        "DEVCORE_MCP_TASK_TRANSITIONS": "1" if transitions else "0",
        "DEVCORE_MCP_READ_ONLY": "0" if access == "write" else "1",
        "DEVCORE_CONTEXT_MAX_BYTES": str(budget), "DEVCORE_MCP_API_TIMEOUT_SECONDS": str(timeout),
    })
    return {"profile": "individual", "manifest_sha256": pin, "engine": str(engine),
            "project": client.project, "task_access": access, "audit": audit, "delete": delete, "transitions": transitions,
            "operationally_qualified": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--credential-file", type=Path, required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--tasks", choices=["disabled", "read", "write"], default="disabled")
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--delete", action="store_true")
    parser.add_argument("--transitions", action="store_true")
    parser.add_argument("--context-max-bytes", type=int, default=12000)
    parser.add_argument("--timeout-seconds", type=int, default=10)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        report = prepare(args.bundle, args.manifest_sha256, args.api_url, args.credential_file,
                         args.project, args.tasks, args.audit, args.delete, args.context_max_bytes, args.timeout_seconds, transitions=args.transitions)
    except Exception:
        print(json.dumps({"success": False, "code": "candidate_mcp_preflight_refused"}), file=sys.stderr)
        return 2
    if args.check:
        print(json.dumps(report, separators=(",", ":")))
        return 0
    # No diagnostic output on stdout: it belongs exclusively to MCP JSON-RPC.
    runpy.run_path(str(args.bundle / "MCP/devcore-scripts/server.py"), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
