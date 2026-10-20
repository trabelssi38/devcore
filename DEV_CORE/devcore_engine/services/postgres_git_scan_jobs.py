"""Submit one read-only Git scan per registered project revision."""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys
from uuid import uuid4

from devcore_engine.runs.postgres_store import PostgresRunStore
from devcore_engine.security.identity import Principal, ProjectAccessDenied, WRITE

from .postgres_automation_hooks import _principal, _registered_git_root


SHA = re.compile(r"^[0-9a-fA-F]{40}(?:[0-9a-fA-F]{24})?$")
TASK_ID = re.compile(r"^T-\d{1,8}$")
SCRIPT = Path(__file__).resolve().parents[2] / "Scripts" / "team_git_scan_job.py"


class PostgresGitScanJobs(PostgresRunStore):
    """Admit a safe command, durable run and submission history atomically."""

    def submit(self, principal: Principal, project: str, *, commit: str | None = None) -> dict:
        actor = _principal(principal, project, WRITE)
        if commit is not None and (not isinstance(commit, str) or SHA.fullmatch(commit) is None):
            raise ValueError("Full Git commit SHA required")
        if not SCRIPT.is_file():
            raise RuntimeError("Qualified Git scan script unavailable")
        with self._transaction(project) as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", ("git-scan:" + project,))
            cursor.execute("SELECT root_path FROM projects WHERE id=%s AND status='active'", (project,))
            row = cursor.fetchone()
            if row is None or not _registered_git_root(row[0]):
                raise ProjectAccessDenied("Active registered Git project required")
            root = Path(row[0]).resolve()
            try:
                head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                                      capture_output=True, text=True, timeout=10, check=False)
                if head.returncode != 0 or SHA.fullmatch(head.stdout.strip()) is None:
                    raise ValueError("Git HEAD unavailable")
                revision = (commit or head.stdout.strip()).lower()
                reachable = subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor",
                                            revision, "HEAD"], capture_output=True, timeout=10, check=False)
                if reachable.returncode != 0:
                    raise ValueError("Commit is not reachable from registered HEAD")
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise ValueError("Git verification unavailable") from exc
            key = f"job:git_scan:{revision}"
            cursor.execute("""SELECT id,status FROM runs WHERE project_id=%s
                AND idempotency_key=%s AND execution_ready""", (project, key))
            existing = cursor.fetchone()
            if existing is not None:
                return {"project": project, "run_id": existing[0],
                        "status": existing[1], "created": False}
            cursor.execute("""SELECT id,status FROM runs WHERE project_id=%s
                AND execution_ready AND metadata->>'job_kind'='git_scan'
                AND status IN ('queued','running','paused','waiting_approval')
                ORDER BY created_at LIMIT 1""", (project,))
            active = cursor.fetchone()
            if active is not None:
                return {"project": project, "run_id": active[0],
                        "status": active[1], "created": False}
            cursor.execute("""SELECT count(*) FROM runs WHERE project_id=%s
                AND status='queued' AND execution_ready""", (project,))
            if cursor.fetchone()[0] >= 50:
                raise RuntimeError("Project run queue is full")
            cursor.execute("""SELECT legacy_id FROM tasks WHERE project_id=%s
                AND status<>'deleted' AND legacy_id IS NOT NULL ORDER BY task_number""", (project,))
            task_ids = [item[0] for item in cursor.fetchall() if TASK_ID.fullmatch(item[0])]
            encoded = json.dumps(task_ids, separators=(",", ":"))
            if len(encoded.encode("utf-8")) > 12000:
                raise RuntimeError("Task snapshot exceeds Git scan bound")
            command = [sys.executable, str(SCRIPT), "--project", project,
                       "--root", str(root), "--revision", revision,
                       "--task-ids-json", encoded]
            run_id = "run-" + uuid4().hex[:12]
            cursor.execute("""INSERT INTO runs
                (id,project_id,title,status,command,timeout_seconds,attempt_number,
                 max_attempts,cancellation_requested,idempotency_key,actor,env,metadata,execution_ready)
                VALUES (%s,%s,'Git task scan','queued',%s::jsonb,60,0,1,false,
                        %s,%s,'{}'::jsonb,%s::jsonb,true)""",
                (run_id, project, json.dumps(command), key, actor,
                 json.dumps({"job_kind": "git_scan", "revision": revision})))
            cursor.execute("""INSERT INTO events
                (id,project_id,run_id,event_type,source,payload)
                VALUES (%s,%s,%s,'project_job.submitted','git_scan',%s::jsonb)""",
                ("event-" + uuid4().hex, project, run_id,
                 json.dumps({"revision": revision, "actor": actor})))
            return {"project": project, "run_id": run_id,
                    "status": "queued", "created": True}
