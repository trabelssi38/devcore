"""Prepare a guarded PostgreSQL import for the nine post-cutover legacy tasks.

The source is read-only. This command writes SQL for review and does not connect
to PostgreSQL. Run the SQL only with a migration role after a database backup.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sqlite3


EXPECTED_IDS = tuple(f"T-{number}" for number in range(393, 402))
EXPECTED_SOURCE_SHA256 = "e24133a8b4a15e0a62e83b4018eb6570ad49cbdf0032a355e6a399cacf10a4f4"


def quote_sql(value: str) -> str:
    if "\x00" in value:
        raise ValueError("PostgreSQL text cannot contain NUL")
    return "'" + value.replace("'", "''") + "'"


def prepare(source_path: Path, output_path: Path) -> dict:
    source_path = source_path.resolve(strict=True)
    output_path = output_path.resolve()
    if output_path.exists() or output_path.is_relative_to(source_path.parent):
        raise ValueError("SQL output must be new and outside the source directory")
    source_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()
    if source_sha256 != EXPECTED_SOURCE_SHA256:
        raise ValueError("Historical pilot source differs from the qualified copy")

    with sqlite3.connect(f"file:{source_path.as_posix()}?mode=ro&immutable=1", uri=True) as db:
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("Source integrity failed")
        rows = db.execute(
            "SELECT t.id, m.task_uuid, t.title, t.mode, t.status, t.version, "
            "t.steps_done, t.steps_total, t.depends_on, t.worktree, t.metadata, "
            "t.created_at, t.started_at, t.completed_at, t.updated_at "
            "FROM tasks t JOIN legacy_task_identity_map m "
            "ON m.project_id=t.project_id AND m.legacy_task_id=t.id "
            "WHERE t.project_id='devcore' AND t.id IN ("
            + ",".join("?" for _ in EXPECTED_IDS) + ") ORDER BY t.id",
            EXPECTED_IDS,
        ).fetchall()
    if tuple(row[0] for row in rows) != EXPECTED_IDS:
        raise ValueError("The nine expected tasks are not present exactly once")
    if any(row[4] != "done" or row[8] is not None for row in rows):
        raise ValueError("Unexpected task state or dependency")

    payload = []
    for row in rows:
        (legacy_id, task_uuid, title, mode, status, version, steps_done,
         steps_total, _depends_on, _worktree, metadata, created_at,
         started_at, completed_at, updated_at) = row
        try:
            metadata_value = json.loads(metadata or "{}")
        except json.JSONDecodeError:
            metadata_value = {"source_text": metadata}
        if not isinstance(metadata_value, dict):
            raise ValueError(f"Unexpected metadata for {legacy_id}")
        payload.append({
            "legacy_id": legacy_id, "task_uuid": task_uuid, "title": title,
            "mode": mode, "status": status, "version": version,
            "steps_done": steps_done, "steps_total": steps_total,
            "metadata": metadata_value, "created_at": created_at,
            "started_at": started_at, "completed_at": completed_at,
            "updated_at": updated_at,
        })

    encoded = quote_sql(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    sql = f"""-- Qualified source SHA-256: {source_sha256}
-- Requires a migration role with INSERT on public.tasks; no application role grant.
-- A PostgreSQL backup and maintenance window are required before execution.
BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;
SET LOCAL app.current_project_id = 'devcore';
LOCK TABLE public.tasks IN SHARE ROW EXCLUSIVE MODE;
CREATE TEMP TABLE delta_stage ON COMMIT DROP AS
SELECT * FROM jsonb_to_recordset({encoded}::jsonb) AS row(
    legacy_id text, task_uuid uuid, title text, mode text, status text,
    version integer, steps_done integer, steps_total integer, metadata jsonb,
    created_at timestamptz, started_at timestamptz, completed_at timestamptz,
    updated_at timestamptz);
DO $guard$
BEGIN
    IF (SELECT count(*) FROM delta_stage) <> 9
       OR NOT EXISTS (SELECT 1 FROM public.projects WHERE id='devcore')
       OR EXISTS (SELECT 1 FROM public.tasks t JOIN delta_stage d
                  ON t.task_uuid=d.task_uuid OR
                     (t.project_id='devcore' AND t.legacy_id=d.legacy_id))
    THEN RAISE EXCEPTION 'Historical task delta preflight failed; transaction aborted';
    END IF;
END
$guard$;
WITH numbered AS (
    SELECT d.*, (SELECT coalesce(max(task_number),0) FROM public.tasks
                 WHERE project_id='devcore')
              + row_number() OVER (ORDER BY d.legacy_id) AS new_number
    FROM delta_stage d
)
INSERT INTO public.tasks (
    task_uuid, project_id, task_number, legacy_id, title, mode, status,
    version, steps_done, steps_total, depends_on_uuid, worktree, metadata,
    created_at, started_at, completed_at, updated_at)
SELECT task_uuid, 'devcore', new_number, legacy_id, title, mode, status,
       version, steps_done, steps_total, NULL, NULL, metadata,
       created_at, started_at, completed_at, updated_at
FROM numbered;
DO $verify$
BEGIN
    IF (SELECT count(*) FROM public.tasks t JOIN delta_stage d
        ON t.task_uuid=d.task_uuid AND t.project_id='devcore'
        AND t.legacy_id=d.legacy_id AND t.title=d.title
        AND t.status=d.status AND t.metadata=d.metadata) <> 9
    THEN RAISE EXCEPTION 'Historical task delta verification failed; transaction aborted';
    END IF;
END
$verify$;
SELECT legacy_id, task_number FROM public.tasks
WHERE project_id='devcore' AND task_uuid IN (SELECT task_uuid FROM delta_stage)
ORDER BY legacy_id;
COMMIT;
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(sql, encoding="utf-8")
    return {"source_sha256": source_sha256, "task_count": len(payload),
            "legacy_ids": list(EXPECTED_IDS), "output": str(output_path),
            "executed": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.output), ensure_ascii=False))


if __name__ == "__main__":
    main()
