"""Submit bounded RepoWise updates for one registered Git project."""

from __future__ import annotations

from datetime import UTC, datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from uuid import uuid4

from devcore_engine.runs.postgres_store import PostgresRunStore
from devcore_engine.security.identity import Principal, ProjectAccessDenied, WRITE

from .postgres_automation_hooks import _principal, _registered_git_root


SHA = re.compile(r"^[0-9a-fA-F]{40}(?:[0-9a-fA-F]{24})?$")
SCRIPT = Path(__file__).resolve().parents[2] / "Scripts" / "team_repowise_job.py"


class PostgresRepoWiseJobs(PostgresRunStore):
    def submit(self, principal: Principal, project: str) -> dict:
        actor = _principal(principal, project, WRITE)
        executable = os.environ.get("DEVCORE_REPOWISE_EXE") or shutil.which("repowise")
        if not executable or not Path(executable).is_absolute() or not Path(executable).is_file():
            raise RuntimeError("RepoWise executable unavailable")
        if not SCRIPT.is_file():
            raise RuntimeError("Managed RepoWise script unavailable")
        with self._transaction(project) as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", ("repowise:" + project,))
            cursor.execute("SELECT root_path FROM projects WHERE id=%s AND status='active'", (project,))
            row = cursor.fetchone()
            if row is None or not _registered_git_root(row[0]):
                raise ProjectAccessDenied("Active registered Git project required")
            root = Path(row[0]).resolve()
            try:
                result = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                                        capture_output=True, text=True, timeout=10, check=False)
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise ValueError("Git revision unavailable") from exc
            revision = result.stdout.strip().lower()
            if result.returncode != 0 or SHA.fullmatch(revision) is None:
                raise ValueError("Git revision unavailable")
            cursor.execute("""SELECT id,status FROM runs WHERE project_id=%s
                AND execution_ready AND metadata->>'job_kind'='repowise_index'
                AND status IN ('queued','running','paused','waiting_approval')
                ORDER BY created_at LIMIT 1""", (project,))
            active = cursor.fetchone()
            if active is not None:
                return {"project": project, "run_id": active[0],
                        "status": active[1], "created": False}
            cursor.execute("""SELECT id,finished_at FROM runs WHERE project_id=%s
                AND execution_ready AND metadata->>'job_kind'='repowise_index'
                AND metadata->>'revision'=%s AND status='succeeded'
                ORDER BY finished_at DESC LIMIT 1""", (project, revision))
            last = cursor.fetchone()
            now = datetime.now(UTC)
            if last is not None and last[1] is not None and (now - last[1]).total_seconds() < 86400:
                return {"project": project, "run_id": last[0],
                        "status": "succeeded", "created": False}
            key = f"job:repowise:{revision}:{now.date().isoformat()}"
            cursor.execute("SELECT id,status FROM runs WHERE project_id=%s AND idempotency_key=%s", (project, key))
            existing = cursor.fetchone()
            if existing is not None:
                return {"project": project, "run_id": existing[0],
                        "status": existing[1], "created": False}
            cursor.execute("""SELECT count(*) FROM runs WHERE project_id=%s
                AND status='queued' AND execution_ready""", (project,))
            if cursor.fetchone()[0] >= 50:
                raise RuntimeError("Project run queue is full")
            command = [sys.executable, str(SCRIPT), "--project", project, "--root", str(root),
                       "--revision", revision, "--executable", str(Path(executable).resolve())]
            if last is not None:
                command.append("--force")
            run_id = "run-" + uuid4().hex[:12]
            cursor.execute("""INSERT INTO runs
                (id,project_id,title,status,command,timeout_seconds,attempt_number,
                 max_attempts,cancellation_requested,idempotency_key,actor,env,metadata,execution_ready)
                VALUES (%s,%s,'RepoWise project index','queued',%s::jsonb,720,0,1,false,
                        %s,%s,'{}'::jsonb,%s::jsonb,true)""",
                (run_id, project, json.dumps(command), key, actor,
                 json.dumps({"job_kind": "repowise_index", "revision": revision})))
            cursor.execute("""INSERT INTO events
                (id,project_id,run_id,event_type,source,payload)
                VALUES (%s,%s,%s,'project_job.submitted','repowise_index',%s::jsonb)""",
                ("event-" + uuid4().hex, project, run_id,
                 json.dumps({"revision": revision, "actor": actor})))
            return {"project": project, "run_id": run_id,
                    "status": "queued", "created": True}
