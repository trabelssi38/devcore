import os
import json
import hashlib
import re
import sqlite3
import sys
import subprocess
from datetime import datetime
from pathlib import Path

DEVCORE_ROOT = Path(os.environ.get("DEVCORE_PLATFORM_ROOT", "C:/devcore/DEV_CORE"))
if not DEVCORE_ROOT.exists():
    DEVCORE_ROOT = Path(__file__).resolve().parents[3]
if str(DEVCORE_ROOT) not in sys.path:
    sys.path.insert(0, str(DEVCORE_ROOT))
from devcore_engine.db import get_data_root, get_local_data_root
DEVCORE_DATA = get_data_root()
DEVCORE_LOCAL = get_local_data_root()
DEVCORE_SCRIPTS = DEVCORE_ROOT / "Scripts"

def apply_rtk(text: str) -> str:
    """Apply RTK compression to tool outputs."""
    if not text:
        return text
    
    original_size = len(text)
    lines = text.splitlines()
    
    compressed_lines = []
    for line in lines:
        line = line.strip()
        if line:
            line = re.sub(r'\s{2,}', ' ', line)
            compressed_lines.append(line)
            
    if len(compressed_lines) > 500:
        head = compressed_lines[:200]
        tail = compressed_lines[-200:]
        trunc_count = len(compressed_lines) - 400
        compressed_lines = head + [f"\n... [RTK TRUNCATED {trunc_count} LINES] ...\n"] + tail
        
    compressed_text = '\n'.join(compressed_lines)
    new_size = len(compressed_text)
    
    if original_size > 0:
        savings = round(((original_size - new_size) / original_size) * 100, 1)
        try:
            kpi_file = DEVCORE_LOCAL / "Metrics" / "kpi.csv"
            kpi_file.parent.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            row = f"{timestamp},MCP_RTK_filter,{original_size},{new_size},{savings},YES\n"
            
            if not kpi_file.exists():
                with open(kpi_file, "w", encoding="utf-8") as f:
                    f.write("timestamp,file,json_chars,toon_chars,savings_pct,recommended\n")
            with open(kpi_file, "a", encoding="utf-8") as f:
                f.write(row)
        except Exception:
            pass
            
    return compressed_text

