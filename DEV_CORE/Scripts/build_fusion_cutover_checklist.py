"""Build a review-only cutover checklist from fusion validation reports."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build(candidate_validation: Path, graph_comparison: Path, reachability: Path, consumer_inventory: Path, scheduler_archive: Path, output: Path) -> dict:
    candidate = _load(candidate_validation)
    comparison = _load(graph_comparison)
    impact = _load(reachability)
    consumers = _load(consumer_inventory)
    scheduler = _load(scheduler_archive)
    checks = [
        {"id": "candidate_integrity", "passed": candidate.get("integrity_check") == "ok", "evidence": candidate.get("integrity_check")},
        {"id": "candidate_historical_fk_empty", "passed": (candidate.get("foreign_key_check") or {}).get("total") == 0, "evidence": (candidate.get("foreign_key_check") or {}).get("total")},
        {"id": "graph_sources_no_new_relations", "passed": comparison.get("only_other_distinct_relations") == 0, "evidence": comparison.get("only_other_distinct_relations")},
        {"id": "impact_reachability_equal", "passed": impact.get("impact_reachability_equal") is True, "evidence": impact.get("mismatch_nodes")},
        {"id": "graph_projection_fk", "passed": (candidate.get("graph_fk_preview") or {}).get("foreign_key_violations") == 0, "evidence": (candidate.get("graph_fk_preview") or {}).get("foreign_key_violations")},
        {"id": "task_projection_fk", "passed": (candidate.get("task_project_fk_preview") or {}).get("missing_after") == 0, "evidence": (candidate.get("task_project_fk_preview") or {}).get("missing_after")},
        {"id": "project_review_empty", "passed": candidate.get("project_review_required", 0) == 0, "evidence": candidate.get("project_review_required")},
        {"id": "scheduler_activation_forbidden", "passed": scheduler.get("jobs_activation_allowed") is False, "evidence": scheduler.get("jobs_activation_allowed")},
        {"id": "quarantine_empty", "passed": (candidate.get("graph_fk_preview") or {}).get("quarantine", 0) == 0, "evidence": (candidate.get("graph_fk_preview") or {}).get("quarantine")},
        {"id": "unresolved_task_conflicts_empty", "passed": candidate.get("task_review_required", 0) == 0, "evidence": candidate.get("task_review_required")},
        {"id": "consumer_contract_reviewed", "passed": consumers.get("summary", {}).get("raw_count", 0) == 0, "evidence": consumers.get("summary", {}).get("raw_count")},
    ]
    blockers = [check["id"] for check in checks if not check["passed"]]
    report = {
        "report_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "review_only",
        "ready_for_cutover": False,
        "checks": checks,
        "blockers": blockers,
        "policy": "a checklist never enables cutover; every blocker requires an explicit reviewed decision and an independently validated candidate",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"output": str(output), "status": report["status"], "ready_for_cutover": False, "blockers": blockers}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-validation", type=Path, required=True)
    parser.add_argument("--graph-comparison", type=Path, required=True)
    parser.add_argument("--reachability", type=Path, required=True)
    parser.add_argument("--consumer-inventory", type=Path, required=True)
    parser.add_argument("--scheduler-archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.candidate_validation, args.graph_comparison, args.reachability, args.consumer_inventory, args.scheduler_archive, args.output), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
