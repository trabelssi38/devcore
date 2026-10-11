"""Configure only this repository's Codex MCP tables, with backup and conflict checks."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import tomllib
from uuid import uuid4


def build_config(original: bytes, repo: Path, python: Path, repowise_python: Path,
                 local_root: Path, data_root: Path, project: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", project) or ".." in project:
        raise ValueError("invalid project")
    parsed = tomllib.loads(original.decode("utf-8-sig"))
    text = original.decode("utf-8-sig")
    # Remove precisely the two managed tables and their children; keep every other section.
    text = re.sub(r"(?ms)^\[mcp_servers\.(?:repowise|devcore)(?:\.[^\]\r\n]+)?\][^\r\n]*\r?\n.*?(?=^\[|\Z)", "", text)
    quote = lambda value: json.dumps(str(value), ensure_ascii=False)
    platform = repo / "DEV_CORE"
    block = f"""
[mcp_servers.repowise]
command = {quote(repowise_python)}
args = [{quote(platform / 'Scripts' / 'repowise_mcp_local.py')}, {quote(repo)}]
cwd = {quote(repo)}
startup_timeout_sec = 120
tool_timeout_sec = 60
enabled_tools = ["get_context", "get_symbol", "search_codebase", "get_overview", "get_health"]

[mcp_servers.repowise.env]
REPOWISE_EMBEDDER = "mock"
REPOWISE_TELEMETRY_DISABLED = "1"

[mcp_servers.devcore]
command = {quote(python)}
args = [{quote(platform / 'MCP' / 'devcore-scripts' / 'server.py')}]
cwd = {quote(repo)}
startup_timeout_sec = 30
tool_timeout_sec = 30
enabled_tools = ["devcore_task_status", "devcore_check", "devcore_project_context"]

[mcp_servers.devcore.env]
DEVCORE_PLATFORM_ROOT = {quote(platform)}
DEVCORE_LOCAL_ROOT = {quote(local_root)}
DEVCORE_DATA_ROOT = {quote(data_root)}
DEVCORE_MCP_PROJECT = {quote(project)}
DEVCORE_MCP_READ_ONLY = "1"
DEVCORE_CONTEXT_ROOT = {quote(repo / 'docs' / 'project-context')}
DEVCORE_CONTEXT_MAX_BYTES = "12000"
"""
    result = text.rstrip() + "\n" + block
    after = tomllib.loads(result)
    for obj in (parsed, after):
        servers = obj.get("mcp_servers", {})
        servers.pop("repowise", None)
        servers.pop("devcore", None)
        if not servers:
            obj.pop("mcp_servers", None)
    if parsed != after:
        raise ValueError("refusing to change unrelated Codex settings")
    return result


def install(config: Path, content: str, original: bytes) -> Path | None:
    config.parent.mkdir(parents=True, exist_ok=True)
    backup = None
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=config.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        current = config.read_bytes() if config.exists() else b""
        if current != original:
            raise ValueError("Codex configuration changed since it was read")
        if config.exists():
            backup = config.with_name(f"config.toml.backup-{uuid4()}")
            backup.write_bytes(original)
        os.replace(temporary, config)
        return backup
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--repowise-python", type=Path, required=True)
    parser.add_argument("--local-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    repo = args.repo.resolve()
    config = repo / ".codex" / "config.toml"
    try:
        for path in (args.python, args.repowise_python, repo / "DEV_CORE" / "MCP" / "devcore-scripts" / "server.py",
                     repo / "DEV_CORE" / "Scripts" / "repowise_mcp_local.py"):
            if not path.is_file():
                raise ValueError(f"required file missing: {path}")
        original = config.read_bytes() if config.exists() else b""
        content = build_config(original, repo, args.python.resolve(), args.repowise_python.resolve(),
                               args.local_root.resolve(), args.data_root.resolve(), args.project)
        backup = install(config, content, original) if args.apply else None
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps({"status": "applied" if args.apply else "preview", "config": str(config),
                      "backup": str(backup) if backup else None,
                      "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                      "servers": ["repowise", "devcore"], "project": args.project}, indent=2))


if __name__ == "__main__":
    main()
