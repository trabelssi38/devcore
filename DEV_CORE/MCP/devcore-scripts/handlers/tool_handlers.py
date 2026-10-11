import os
import sys
import json
import re
import socket
from pathlib import Path

from services.task_service import (
    DEVCORE_ROOT,
    DEVCORE_DATA,
    DEVCORE_LOCAL,
    DEVCORE_SCRIPTS,
    run_python_script,
    require_project,
    open_task_service,
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

def emit_event(event_type: str, payload: dict, project: str | None) -> dict:
    try:
        import re
        from devcore_engine.services.tasks import TaskService

        project = require_project(project)
        if not isinstance(event_type, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,79}", event_type):
            raise ValueError("invalid event_type")
        if not isinstance(payload, dict):
            raise ValueError("payload must be an object")
        service = TaskService()
        try:
            service.get_board(project)
            if not service.conn.execute("SELECT 1 FROM projects WHERE id = ?", (project,)).fetchone():
                raise ValueError(f"project not found: {project}")
            event_id = service.event_bus.publish(event_type, payload, project=project)
            return {"success": True, "event_id": event_id, "project": project}
        finally:
            service.conn.close()
    except Exception as e:
        return {"success": False, "error": str(e)}

# Handlers registry pattern to reduce CCN from 23 to 1
def handle_launch(arguments: dict) -> dict:
    (DEVCORE_DATA / "Memory").mkdir(parents=True, exist_ok=True)
    (DEVCORE_LOCAL / "Logs" / "scripts").mkdir(parents=True, exist_ok=True)
    run_python_script(DEVCORE_SCRIPTS / "Auto" / "token_report.py")
    return {"success": True, "stdout": "Daily launch sequence completed natively in Python."}

def handle_task_scan(arguments: dict) -> dict:
    try:
        project = require_project(arguments.get("project"))
    except ValueError as exc:
        return {"success": False, "error": str(exc)}
    return run_python_script(DEVCORE_SCRIPTS / "Auto" / "task_prompt_analyzer.py", ["--project", project])

def handle_task_sync(arguments: dict) -> dict:
    return sync_tasks(arguments.get("project"))

def handle_task_status(arguments: dict) -> dict:
    return get_active_task_status(arguments.get("project"))

def handle_task_done(arguments: dict) -> dict:
    return complete_active_task(arguments.get("project"), task_id=arguments.get("task_id"),
                                expected_version=arguments.get("expected_version"))

def handle_endday(arguments: dict) -> dict:
    run_python_script(DEVCORE_SCRIPTS / "Auto" / "token_report.py")
    run_python_script(DEVCORE_SCRIPTS / "gen_dashboard.py")
    return {"success": True, "stdout": "Endday shutdown hooks executed natively in Python."}

def handle_diagnose(arguments: dict) -> dict:
    return run_python_script(DEVCORE_SCRIPTS / "dc.py", ["doctor"])

def handle_check(arguments: dict) -> dict:
    try:
        project = require_project(arguments.get("project"))
        service = open_task_service()
        try:
            tasks_data = service.get_board(project)
            if not service.conn.execute("SELECT 1 FROM projects WHERE id = ?", (project,)).fetchone():
                raise ValueError(f"project not found: {project}")
        finally:
            service.conn.close()
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    return {
        "success": True,
        "tasks_json": tasks_data,
        "qdrant_status": "Qdrant active check" if check_port(6333) else "Qdrant unavailable",
        "memory_exists": (DEVCORE_DATA / "Memory" / "MEMORY.md").exists()
    }

def handle_project_context(arguments: dict) -> dict:
    """Read only the administrator-configured context directory; no client path input."""
    from devcore_engine.services.project_context import load_project_context
    try:
        if set(arguments) - {"project", "budget_bytes", "query"}:
            raise ValueError("Unsupported project context argument")
        project = require_project(arguments.get("project"))
        root = os.getenv("DEVCORE_CONTEXT_ROOT")
        if not root or not Path(root).is_absolute():
            raise ValueError("An explicit absolute DEVCORE_CONTEXT_ROOT is required")
        limit = int(os.getenv("DEVCORE_CONTEXT_MAX_BYTES", "12000"))
        if not 256 <= limit <= 65536:
            raise ValueError("Invalid configured context limit")
        budget = arguments.get("budget_bytes", limit)
        if type(budget) is not int or not 256 <= budget <= limit:
            raise ValueError("budget_bytes must be between 256 and the configured context limit")
        return load_project_context(Path(root), project, budget_bytes=budget,
                                    query=arguments.get("query", ""))
    except (OSError, ValueError) as exc:
        return {"success": False, "error": str(exc)}

def handle_event_emit(arguments: dict) -> dict:
    return emit_event(arguments.get("event_type"), arguments.get("payload", {}), arguments.get("project"))

def handle_dashboard_refresh(arguments: dict) -> dict:
    return run_python_script(DEVCORE_SCRIPTS / "gen_dashboard.py")

def handle_health_check(arguments: dict) -> dict:
    try:
        project = require_project(arguments.get("project"))
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", project) or project in {".", ".."}:
            raise ValueError("project must be a simple project identifier")
        repo_root = os.getenv("DEVCORE_MCP_REPO_ROOT", "")
        if not repo_root or not Path(repo_root).is_absolute() or not Path(repo_root).is_dir():
            raise ValueError("An absolute existing DEVCORE_MCP_REPO_ROOT is required")
    except ValueError as exc:
        return {"success": False, "error": str(exc)}
    return run_python_script(
        DEVCORE_SCRIPTS / "Auto" / "integrity_check.py",
        ["--project", project, "--repo", str(Path(repo_root).resolve())],
    )

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
    "devcore_project_context": handle_project_context,
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
        "name": "devcore_project_context",
        "description": "Charge fiche et décisions applicables du projet explicite, avec plafond en octets UTF-8 (pas tokens), omissions et fraîcheur. Aucun accès SQLite.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project": {"type": "string"},
                "budget_bytes": {"type": "integer", "minimum": 256, "maximum": 65536},
                "query": {"type": "string", "maxLength": 4096}
            },
            "required": ["project"],
            "additionalProperties": False
        }
    },
    {
        "name": "devcore_launch",
        "description": "Lance le script de demarrage quotidien DEV_CORE",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "devcore_task_scan",
        "description": "Analyse les suggestions historiques pour un projet explicite",
        "input_schema": {"type": "object", "properties": {"project": {"type": "string"}}, "required": ["project"], "additionalProperties": False}
    },
    {
        "name": "devcore_task_sync",
        "description": "Importe les suggestions de taches dans SQLite",
        "input_schema": {"type": "object", "properties": {"project": {"type": "string"}}, "required": ["project"]}
    },
    {
        "name": "devcore_task_status",
        "description": "Retourne le statut du board de taches",
        "input_schema": {"type": "object", "properties": {"project": {"type": "string"}}, "required": ["project"]}
    },
    {
        "name": "devcore_task_done",
        "description": "Clôture la tâche nommée du projet, avec version attendue optionnelle. Une version exige task_id. Sans task_id, conserve la sélection et l'avancement historiques.",
        "input_schema": {
            "type": "object", "properties": {
                "project": {"type": "string"},
                "task_id": {"type": "string", "minLength": 1, "maxLength": 128},
                "expected_version": {"type": "integer", "minimum": 1}
            }, "required": ["project"], "additionalProperties": False
        }
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
        "input_schema": {"type": "object", "properties": {"project": {"type": "string"}}, "required": ["project"]}
    },
    {
        "name": "devcore_event_emit",
        "description": "Emet un evenement dans le bus DEV_CORE",
        "input_schema": {
            "type": "object",
            "properties": {
                "project": {"type": "string"},
                "event_type": {"type": "string"},
                "payload": {"type": "object"}
            },
            "required": ["project", "event_type"]
        }
    },
    {
        "name": "devcore_dashboard_refresh",
        "description": "Régénère le dashboard Cockpit immédiatement",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "devcore_health_check",
        "description": "Vérifie l'intégrité des tâches pour le projet explicite et le dépôt configuré côté serveur",
        "input_schema": {"type": "object", "properties": {"project": {"type": "string"}}, "required": ["project"], "additionalProperties": False}
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