def run_python_script(script_path: Path, args: list = None) -> dict:
    """Execute a Python script using the active python interpreter."""
    cmd = [sys.executable, str(script_path)]
    if args:
        cmd.extend(args)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        stdout = apply_rtk(result.stdout)
        return {
            "success": result.returncode == 0,
            "stdout": stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Script timeout (> 5 min)"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def get_api_url() -> str | None:
    url = os.environ.get("DEVCORE_API_URL") or os.environ.get("DEVCORE_MCP_API_URL")
    if url:
        return url.strip().rstrip("/")
    return None

def require_project(project: str | None) -> str:
    if not isinstance(project, str) or not project.strip():
        raise ValueError("project is required")
    return project.strip()

def open_task_service():
    """Use an existing SQLite database without schema initialization in consultation mode."""
    if os.getenv("DEVCORE_CLIENT_MODE") == "1":
        raise PermissionError("Direct client access to the database is forbidden in client mode; route through the active API instance.")
    from devcore_engine.services.tasks import TaskService
    if os.getenv("DEVCORE_MCP_READ_ONLY") != "1":
        return TaskService()
    return open_existing_task_service(read_only=True)


def open_existing_task_service(*, read_only: bool):
    """Never create a database or change its schema as part of a tool operation."""
    if os.getenv("DEVCORE_CLIENT_MODE") == "1":
        raise PermissionError("Direct client access to the database is forbidden in client mode; route through the active API instance.")
    from devcore_engine.services.tasks import TaskService
    root = os.getenv("DEVCORE_LOCAL_ROOT")
    if not root or not Path(root).is_absolute():
        raise ValueError("An explicit absolute DEVCORE_LOCAL_ROOT is required")
    database = Path(root) / "devcore.db"
    if not database.is_file():
        raise ValueError("Task database does not exist")
    mode = "ro" if read_only else "rw"
    conn = sqlite3.connect(database.resolve().as_uri() + f"?mode={mode}", uri=True, timeout=5.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        if read_only:
            conn.execute("PRAGMA query_only = ON")
        return TaskService(conn)
    except Exception:
        conn.close()
        raise

def get_active_task_status(project: str | None = None) -> dict:
    try:
        project = require_project(project)
    except Exception as exc:
        return {"success": False, "error": str(exc)}

    api_url = get_api_url()
    if api_url:
        import urllib.request
        import urllib.error
        from urllib.parse import urlencode

        req_url = f"{api_url}/api/v1/tasks?" + urlencode({"project": project})
        req = urllib.request.Request(req_url, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return {"success": False, "error": f"project not found: {project}"}
            fallback_url = f"{api_url}/api/dashboard/tasks?" + urlencode({"project": project})
            try:
                with urllib.request.urlopen(urllib.request.Request(fallback_url, headers={"Accept": "application/json"}), timeout=10.0) as resp2:
                    data = json.loads(resp2.read().decode("utf-8"))
            except urllib.error.HTTPError as exc2:
                if exc2.code == 404:
                    return {"success": False, "error": f"project not found: {project}"}
                return {"success": False, "error": f"API request failed with HTTP {exc2.code}"}
            except Exception as e2:
                return {"success": False, "error": str(e2)}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

        tasks = data.get("tasks") if isinstance(data, dict) else data
        if not isinstance(tasks, list):
            return {"success": False, "error": "Invalid API task list response"}
        active = next((task for task in tasks if task.get("status") in {"in_progress", "active"}), None)
        done_count = sum(task.get("status") == "done" for task in tasks)
        status_str = f"Active task: {active['id'] if active else 'None'} ({active['title'] if active else 'N/A'})\n"
        status_str += f"Tasks progress: {done_count}/{len(tasks)} completed."
        return {"success": True, "stdout": status_str}

    try:
        service = open_task_service()
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    try:
        board = service.get_board(project)
        if not service.conn.execute("SELECT 1 FROM projects WHERE id = ?", (project,)).fetchone():
            raise ValueError(f"project not found: {project}")
        tasks = board["tasks"]
        active = next((task for task in tasks if task["status"] in {"in_progress", "active"}), None)
        done_count = sum(task["status"] == "done" for task in tasks)
        status_str = f"Active task: {active['id'] if active else 'None'} ({active['title'] if active else 'N/A'})\n"
        status_str += f"Tasks progress: {done_count}/{len(tasks)} completed."
        return {"success": True, "stdout": status_str}
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    finally:
        service.conn.close()

def complete_active_task(project: str | None = None, task_id: str | None = None,
                         expected_version: int | None = None) -> dict:
    """Complete a named task conditionally; retain implicit selection for old callers."""
    from devcore_engine.services.tasks import StaleTaskVersion

    try:
        project = require_project(project)
        if task_id is not None:
            if not isinstance(task_id, str) or not re.fullmatch(r"T-(?:\d+|GIT-[A-Za-z0-9]+)", task_id, re.IGNORECASE):
                raise ValueError("invalid task_id")
        if expected_version is not None:
            if type(expected_version) is not int or expected_version < 1:
                raise ValueError("expected_version must be a positive integer")
            if not task_id:
                raise ValueError("task_id is required with expected_version")
    except ValueError as exc:
        return {"success": False, "error": str(exc), "code": "invalid_arguments"}

    api_url = get_api_url()
    if api_url:
        import urllib.request
        import urllib.error

        if task_id is None:
            st = get_active_task_status(project)
            if not st.get("success"):
                return st
            m = re.search(r"Active task: (T-[A-Za-z0-9-]+)", st.get("stdout", ""))
            if not m or m.group(1) == "None":
                return {"success": False, "error": "Aucune tâche active à clore.", "code": "task_not_found"}
            task_id = m.group(1)

        body = json.dumps({"project": project, "id": task_id, "expected_version": expected_version}).encode("utf-8")
        req_url = f"{api_url}/api/done"
        req = urllib.request.Request(
            req_url,
            data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                return {
                    "success": True,
                    "stdout": f"Task {task_id} marked as DONE.",
                    "project": project,
                    "task_id": task_id,
                    "version": res.get("version"),
                }
        except urllib.error.HTTPError as exc:
            err_code = "mutation_failed"
            err_msg = f"HTTP {exc.code}"
            try:
                err_data = json.loads(exc.read().decode("utf-8"))
                detail = err_data.get("detail")
                if isinstance(detail, dict):
                    err_code = detail.get("code", err_code)
                    err_msg = detail.get("message", err_msg)
                elif isinstance(detail, str):
                    err_msg = detail
                if err_data.get("code"):
                    err_code = err_data.get("code")
            except Exception:
                pass
            if exc.code == 409 or err_code in {"stale_task_version", "task_version_unavailable"}:
                return {"success": False, "error": err_msg or "Task changed before completion", "code": err_code}
            if exc.code == 404 or err_code == "task_not_found":
                return {"success": False, "error": err_msg or "Task not found in project", "code": "task_not_found"}
            return {"success": False, "error": err_msg, "code": err_code}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # Direct database route (local development, migration, tests without API)
    try:
        service = open_existing_task_service(read_only=False)
    except (OSError, ValueError, sqlite3.Error, PermissionError) as exc:
        return {"success": False, "error": str(exc), "code": "task_store_unavailable"}
    try:
        if not service.conn.execute("SELECT 1 FROM projects WHERE id = ?", (project,)).fetchone():
            return {"success": False, "error": f"project not found: {project}", "code": "project_not_found"}
        explicit_task = task_id is not None
        if explicit_task:
            row = service.conn.execute(
                "SELECT * FROM tasks WHERE project_id=? AND id=? COLLATE NOCASE AND status <> 'deleted'",
                (project, task_id)).fetchone()
            if row is None:
                return {"success": False, "error": "Task not found in project", "code": "task_not_found"}
            task_id = row["id"]
            if expected_version is not None and "version" not in row.keys():
                return {"success": False, "error": "Task versions unavailable; migrate before conditional writes",
                        "code": "task_version_unavailable"}
        else:
            task_id = service.get_board(project)["current_task"]
        if not task_id:
            return {"success": False, "error": "Aucune tâche active à clore.", "code": "task_not_found"}
        completed = service.complete_task(task_id, project_id=project, expected_version=expected_version)
        if not completed:
            return {"success": False, "error": "Task changed before completion", "code": "task_not_found"}
        if not explicit_task:
            service.next_task(project)
        return {"success": True, "stdout": f"Task {task_id} marked as DONE.",
                "project": project, "task_id": task_id, "version": completed.get("version")}
    except StaleTaskVersion as exc:
        return {"success": False, "error": str(exc), "code": "stale_task_version"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        service.conn.close()

def scan_queue_file(q_file: Path) -> tuple[bytes, list[tuple[str, dict]]]:
    """Read a queue without consuming it; the caller removes it after SQL commits."""
    if not q_file.exists():
        return b"", []
    content = q_file.read_bytes()
    suggestions = []
    for number, line in enumerate(content.decode("utf-8-sig").splitlines(), start=1):
        if not line.strip():
            continue
        suggestion = json.loads(line)
        if not isinstance(suggestion, dict):
            raise ValueError(f"Invalid suggestion in {q_file.name}:{number}")
        source_key = hashlib.sha256(
            f"{q_file.name}\0{number}\0{line}".encode("utf-8")
        ).hexdigest()
        suggestions.append((source_key, suggestion))
    return content, suggestions

def sync_tasks(project: str | None = None) -> dict:
    """Import task suggestions into SQLite, then consume unchanged queue files."""
    from devcore_engine.services.tasks import TaskService

    try:
        project = require_project(project)
    except ValueError as exc:
        return {"success": False, "error": str(exc)}
    service = TaskService()
    try:
        board = service.get_board(project)
        if not service.conn.execute("SELECT 1 FROM projects WHERE id = ?", (project,)).fetchone():
            raise ValueError(f"project not found: {project}")
        project = board["project"]
        proj_mem = DEVCORE_DATA / "Memory" / project
        queues = []
        for q in ["git", "spec", "prompt"]:
            q_file = proj_mem / f"task_{q}_queue.jsonl"
            if q_file.exists():
                content, entries = scan_queue_file(q_file)
                queues.append((q_file, content, entries))
        if not queues:
            return {"success": True, "stdout": "Sync complete. 0 tasks added."}
        existing_titles = {task["title"] for task in board["tasks"]}
        added = 0
        for _, _, entries in queues:
            for source_key, suggestion in entries:
                title = str(suggestion.get("title") or "Untitled suggestion").strip()
                if title.lower() in existing_titles:
                    continue
                service.add_task(
                    title, mode=suggestion.get("mode") or "coding", project_id=project,
                    depends_on=suggestion.get("depends_on"),
                    metadata={"worktree": suggestion.get("worktree")},
                    idempotency_key=source_key,
                )
                existing_titles.add(title.lower())
                added += 1
        retained = 0
        for q_file, content, _ in queues:
            if q_file.exists() and q_file.read_bytes() == content:
                q_file.unlink()
            else:
                retained += 1
        return {"success": True, "stdout": f"Sync complete. {added} task(s) added to SQLite.",
                "retained_queues": retained}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        service.conn.close()
