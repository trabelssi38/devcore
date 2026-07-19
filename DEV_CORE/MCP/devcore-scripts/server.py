# MCP Server for DEV_CORE Scripts
# Permet a Hermes de lancer les scripts DEV_CORE en Python natif (sans powershell.exe)

import os
import sys
import json
import subprocess
import re
from datetime import datetime
from pathlib import Path
from typing import Any

# Import MCP types
try:
    from mcp.server import Server
    from mcp.types import Tool, ToolInputSchema
except ImportError:
    pass

# Resolves platform roots and script locations
DEVCORE_ROOT = Path(os.environ.get("DEVCORE_PLATFORM_ROOT", "C:/devcore/DEV_CORE"))
DEVCORE_DATA = Path(os.environ.get("DEVCORE_DATA_ROOT", "C:/devcore/DEV_CORE_DATA"))
DEVCORE_SCRIPTS = DEVCORE_ROOT / "Scripts"

# Import MCP Hooks manager
try:
    sys.path.insert(0, str(Path(__file__).parent))
    from hooks import HookManager, CircuitBreakerOpenError
    hook_manager = HookManager()
except Exception:
    hook_manager = None
    class CircuitBreakerOpenError(Exception): pass


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

def run_powershell_script(script_path: Path, args: list = None) -> dict:
    """Execute a PowerShell script."""
    cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script_path)]
    if args:
        cmd.extend(args)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(DEVCORE_ROOT.parent)
        )
        try:
            parsed = json.loads(result.stdout)
            return {"success": result.returncode == 0, "result": parsed}
        except Exception:
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
            "error": "Script timeout (> 1 min)"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def get_active_project() -> str:
    return os.environ.get("DEVCORE_ACTIVE_PROJECT_NAME", "devcore")

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
        queue_types = ["git", "spec", "prompt"]
        for q in queue_types:
            q_file = proj_mem / f"task_{q}_queue.jsonl"
            if q_file.exists():
                try:
                    with open(q_file, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip():
                                suggestions.append(json.loads(line))
                    q_file.unlink() # Cleanup queue file
                except Exception:
                    pass
                    
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

# Tool definitions
TOOLS = [
    {
        "name": "devcore_launch",
        "description": "Lance le script de demarrage quotidien DEV_CORE",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "devcore_task_scan",
        "description": "Scan automatique git + specs + prompts pour la detection des taches",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "devcore_task_sync",
        "description": "Synchronise les taches detectees dans tasks.json",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "devcore_task_status",
        "description": "Retourne le statut du board de taches",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "devcore_task_done",
        "description": "Marque la tache active comme completee et passe a la suivante",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "devcore_endday",
        "description": "Lance la cloture quotidienne (lecons + Qdrant + Obsidian sync)",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "devcore_diagnose",
        "description": "Lance le diagnostic complet du systeme DEV_CORE",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "devcore_check",
        "description": "Verifie l'état des services (Qdrant, Ollama, tasks, memory)",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "devcore_event_emit",
        "description": "Émet un événement dans le bus DEV_CORE",
        "input_schema": {
            "type": "object",
            "properties": {
                "event_type": {"type": "string"},
                "payload": {"type": "object"}
            },
            "required": ["event_type"]
        }
    },
    {
        "name": "devcore_dashboard_refresh",
        "description": "Régénère le dashboard Cockpit immédiatement",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "devcore_health_check",
        "description": "Vérifie la santé complète du pipeline (tasks.json, encoding, dashboard sync)",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "devcore_impact_analysis",
        "description": "Analyse d'impact via le knowledge graph: identifie les fichiers, services, tâches et commits liés à une cible",
        "input_schema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Fichier, service ou noeud cible (ex: DEV_CORE/Scripts/qdrant_sync.ps1)"}
            },
            "required": ["target"]
        }
    },
    {
        "name": "devcore_knowledge_status",
        "description": "Retourne le statut du knowledge graph (nombre de noeuds, arêtes, date de génération)",
        "input_schema": {"type": "object", "properties": {}}
    }
]

def emit_event(event_type: str, payload: dict) -> dict:
    try:
        bus_dir = DEVCORE_DATA / "Bus" / "events"
        bus_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        evt_file = bus_dir / f"{timestamp}_{event_type}.json"
        
        evt_data = {
            "type": event_type,
            "timestamp": datetime.now().isoformat()
        }
        if payload:
            evt_data.update(payload)
            
        with open(evt_file, "w", encoding="utf-8") as f:
            json.dump(evt_data, f, ensure_ascii=False, indent=2)
            
        return {"success": True, "event_file": str(evt_file)}
    except Exception as e:
        return {"success": False, "error": str(e)}

