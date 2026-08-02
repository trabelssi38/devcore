# MCP Server for DEV_CORE Scripts
# Permet a Hermes de lancer les scripts DEV_CORE en Python natif (sans powershell.exe)

import os
import sys
from pathlib import Path

# Add paths to sys.path so package imports resolve correctly
sys.path.append(str(Path(__file__).resolve().parent))

# Import MCP types
try:
    from mcp.server import Server
    from mcp.types import Tool, ToolInputSchema
except ImportError:
    pass

# Import MCP Hooks manager
try:
    from hooks import HookManager, CircuitBreakerOpenError
    hook_manager = HookManager()
except Exception:
    hook_manager = None
    class CircuitBreakerOpenError(Exception): pass

# Import tool definitions and handlers
from handlers.tool_handlers import (
    DEVCORE_SCRIPTS,
    DEVCORE_DATA,
    TOOLS,
    dispatch_tool
)

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
            
    res = dispatch_tool(tool_name, arguments)
    
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