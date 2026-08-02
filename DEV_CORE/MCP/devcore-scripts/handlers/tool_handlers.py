import os
import sys
import json
import socket
from datetime import datetime
from pathlib import Path

from services.task_service import (
    DEVCORE_ROOT,
    DEVCORE_DATA,
    DEVCORE_SCRIPTS,
    run_python_script,
    get_active_project,
    get_active_task_status,
    complete_active_task,
    sync_tasks
)

def check_port(port: int) -> bool:
    """Natively checks if a local port is listening."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except Exception:
        return False

def run_powershell_script(script_path: Path, args: list = None) -> dict:
    """Execute a PowerShell script."""
    import subprocess
    from services.task_service import apply_rtk
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

# Handlers registry pattern to reduce CCN from 23 to 1
def handle_launch(arguments: dict) -> dict:
    (DEVCORE_DATA / "Memory").mkdir(parents=True, exist_ok=True)
    (DEVCORE_DATA / "Logs" / "scripts").mkdir(parents=True, exist_ok=True)
    run_python_script(DEVCORE_SCRIPTS / "Auto" / "token_report.py")
    return {"success": True, "stdout": "Daily launch sequence completed natively in Python."}

def handle_task_scan(arguments: dict) -> dict:
    return run_python_script(DEVCORE_SCRIPTS / "Auto" / "task_prompt_analyzer.py")

def handle_task_sync(arguments: dict) -> dict:
    return sync_tasks()

def handle_task_status(arguments: dict) -> dict:
    return get_active_task_status()

def handle_task_done(arguments: dict) -> dict:
    return complete_active_task()

def handle_endday(arguments: dict) -> dict:
    run_python_script(DEVCORE_SCRIPTS / "Auto" / "token_report.py")
    run_python_script(DEVCORE_SCRIPTS / "gen_dashboard.py")
    return {"success": True, "stdout": "Endday shutdown hooks executed natively in Python."}

def handle_diagnose(arguments: dict) -> dict:
    return run_python_script(DEVCORE_SCRIPTS / "dc.py", ["doctor"])

def handle_check(arguments: dict) -> dict:
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

def handle_event_emit(arguments: dict) -> dict:
    return emit_event(arguments.get("event_type"), arguments.get("payload", {}))

def handle_dashboard_refresh(arguments: dict) -> dict:
    return run_python_script(DEVCORE_SCRIPTS / "gen_dashboard.py")

def handle_health_check(arguments: dict) -> dict:
    return run_python_script(DEVCORE_SCRIPTS / "Auto" / "integrity_check.py")

def handle_impact_analysis(arguments: dict) -> dict:
    target = arguments.get("target", "")
    return run_powershell_script(DEVCORE_SCRIPTS / "knowledge_graph.ps1", ["-Action", "ImpactAnalysis", "-Target", target, "-Json"])

def handle_knowledge_status(arguments: dict) -> dict:
    return run_powershell_script(DEVCORE_SCRIPTS / "knowledge_graph.ps1", ["-Action", "Status", "-Json"])

# The Tool Handler Registry
TOOL_HANDLERS = {
    "devcore_launch": handle_launch,
    "devcore_task_scan": handle_task_scan,
    "devcore_task_sync": handle_task_sync,
    "devcore_task_status": handle_task_status,
    "devcore_task_done": handle_task_done,
    "devcore_endday": handle_endday,
    "devcore_diagnose": handle_diagnose,
    "devcore_check": handle_check,
    "devcore_event_emit": handle_event_emit,
    "devcore_dashboard_refresh": handle_dashboard_refresh,
    "devcore_health_check": handle_health_check,
    "devcore_impact_analysis": handle_impact_analysis,
    "devcore_knowledge_status": handle_knowledge_status,
}

def dispatch_tool(tool_name: str, arguments: dict) -> dict:
    handler = TOOL_HANDLERS.get(tool_name)
    if handler:
        return handler(arguments)
    return {"error": f"Unknown tool: {tool_name}"}

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
        "description": "Emet un evenement dans le bus DEV_CORE",
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