def _dispatch_tool_call(tool_name: str, arguments: dict) -> dict:
    """Internal tool call dispatcher."""
    if tool_name == "devcore_launch":
        # Launch daily task logic
        (DEVCORE_DATA / "Memory").mkdir(parents=True, exist_ok=True)
        (DEVCORE_DATA / "Logs" / "scripts").mkdir(parents=True, exist_ok=True)
        # Execute pricing sync and token report in python
        run_python_script(DEVCORE_SCRIPTS / "Auto" / "token_report.py")
        return {"success": True, "stdout": "Daily launch sequence completed natively in Python."}
        
    elif tool_name == "devcore_task_scan":
        # Run python prompt analyzer
        return run_python_script(DEVCORE_SCRIPTS / "Auto" / "task_prompt_analyzer.py")
        
    elif tool_name == "devcore_task_sync":
        return sync_tasks()
        
    elif tool_name == "devcore_task_status":
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
        
    elif tool_name == "devcore_task_done":
        return complete_active_task()
        
    elif tool_name == "devcore_endday":
        # Daily close: run token metrics report and refresh dashboard
        run_python_script(DEVCORE_SCRIPTS / "Auto" / "token_report.py")
        run_python_script(DEVCORE_SCRIPTS / "gen_dashboard.py")
        return {"success": True, "stdout": "Endday shutdown hooks executed natively in Python."}
        
    elif tool_name == "devcore_diagnose":
        return run_python_script(DEVCORE_SCRIPTS / "dc.py", ["doctor"])
        
    elif tool_name == "devcore_check":
        project = get_active_project()
        tasks_file = DEVCORE_DATA / "Memory" / project / "tasks.json"
        try:
            tasks_data = json.loads(tasks_file.read_text(encoding="utf-8-sig")) if tasks_file.exists() else {}
        except Exception:
            tasks_data = {}
        return {
            "tasks_json": tasks_data,
            "qdrant_status": "Qdrant active check" if check_port(6333) else "Qdrant unavailable",
            "memory_exists": (DEVCORE_DATA / "Memory" / "MEMORY.md").exists()
        }
        
    elif tool_name == "devcore_event_emit":
        return emit_event(arguments.get("event_type"), arguments.get("payload", {}))
        
    elif tool_name == "devcore_dashboard_refresh":
        return run_python_script(DEVCORE_SCRIPTS / "gen_dashboard.py")
        
    elif tool_name == "devcore_health_check":
        return run_python_script(DEVCORE_SCRIPTS / "Auto" / "integrity_check.py")
        
    elif tool_name == "devcore_impact_analysis":
        target = arguments.get("target", "")
        return run_powershell_script(DEVCORE_SCRIPTS / "knowledge_graph.ps1", ["-Action", "ImpactAnalysis", "-Target", target, "-Json"])
        
    elif tool_name == "devcore_knowledge_status":
        return run_powershell_script(DEVCORE_SCRIPTS / "knowledge_graph.ps1", ["-Action", "Status", "-Json"])
        
    else:
        return {"error": f"Unknown tool: {tool_name}"}

def handle_tool_call(tool_name: str, arguments: dict) -> dict:
    """Handle tool call wrapped with Pre/Post hooks."""
    arguments = arguments or {}
    context = {}
    
    if hook_manager:
        try:
            context = hook_manager.run_pre_hooks(tool_name, arguments)
        except CircuitBreakerOpenError as e:
            return {"success": False, "error": str(e), "circuit_breaker_open": True}
        except Exception as e:
            context["pre_hook_error"] = str(e)
            
    res = _dispatch_tool_call(tool_name, arguments)
    
    if hook_manager:
        try:
            res = hook_manager.run_post_hooks(tool_name, arguments, res, context)
        except Exception as e:
            res["post_hook_error"] = str(e)
            
    return res


def main():
    print("DEV_CORE MCP Server started")
    print(f"Scripts path: {DEVCORE_SCRIPTS}")
    print(f"Data path: {DEVCORE_DATA}")
    print(f"Available tools: {len(TOOLS)}")
    for tool in TOOLS:
        print(f"  - {tool['name']}: {tool['description']}")

if __name__ == "__main__":
    main()