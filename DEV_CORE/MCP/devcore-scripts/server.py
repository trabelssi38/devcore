# MCP Server for DEV_CORE Scripts
# Permet a Hermes de lancer les scripts DEV_CORE en Python natif (sans powershell.exe)

import asyncio
import json
import os
import sys
from pathlib import Path

from mcp.server import InitializationOptions, NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, TextContent, Tool

# Add paths to sys.path so package imports resolve correctly
sys.path.append(str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

AUTH_PROFILE = os.environ.get("DEVCORE_MCP_AUTH_PROFILE", "legacy").strip()
if AUTH_PROFILE not in {"legacy", "individual"}:
    raise ValueError("Unknown DEVCORE_MCP_AUTH_PROFILE")

if AUTH_PROFILE == "individual":
    # No legacy adapters/hooks imported: the client has no business or identity DB access.
    from services.individual_tasks import IndividualApiClient
    individual_client = IndividualApiClient.from_environment()
    TOOLS = individual_client.tools
    hook_manager = None
else:
    try:
        from hooks import HookManager, CircuitBreakerOpenError
        hook_manager = HookManager()
    except Exception:
        hook_manager = None
        class CircuitBreakerOpenError(Exception): pass
    from handlers.tool_handlers import TOOLS, dispatch_tool

CONSULTATION_TOOLS = {"devcore_task_status", "devcore_check", "devcore_project_context"}

def handle_tool_call(tool_name: str, arguments: dict) -> dict:
    """Handle tool call wrapped with Pre/Post hooks."""
    if AUTH_PROFILE == "individual":
        return individual_client.call(tool_name, arguments)
    arguments = arguments or {}
    if os.getenv("DEVCORE_MCP_READ_ONLY") == "1" and tool_name not in CONSULTATION_TOOLS:
        return {"success": False, "error": "Tool unavailable in the consultation profile"}
    bound_project = os.getenv("DEVCORE_MCP_PROJECT")
    if bound_project and arguments.get("project") != bound_project:
        return {"success": False, "error": "Explicit project must match the configured project"}
    if tool_name == "devcore_project_context":
        # This pure reader's measured payload must not be modified by post-hooks.
        return dispatch_tool(tool_name, arguments)
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

def create_mcp_server() -> Server:
    server = Server("devcore-scripts", version="1.0.0")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        readonly = os.getenv("DEVCORE_MCP_READ_ONLY") == "1"
        return [
            Tool(
                name=item["name"],
                description=item["description"],
                inputSchema=item["input_schema"],
            )
            for item in TOOLS
            if AUTH_PROFILE == "individual" or not readonly or item["name"] in CONSULTATION_TOOLS
        ]

    # Individual arguments are validated by the adapter before secret/network access,
    # giving JSON errors instead of the SDK's unmeasured textual schema diagnostics.
    @server.call_tool(validate_input=AUTH_PROFILE != "individual")
    async def call_tool(name: str, arguments: dict) -> CallToolResult:
        result = await asyncio.to_thread(handle_tool_call, name, arguments)
        failed = result.get("success") is False or "error" in result
        if name == "devcore_project_context" or (AUTH_PROFILE == "individual" and name == "devcore_task_audit"):
            from devcore_engine.services.project_context import encode_context
            # One textual payload: don't duplicate a long context in structuredContent.
            return CallToolResult(
                content=[TextContent(type="text", text=encode_context(result) + "\n")],
                isError=failed,
            )
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(result, ensure_ascii=False))],
            structuredContent=None if AUTH_PROFILE == "individual" else result,
            isError=failed,
        )

    return server


async def serve_stdio() -> None:
    server = create_mcp_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="devcore-scripts",
                server_version="1.0.0",
                capabilities=server.get_capabilities(NotificationOptions(), {}),
            ),
        )


def main() -> None:
    asyncio.run(serve_stdio())

if __name__ == "__main__":
    main()
