"""Validate explicit P2 migration decisions without applying them."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


REQUIRED_APPROVALS = (
    "project_ownership_and_roots",
    "task_field_conflict_winners",
    "quarantine_retention_policy",
    "postgresql_global_stack_readiness",
    "cutover_and_rollback_window",
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(proposals_path: Path, approvals_path: Path | None, output: Path) -> dict:
    proposals = _load(proposals_path)
    approvals = _load(approvals_path) if approvals_path else {}
    projects = [row for row in proposals.get("projects", []) if row.get("decision") == "review_required"]
    conflicts = proposals.get("field_conflicts", [])
    approved_projects = approvals.get("projects", {})
    approved_conflicts = {
        (row.get("project_id"), row.get("task_id"), row.get("field")): row
        for row in approvals.get("task_conflicts", [])
    }
    missing_projects = [row["project_id"] for row in projects
                        if not approved_projects.get(row["project_id"], {}).get("decision")
                        or not approved_projects.get(row["project_id"], {}).get("evidence")]
    missing_conflicts = [
        {"project_id": row["project_id"], "task_id": row["task_id"], "field": row["field"]}
        for row in conflicts
        if not approved_conflicts.get((row["project_id"], row["task_id"], row["field"]), {}).get("winner")
        or not approved_conflicts.get((row["project_id"], row["task_id"], row["field"]), {}).get("evidence")
    ]
    approvals_present = approvals.get("approvals", {})
    missing_approvals = [name for name in REQUIRED_APPROVALS
                         if not approvals_present.get(name, {}).get("approved_by")
                         or not approvals_present.get(name, {}).get("evidence")]
    blockers = []
    if missing_projects:
        blockers.append("project_decisions_missing")
    if missing_conflicts:
        blockers.append("task_conflict_decisions_missing")
    if missing_approvals:
        blockers.append("required_approvals_missing")
    deferred = [name for name in REQUIRED_APPROVALS
                if approvals.get("approvals", {}).get(name, {}).get("state") == "deferred"]
    status = "decisions_closed_with_deferrals" if not blockers and deferred else ("approved" if not blockers else "review_required")
    report = {
        "report_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "ready_for_cutover": False,
        "proposal_source": str(proposals_path.resolve()),
        "approval_source": str(approvals_path.resolve()) if approvals_path else None,
        "counts": {"projects_reviewed": len(projects) - len(missing_projects),
                    "projects_required": len(projects),
                    "conflicts_reviewed": len(conflicts) - len(missing_conflicts),
                    "conflicts_required": len(conflicts)},
        "missing_projects": missing_projects,
        "missing_conflicts": missing_conflicts,
        "missing_approvals": missing_approvals,
        "deferred_approvals": deferred,
        "blockers": blockers,
        "policy": "review only; this validator never changes candidates or operational databases",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposals", type=Path, required=True)
    parser.add_argument("--approvals", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = validate(args.proposals, args.approvals, args.output)
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["status"] in {"approved", "decisions_closed_with_deferrals"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
