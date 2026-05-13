# MCP Server for DEV_CORE Scripts
# Permet a Hermes de lancer les scripts DEV_CORE

import json
import subprocess
from pathlib import Path
from typing import Any

# Import MCP types
try:
    from mcp.server import Server
    from mcp.types import Tool, ToolInputSchema
except ImportError:
    # Fallback if MCP not installed
    pass

# DEV_CORE Paths
DEVCORE_SCRIPTS = Path("C:/devcore/DEV_CORE/Scripts")
DEVCORE_DATA = Path("C:/devcore/DEV_CORE_DATA")


def run_powershell(script_path: str, args: list = None) -> dict:
    """Execute a PowerShell script and return output."""
    cmd = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script_path]
    if args:
        cmd.extend(args)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        return {
            "success": True,
            "stdout": result.stdout,
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


def read_json(file_path: str) -> dict:
    """Read a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e)}


# Tool definitions
TOOLS = [
    {
        "name": "devcore_launch",
        "description": "Lance le script de demarrage quotidien DEV_CORE",
        "input_schema": {
            "type": "object",
            "properties": {},
        }
    },
    {
        "name": "devcore_task_scan",
        "description": "Scan automatique git + specs + prompts pour detection taches",
        "input_schema": {
            "type": "object",
            "properties": {},
        }
    },
    {
        "name": "devcore_task_sync",
        "description": "Synchronise les taches detectees dans tasks.json",
        "input_schema": {
            "type": "object",
            "properties": {},
        }
    },
    {
        "name": "devcore_task_status",
        "description": "Retourne le statut du board de taches",
        "input_schema": {
            "type": "object",
            "properties": {},
        }
    },
    {
        "name": "devcore_task_done",
        "description": "Marque la tache active comme completee et passe a la suivante",
        "input_schema": {
            "type": "object",
            "properties": {},
        }
    },
    {
        "name": "devcore_endday",
        "description": "Lance la cloture quotidienne (lessons + Qdrant + Obsidian sync)",
        "input_schema": {
            "type": "object",
            "properties": {},
        }
    },
    {
        "name": "devcore_diagnose",
        "description": "Lance le diagnostic complet du systeme DEV_CORE",
        "input_schema": {
            "type": "object",
            "properties": {},
        }
    },
    {
        "name": "devcore_check",
        "description": "Verifie l'etat des services (Qdrant, Ollama, tasks, memory)",
        "input_schema": {
            "type": "object",
            "properties": {},
        }
    }
]


def handle_tool_call(tool_name: str, arguments: dict) -> dict:
    """Handle tool call from Hermes."""
    results = {
        "devcore_launch": lambda: run_powershell(str(DEVCORE_SCRIPTS / "launch.ps1")),
        "devcore_task_scan": lambda: run_powershell(str(DEVCORE_SCRIPTS / "task_scan.ps1")),
        "devcore_task_sync": lambda: run_powershell(str(DEVCORE_SCRIPTS / "task_sync.ps1")),
        "devcore_task_status": lambda: run_powershell(str(DEVCORE_SCRIPTS / "task_status.ps1")),
        "devcore_task_done": lambda: run_powershell(str(DEVCORE_SCRIPTS / "task_done.ps1")),
        "devcore_endday": lambda: run_powershell(str(DEVCORE_SCRIPTS / "endday.ps1")),
        "devcore_diagnose": lambda: run_powershell(str(DEVCORE_SCRIPTS / "diagnose.ps1")),
        "devcore_check": lambda: {
            "tasks_json": read_json(str(DEVCORE_DATA / "Memory" / "tasks.json")),
            "qdrant_status": "check via curl http://localhost:6333/collections",
            "memory_exists": (DEVCORE_DATA / "Memory" / "MEMORY.md").exists()
        }
    }

    if tool_name in results:
        return results[tool_name]()
    else:
        return {"error": f"Unknown tool: {tool_name}"}


def main():
    """Main entry point for MCP server."""
    print("DEV_CORE MCP Server started")
    print(f"Scripts path: {DEVCORE_SCRIPTS}")
    print(f"Data path: {DEVCORE_DATA}")
    print(f"Available tools: {len(TOOLS)}")

    # In production, this would start the MCP server
    # For now, we just print the tools
    for tool in TOOLS:
        print(f"  - {tool['name']}: {tool['description']}")


if __name__ == "__main__":
    main()