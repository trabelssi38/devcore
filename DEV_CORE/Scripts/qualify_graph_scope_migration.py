"""Qualify graph migration and RLS against an isolated PostgreSQL cluster."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile

import pg8000.dbapi


PG_BIN = Path("C:/Program Files/PostgreSQL/17/bin")
DDL = Path(__file__).resolve().parents[1] / (
    "devcore_engine/persistence/migrations/20261017_legacy_graph_scope.sql")
USAGE_DDL = DDL.with_name("20261017_project_llm_usage.sql")
QUALIFICATION = Path("E:/DevCoreRuntime/qualification")
PORT = 55435


def command(args: list[str], *, detached: bool = False) -> None:
    output = ({"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
              if detached else {"capture_output": True, "text": True})
    result = subprocess.run(args, timeout=120, **output)
    if result.returncode:
        raise RuntimeError(f"{Path(args[0]).name} failed ({result.returncode}): "
                           + ((result.stderr or result.stdout or "")[-1500:]))


def connect(user: str):
    return pg8000.dbapi.connect(user=user, host="127.0.0.1", port=PORT,
                                database="postgres")


def visible(user: str, project: str | None) -> tuple[int, int, int]:
    db = connect(user)
    try:
        cursor = db.cursor()
        if project is not None:
            cursor.execute("SELECT set_config('app.current_project_id', %s, true)", (project,))
        counts = []
        for table in ("legacy_kg_nodes", "legacy_kg_edges", "project_graph_stats"):
            cursor.execute(f"SELECT count(*) FROM {table}")
            counts.append(cursor.fetchone()[0])
        return tuple(counts)
    finally:
        db.rollback()
        db.close()


def main() -> int:
    base = QUALIFICATION.resolve(strict=True)
    root = Path(tempfile.mkdtemp(prefix="pg-graph-scope-", dir=base)).resolve(strict=True)
    if root.parent != base:
        raise RuntimeError("Isolated cluster path escaped qualification root")
    os.environ["DEVCORE_LOCAL_ROOT"] = str(root / "local")
    os.environ["DEVCORE_DATA_ROOT"] = str(root / "data-root")
    data = root / "postgres"
    started = False
    qualified = False
    try:
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1", PORT)) == 0:
                raise RuntimeError("Isolated PostgreSQL port is occupied")
        command([str(PG_BIN / "initdb.exe"), "-D", str(data), "-U", "graph_owner",
                 "-A", "trust", "--encoding=UTF8", "--no-instructions"])
        started = True
        command([str(PG_BIN / "pg_ctl.exe"), "-D", str(data), "-l", str(root / "postgres.log"),
                 "-o", f"-h 127.0.0.1 -p {PORT}", "start", "-w"], detached=True)
        owner = connect("graph_owner")
        try:
            cur = owner.cursor()
            cur.execute("CREATE ROLE devcore_app_qualification LOGIN NOBYPASSRLS")
            cur.execute("CREATE TABLE projects(id text PRIMARY KEY)")
            cur.execute("INSERT INTO projects VALUES ('devcore'),('scripts')")
            cur.execute("CREATE TABLE legacy_kg_nodes(id text PRIMARY KEY,type text NOT NULL,label text NOT NULL,properties jsonb)")
            cur.execute("""CREATE TABLE legacy_kg_edges(id bigint PRIMARY KEY,
                from_node text REFERENCES legacy_kg_nodes(id),
                to_node text REFERENCES legacy_kg_nodes(id),type text NOT NULL,properties jsonb)""")
            cur.execute("GRANT USAGE ON SCHEMA public TO devcore_app_qualification")
            cur.execute("""INSERT INTO legacy_kg_nodes VALUES
                ('task:one','task','One','{}'),('file:one','file','One','{}'),
                ('project:scripts','project','Scripts','{}')""")
            cur.execute("""INSERT INTO legacy_kg_edges VALUES
                (1,'task:one','file:one','task_file','{}'),
                (2,'task:one','project:scripts','project_task','{}')""")
            owner.commit()
        finally:
            owner.close()
        common = [str(PG_BIN / "psql.exe"), "-X", "-v", "ON_ERROR_STOP=1", "-q",
                  "-h", "127.0.0.1", "-p", str(PORT), "-U", "graph_owner",
                  "-d", "postgres", "-f", str(DDL)]
        command(common)
        command(common)
        usage_command = [*common[:-1], str(USAGE_DDL)]
        command(usage_command)
        command(usage_command)
        if visible("devcore_app_qualification", None) != (0, 0, 0):
            raise RuntimeError("Graph rows visible without project context")
        if visible("devcore_app_qualification", "devcore") != (2, 1, 1):
            raise RuntimeError("Devcore graph projection differs from fixture")
        if visible("devcore_app_qualification", "scripts") != (1, 0, 1):
            raise RuntimeError("Scripts graph projection differs from fixture")
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from devcore_engine.security.identity import Principal
        from devcore_engine.services.postgres_llm_usage import PostgresLlmUsageStore
        store = PostgresLlmUsageStore(
            f"postgresql://devcore_app_qualification@127.0.0.1:{PORT}/postgres")
        principal = Principal("fixture", "credential", "devcore", "task.mutate")
        if not store.record_gemini(principal, trace_id="trace-1", model="gemini-2.5-flash",
                                   prompt_tokens=7, completion_tokens=9):
            raise RuntimeError("Gemini usage was not recorded")
        if store.record_gemini(principal, trace_id="trace-1", model="gemini-2.5-flash",
                               prompt_tokens=7, completion_tokens=9):
            raise RuntimeError("Gemini usage idempotence failed")
        try:
            store.record_gemini(principal, trace_id="trace-1", model="gemini-2.5-flash",
                                prompt_tokens=8, completion_tokens=9)
        except ValueError:
            pass
        else:
            raise RuntimeError("Conflicting Gemini trace was accepted")
        for project, expected in ((None, 0), ("devcore", 1), ("scripts", 0)):
            db = connect("devcore_app_qualification")
            try:
                cur = db.cursor()
                if project:
                    cur.execute("SELECT set_config('app.current_project_id', %s, true)",
                                (project,))
                cur.execute("SELECT count(*) FROM project_llm_usage")
                if cur.fetchone()[0] != expected:
                    raise RuntimeError("Gemini usage RLS did not isolate the project")
            finally:
                db.rollback()
                db.close()
        owner = connect("graph_owner")
        try:
            cur = owner.cursor()
            cur.execute("SELECT count(*) FROM legacy_kg_edges WHERE quarantine_reason='cross_project_endpoints'")
            if cur.fetchone()[0] != 1:
                raise RuntimeError("Cross-project edge was not quarantined")
        finally:
            owner.rollback()
            owner.close()
        qualified = True
        print(json.dumps({"status": "graph_scope_migration_qualified", "port": PORT,
                          "idempotent": True, "rls": "no_context_denied_and_projects_isolated",
                          "cross_project_edges_quarantined": 1,
                          "gemini_usage": "project_isolated_and_idempotent"}))
        return 0
    finally:
        if started:
            status = subprocess.run([str(PG_BIN / "pg_ctl.exe"), "-D", str(data), "status"],
                                    capture_output=True)
            if status.returncode == 0:
                command([str(PG_BIN / "pg_ctl.exe"), "-D", str(data), "stop", "-m", "fast", "-w"])
        if qualified and root.parent == base and root.exists():
            shutil.rmtree(root)


if __name__ == "__main__":
    raise SystemExit(main())
