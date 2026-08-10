import os
import json
import re
import sys
import subprocess
from datetime import datetime
from pathlib import Path

DEVCORE_ROOT = Path(os.environ.get("DEVCORE_PLATFORM_ROOT", "C:/devcore/DEV_CORE"))
try:
    from devcore_engine.db import get_data_root
    DEVCORE_DATA = get_data_root()
except Exception:
    DEVCORE_DATA = Path(os.environ.get("DEVCORE_DATA_ROOT", "C:/devcore/DEV_CORE_DATA"))
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
            kpi_file = DEVCORE_DATA / "Metrics" / "kpi.csv"
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

def get_active_project() -> str:
    return os.environ.get("DEVCORE_ACTIVE_PROJECT_NAME", "devcore")

def get_active_task_status() -> dict:
    project = get_active_project()
    tasks_file = DEVCORE_DATA / "Memory" / project / "tasks.json"
    if tasks_file.exists():
        try:
            board = json.loads(tasks_file.read_text(encoding="utf-8-sig"))
            tasks = board.get("tasks", [])
            active = next((t for t in tasks if t.get("status") == "active"), None)
            done_count = sum(1 for t in tasks if t.get("status") == "done")
            status_str = f"Active task: {active.get('id') if active else 'None'} ({active.get('title') if active else 'N/A'})\n"
            status_str += f"Tasks progress: {done_count}/{len(tasks)} completed."
            return {"success": True, "stdout": status_str}
        except Exception as e:
            return {"success": False, "error": f"Failed to read board: {e}"}
    return {"success": False, "error": "tasks.json not found"}

def complete_active_task() -> dict:
    """Natively completes the active task and transitions to the next one."""
    try:
        project = get_active_project()
        tasks_file = DEVCORE_DATA / "Memory" / project / "tasks.json"
        if not tasks_file.exists():
            return {"success": False, "error": "tasks.json not found"}
        
        with open(tasks_file, "r", encoding="utf-8-sig") as f:
            board = json.load(f)
            
        active_id = board.get("current_task")
        if not active_id:
            return {"success": False, "error": "Aucune tâche active à clore."}
            
        for t in board.get("tasks", []):
            if t.get("id") == active_id:
                t["status"] = "done"
                t["steps_done"] = t.get("steps_total", 1)
                t["completed_at"] = datetime.now().isoformat()
                break
                
        # Activate next task if possible
        next_task = next((t for t in board.get("tasks", []) if t.get("status") == "todo"), None)
        if next_task:
            next_task["status"] = "active"
            next_task["started_at"] = datetime.now().isoformat()
            board["current_task"] = next_task["id"]
        else:
            board["current_task"] = None
            
        with open(tasks_file, "w", encoding="utf-8") as f:
            json.dump(board, f, indent=4, ensure_ascii=False)
            
        # Refresh dashboard
        run_python_script(DEVCORE_SCRIPTS / "gen_dashboard.py")
        
        return {"success": True, "stdout": f"Active task {active_id} marked as DONE."}
    except Exception as e:
        return {"success": False, "error": str(e)}

def scan_queue_file(q_file: Path, suggestions: list):
    """Scan queue file and load suggestions (reducing nesting depth)."""
    if not q_file.exists():
        return
    try:
        with open(q_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    suggestions.append(json.loads(line))
        q_file.unlink()  # Cleanup queue file
    except Exception:
        pass

def sync_tasks() -> dict:
    """Natively synchronizes suggestions from queues into tasks.json."""
    try:
        project = get_active_project()
        proj_mem = DEVCORE_DATA / "Memory" / project
        tasks_file = proj_mem / "tasks.json"
        
        if not tasks_file.exists():
            return {"success": False, "error": "tasks.json not found"}
            
        with open(tasks_file, "r", encoding="utf-8-sig") as f:
            board = json.load(f)
            
        # Scan queues
        suggestions = []
        for q in ["git", "spec", "prompt"]:
            scan_queue_file(proj_mem / f"task_{q}_queue.jsonl", suggestions)
                    
        if not suggestions:
            return {"success": True, "stdout": "Sync complete. 0 tasks added."}
            
        # Find highest ID index
        existing_ids = [t.get("id", "") for t in board.get("tasks", [])]
        max_idx = 0
        for tid in existing_ids:
            match = re.search(r'T-(\d+)', tid)
            if match:
                max_idx = max(max_idx, int(match.group(1)))
                
        added = 0
        for sug in suggestions:
            # Check duplicate title
            if any(t.get("title") == sug.get("title") for t in board.get("tasks", [])):
                continue
            max_idx += 1
            new_task = {
                "id": f"T-{max_idx:02d}",
                "title": sug.get("title", "Untitled suggestion"),
                "status": "todo",
                "mode": sug.get("mode", "coding"),
                "steps_done": 0,
                "steps_total": 1,
                "depends_on": sug.get("depends_on"),
                "worktree": sug.get("worktree")
            }
            board.setdefault("tasks", []).append(new_task)
            added += 1
            
        if added > 0:
            with open(tasks_file, "w", encoding="utf-8") as f:
                json.dump(board, f, indent=4, ensure_ascii=False)
                
        # Refresh dashboard
        run_python_script(DEVCORE_SCRIPTS / "gen_dashboard.py")
        
        return {"success": True, "stdout": f"Sync complete. {added} task(s) added to tasks.json."}
    except Exception as e:
        return {"success": False, "error": str(e)}
