"""Run the local RepoWise consultation tools with external Python sockets blocked."""

import ipaddress
import os
import sys


def block_external_sockets(event, args):
    if event not in ("socket.connect", "socket.getaddrinfo"):
        return
    address = args[1] if event == "socket.connect" else args[0]
    host = address[0] if isinstance(address, tuple) else address
    if event == "socket.connect" and not isinstance(address, tuple):
        return  # Local Unix sockets do not address a remote host.
    if host == "localhost":
        return
    try:
        if ipaddress.ip_address(host).is_loopback:
            return
    except (ValueError, TypeError):
        pass
    raise PermissionError("External Python socket access is disabled for local RepoWise MCP")


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: repowise_mcp_local.py <repository>")
    os.environ["REPOWISE_EMBEDDER"] = "mock"
    os.environ["REPOWISE_TELEMETRY_DISABLED"] = "1"
    sys.addaudithook(block_external_sockets)
    from repowise.cli.main import cli
    cli(args=["mcp", sys.argv[1], "--transport", "stdio", "--no-workspace",
              "--tools", "get_context,get_symbol,search_codebase,get_overview,get_health"], prog_name="repowise")


if __name__ == "__main__":
    main()
