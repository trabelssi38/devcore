"""Run an isolated P3 migration rehearsal without touching operational data."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import shutil
import sqlite3
import tempfile


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def check_sqlite(path: Path) -> dict:
    db = sqlite3.connect(path)
    try:
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = len(db.execute("PRAGMA foreign_key_check").fetchall())
        names = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        tables = {}
        virtual_tables = {}
        for name in names:
            try:
                tables[name] = db.execute(f"SELECT COUNT(*) FROM [{name}]").fetchone()[0]
            except sqlite3.OperationalError as exc:
                if "no such module" not in str(exc).lower():
                    raise
                tables[name] = None
                virtual_tables[name] = str(exc)
    finally:
        db.close()
    return {"integrity": integrity, "foreign_key_violations": foreign_keys,
            "tables": tables, "virtual_tables_unavailable": virtual_tables}


def rehearse(snapshot: Path, graph: Path, candidate_validation: Path, output: Path) -> dict:
    snapshot = snapshot.resolve(strict=True)
    graph = graph.resolve(strict=True)
    candidate_validation = candidate_validation.resolve(strict=True)
    output = output.resolve()
    manifest = json.loads((snapshot / "manifest.json").read_text(encoding="utf-8"))
    candidate = json.loads(candidate_validation.read_text(encoding="utf-8"))
    checks: dict[str, dict] = {}
    blockers: list[str] = []

    checks["snapshot_stable"] = {"passed": manifest.get("source_stable") is True,
                                  "source": manifest.get("source_stable")}
    if not checks["snapshot_stable"]["passed"]:
        blockers.append("snapshot_not_stable")

    with tempfile.TemporaryDirectory(prefix="devcore-p3-") as temp:
        rehearsal = Path(temp)
        restored: list[tuple[Path, Path]] = []
        for relative in manifest.get("sqlite", {}):
            source = snapshot / "local" / relative
            target = rehearsal / "restore" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            expected = manifest["sqlite"][relative]["sha256"]
            actual = digest(target)
            restored.append((target, rehearsal / "rollback" / relative))
            checks[f"restore:{relative}"] = {"passed": actual == expected and check_sqlite(target)["integrity"] == "ok",
                                               "sha256_match": actual == expected,
                                               **check_sqlite(target)}
            if not checks[f"restore:{relative}"]["passed"]:
                blockers.append("restore_validation_failed")
        # Simulate a cutover and rollback using only the temporary restore.
        if restored:
            active, rollback = restored[0]
            rollback.parent.mkdir(parents=True, exist_ok=True)
            before = digest(active)
            shutil.copy2(active, rollback)
            replacement = rehearsal / "candidate.db"
            shutil.copy2(active, replacement)
            replacement.replace(active)
            active.unlink()
            rollback.replace(active)
            checks["rollback_simulation"] = {"passed": digest(active) == before,
                                              "restored_sha256": digest(active),
                                              "expected_sha256": before}
            if not checks["rollback_simulation"]["passed"]:
                blockers.append("rollback_simulation_failed")
        else:
            checks["rollback_simulation"] = {"passed": False, "reason": "no_sqlite_in_snapshot"}
            blockers.append("rollback_simulation_unavailable")

    graph_check = check_sqlite(graph)
    checks["graph_projection"] = {"passed": graph_check["integrity"] == "ok" and graph_check["foreign_key_violations"] == 0,
                                   **graph_check, "path": str(graph)}
    if not checks["graph_projection"]["passed"]:
        blockers.append("graph_projection_invalid")

    checks["candidate_validation"] = {
        "passed": candidate.get("integrity_check") == "ok"
        and candidate.get("foreign_key_check", {}).get("total") == 0
        and candidate.get("graph_fk_preview", {}).get("foreign_key_violations", 0) == 0
        and candidate.get("project_review_required", 0) == 0
        and candidate.get("task_review_required", 0) == 0,
        "integrity_check": candidate.get("integrity_check"),
        "application_foreign_key_violations": candidate.get("foreign_key_check", {}).get("total"),
        "unresolved_review_items": candidate.get("project_review_required", 0) + candidate.get("task_review_required", 0),
    }
    if not checks["candidate_validation"]["passed"]:
        blockers.append("candidate_application_constraints_unresolved")
    checks["postgresql_global_stack"] = {"passed": False, "state": "deferred",
                                          "reason": "No qualified PostgreSQL target supplied to rehearsal"}
    blockers.append("postgresql_global_stack_not_qualified")
    checks["operational_cutover"] = {"passed": False, "state": "deferred",
                                      "reason": "Rehearsal is isolated and does not freeze or replace live data"}
    blockers.append("operational_cutover_deferred")

    report = {
        "report_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "stage": "P3_independent_rehearsal",
        "status": "rehearsal_passed_with_blockers" if not any(
            key in blockers for key in ("snapshot_not_stable", "restore_validation_failed", "rollback_simulation_failed", "graph_projection_invalid")
        ) else "rehearsal_failed",
        "ready_for_cutover": False,
        "snapshot": str(snapshot),
        "graph_projection": str(graph),
        "candidate_validation": str(candidate_validation),
        "checks": checks,
        "blockers": sorted(set(blockers)),
        "policy": "isolated rehearsal only; no operational database or live service is modified",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--candidate-validation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = rehearse(args.snapshot, args.graph, args.candidate_validation, args.output)
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["status"] == "rehearsal_passed_with_blockers" else 2


if __name__ == "__main__":
    raise SystemExit(main())
