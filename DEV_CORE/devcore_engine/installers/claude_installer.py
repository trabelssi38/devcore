"""
claude_installer.py -- Portable and dynamic installer for DEV_CORE AI clients integration.
Supports Claude Code (CLI/Desktop), Claude Desktop GUI, Codex, Gemini, and Antigravity.
"""

from __future__ import annotations
import os
import sys
import json
import shutil
import platform
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def detect_environment(repo_root: Optional[Path | str] = None) -> Dict[str, Any]:
    """
    Detect the runtime environment, paths, executables, and config directories dynamically.
    """
    current_os = platform.system().lower()
    
    # 1. Platform Root (always where DEV_CORE engine lives)
    devcore_dir = Path(__file__).resolve().parents[2]
    if (devcore_dir / "DEV_CORE").exists():
        devcore_platform_root = devcore_dir / "DEV_CORE"
        default_repo_root = devcore_dir
    elif devcore_dir.name == "DEV_CORE":
        devcore_platform_root = devcore_dir
        default_repo_root = devcore_dir.parent
    else:
        devcore_platform_root = devcore_dir
        default_repo_root = devcore_dir

    # Repo Root resolution (custom argument > CWD if it's a project > default repo root)
    if repo_root:
        resolved_repo = Path(repo_root).resolve()
    else:
        cwd = Path.cwd().resolve()
        if (cwd / ".git").exists() or (cwd / ".devcore").exists() or (cwd / ".mcp.json").exists():
            resolved_repo = cwd
        else:
            resolved_repo = default_repo_root

    devcore_data_root = (
        resolved_repo / "DEV_CORE_DATA"
        if (resolved_repo / "DEV_CORE_DATA").exists()
        else (default_repo_root / "DEV_CORE_DATA" if (default_repo_root / "DEV_CORE_DATA").exists() else Path.home() / "DEV_CORE_DATA")
    )

    # 2. Python Executable
    python_exe = sys.executable or "python"

    # 3. Repowise Executable Resolution
    repowise_exe = resolve_repowise_binary(python_exe)

    # 4. User Home & Config Directories
    home_dir = Path.home()
    claude_code_dir = home_dir / ".claude"
    
    # Claude Desktop GUI Config Path
    if current_os == "windows":
        appdata = os.environ.get("APPDATA")
        claude_desktop_dir = Path(appdata) / "Claude" if appdata else home_dir / "AppData" / "Roaming" / "Claude"
    elif current_os == "darwin":
        claude_desktop_dir = home_dir / "Library" / "Application Support" / "Claude"
    else:
        # Linux
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        claude_desktop_dir = Path(xdg_config) / "Claude" if xdg_config else home_dir / ".config" / "Claude"

    claude_desktop_config = claude_desktop_dir / "claude_desktop_config.json"

    # Other clients
    codex_dir = home_dir / ".codex"
    gemini_dir = home_dir / ".gemini"
    antigravity_dir = home_dir / ".gemini" / "antigravity"

    return {
        "os": current_os,
        "repo_root": resolved_repo,
        "platform_root": devcore_platform_root,
        "data_root": devcore_data_root,
        "python_exe": python_exe,
        "repowise_exe": repowise_exe,
        "home_dir": home_dir,
        "claude_code_dir": claude_code_dir,
        "claude_code_settings": claude_code_dir / "settings.json",
        "claude_code_md": claude_code_dir / "CLAUDE.md",
        "claude_desktop_dir": claude_desktop_dir,
        "claude_desktop_config": claude_desktop_config,
        "codex_dir": codex_dir,
        "gemini_dir": gemini_dir,
        "antigravity_dir": antigravity_dir,
    }


def resolve_repowise_binary(python_exe: str) -> str:
    """Find the repowise binary dynamically across platforms."""
    # 1. Check PATH
    found = shutil.which("repowise")
    if found:
        return str(Path(found).resolve())

    # 2. Check Python prefix (virtualenv or global installation)
    py_path = Path(python_exe).resolve()
    candidates: List[Path] = []
    if py_path.parent.name.lower() in ("scripts", "bin"):
        candidates.append(py_path.parent / ("repowise.exe" if os.name == "nt" else "repowise"))
    else:
        candidates.append(py_path.parent / "Scripts" / "repowise.exe")
        candidates.append(py_path.parent / "bin" / "repowise")

    # 3. Check AppData Roaming Python on Windows
    if os.name == "nt":
        home = Path.home()
        for ver in ("Python314", "Python313", "Python312", "Python311", "Python310"):
            candidates.append(home / "AppData" / "Roaming" / "Python" / ver / "Scripts" / "repowise.exe")
            candidates.append(Path("C:/") / ver / "Scripts" / "repowise.exe")
            candidates.append(Path("C:/Program Files") / ver / "Scripts" / "repowise.exe")

    for cand in candidates:
        if cand.exists():
            return str(cand.resolve())

    return "repowise"


class ClaudeInstaller:
    """Automated and portable installer for DEV_CORE integrations."""

    def __init__(self, repo_root: Optional[Path | str] = None, dry_run: bool = False):
        self.env = detect_environment(repo_root)
        self.dry_run = dry_run

    def _read_json(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except Exception:
            return {}

    def _write_json_safe(self, path: Path, data: Dict[str, Any]) -> None:
        if self.dry_run:
            print(f"  [DRY-RUN] Would write JSON to {path}")
            return

        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            backup_path = path.with_suffix(".json.bak")
            try:
                shutil.copy2(path, backup_path)
            except Exception:
                pass

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")

    def install_claude_code(self) -> Dict[str, Any]:
        """
        Configure Claude Code CLI and Desktop extension:
        - Native python hooks for Session Lifecycle & Tool tracking
        - Dynamic Repowise MCP server
        - Global and project CLAUDE.md
        - Local .mcp.json
        """
        results: Dict[str, Any] = {"status": "OK", "actions": []}

        # 1. Update ~/.claude/settings.json
        settings_path = self.env["claude_code_settings"]
        settings = self._read_json(settings_path)

        cli_script = str((self.env["platform_root"] / "devcore_engine" / "cli.py").resolve())
        post_tool_script = str((self.env["platform_root"] / "devcore_engine" / "hooks" / "post_tool.py").resolve())
        python_exe = self.env["python_exe"]

        cmd_start = f'"{python_exe}" "{cli_script}" session start'
        cmd_tool = f'"{python_exe}" "{post_tool_script}"'
        cmd_end = f'"{python_exe}" "{cli_script}" session end'

        # Configure Hooks
        hooks = settings.get("hooks", {})
        hooks["UserPromptSubmit"] = [{"matcher": "", "hooks": [{"type": "command", "command": cmd_start}]}]
        hooks["PostToolUse"] = [{"matcher": "Bash", "hooks": [{"type": "command", "command": cmd_tool}]}]
        hooks["Stop"] = [{"matcher": "", "hooks": [{"type": "command", "command": cmd_end}]}]
        settings["hooks"] = hooks

        # Configure MCP Servers
        mcp_servers = settings.get("mcpServers", {})
        repo_posix = str(self.env["repo_root"].resolve()).replace("\\", "/")
        mcp_servers["repowise"] = {
            "command": self.env["repowise_exe"],
            "args": ["mcp", repo_posix, "--transport", "stdio"],
            "description": "repowise: codebase intelligence -- docs, graph, git signals, dead code, decisions"
        }
        settings["mcpServers"] = mcp_servers

        self._write_json_safe(settings_path, settings)
        results["actions"].append(f"Configured Claude Code settings: {settings_path}")

        # 2. Synchronize ~/.claude/CLAUDE.md if needed
        global_md = self.env["claude_code_md"]
        template_md = self.env["platform_root"] / "Config" / "CLAUDE.md"
        if template_md.exists() and not global_md.exists():
            if not self.dry_run:
                global_md.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(template_md, global_md)
            results["actions"].append(f"Created global CLAUDE.md from template: {global_md}")

        # 3. Local project .mcp.json
        local_mcp_path = self.env["repo_root"] / ".mcp.json"
        local_mcp = self._read_json(local_mcp_path)
        local_servers = local_mcp.get("mcpServers", {})
        local_servers["repowise"] = {
            "command": "repowise",
            "args": ["mcp", repo_posix, "--transport", "stdio"],
            "description": "repowise: codebase intelligence -- docs, graph, git signals, dead code, decisions"
        }
        local_mcp["mcpServers"] = local_servers
        self._write_json_safe(local_mcp_path, local_mcp)
        results["actions"].append(f"Updated local .mcp.json: {local_mcp_path}")

        return results

    def install_claude_desktop(self) -> Dict[str, Any]:
        """
        Configure Claude Desktop GUI application (%APPDATA%/Claude/claude_desktop_config.json)
        Preserves all existing user preferences, cowork configs, and merges DEV_CORE MCP servers.
        """
        results: Dict[str, Any] = {"status": "OK", "actions": []}
        config_path = self.env["claude_desktop_config"]

        config = self._read_json(config_path)
        mcp_servers = config.get("mcpServers", {})

        repo_posix = str(self.env["repo_root"].resolve()).replace("\\", "/")
        mcp_servers["repowise"] = {
            "command": self.env["repowise_exe"],
            "args": ["mcp", repo_posix, "--transport", "stdio"],
            "description": "repowise: codebase intelligence -- docs, graph, git signals, dead code, decisions"
        }
        config["mcpServers"] = mcp_servers

        self._write_json_safe(config_path, config)
        results["actions"].append(f"Configured Claude Desktop GUI MCP: {config_path}")

        return results

    def install_universal(self) -> Dict[str, Any]:
        """
        Install integrations for all supported AI clients:
        - Claude Code & Claude Desktop GUI
        - Codex (.codex/config.toml)
        - Gemini / Antigravity (~/.gemini/settings.json & mcp_config.json)
        """
        results: Dict[str, Any] = {"status": "OK", "actions": []}

        # 1. Claude Code & Desktop
        res_code = self.install_claude_code()
        res_desktop = self.install_claude_desktop()
        results["actions"].extend(res_code["actions"])
        results["actions"].extend(res_desktop["actions"])

        repo_posix = str(self.env["repo_root"].resolve()).replace("\\", "/")
        repowise_exe = self.env["repowise_exe"]

        # 2. Gemini & Antigravity
        for g_dir in (self.env["gemini_dir"], self.env["antigravity_dir"]):
            g_settings_path = g_dir / "settings.json"
            g_settings = self._read_json(g_settings_path)
            g_mcp = g_settings.get("mcpServers", {})
            g_mcp["repowise"] = {
                "command": repowise_exe,
                "args": ["mcp", repo_posix, "--transport", "stdio"],
                "description": "repowise: codebase intelligence -- docs, graph, git signals, dead code, decisions"
            }
            g_settings["mcpServers"] = g_mcp
            self._write_json_safe(g_settings_path, g_settings)
            results["actions"].append(f"Configured Gemini/Antigravity settings: {g_settings_path}")

        # 3. Codex TOML config
        codex_config_path = self.env["codex_dir"] / "config.toml"
        repowise_cmd_escaped = str(repowise_exe).replace("\\", "/")
        codex_block = f"""
[mcp_servers.repowise]
command = '{repowise_cmd_escaped}'
args = [
  'mcp',
  '{repo_posix}',
  '--transport',
  'stdio',
]
startup_timeout_sec = 120
"""
        if not self.dry_run:
            codex_config_path.parent.mkdir(parents=True, exist_ok=True)
            content = ""
            if codex_config_path.exists():
                try:
                    with open(codex_config_path, "r", encoding="utf-8-sig") as f:
                        content = f.read()
                except Exception:
                    content = ""
            import re
            pattern = r"(?ms)^\[mcp_servers\.repowise\]\s*.*?(?=^\[[^\r\n]+\]|\Z)"
            if re.search(pattern, content):
                new_content = re.sub(pattern, lambda _: codex_block.strip(), content, count=1)
            else:
                new_content = content.rstrip() + "\n" + codex_block.strip() + "\n"
            with open(codex_config_path, "w", encoding="utf-8") as f:
                f.write(new_content.strip() + "\n")
        results["actions"].append(f"Configured Codex TOML config: {codex_config_path}")

        return results

    def verify(self) -> Dict[str, Any]:
        """
        Verify that all integrations and configs are properly installed and valid.
        """
        checks: List[Dict[str, str]] = []

        # Python Exe
        py_status = "PASS" if Path(self.env["python_exe"]).exists() or shutil.which(self.env["python_exe"]) else "FAIL"
        checks.append({
            "name": "Python Interpreter",
            "status": py_status,
            "details": str(self.env["python_exe"])
        })

        # Repowise Binary
        rep_status = "PASS" if self.env["repowise_exe"] == "repowise" or Path(self.env["repowise_exe"]).exists() else "WARN"
        checks.append({
            "name": "Repowise MCP Executable",
            "status": rep_status,
            "details": str(self.env["repowise_exe"])
        })

        # Claude Code Settings
        code_settings = self.env["claude_code_settings"]
        if code_settings.exists():
            data = self._read_json(code_settings)
            has_hooks = bool(data.get("hooks", {}).get("UserPromptSubmit"))
            has_mcp = bool(data.get("mcpServers", {}).get("repowise"))
            status = "PASS" if (has_hooks and has_mcp) else "WARN"
            details = f"Hooks: {'OK' if has_hooks else 'Missing'}, Repowise MCP: {'OK' if has_mcp else 'Missing'}"
        else:
            status = "FAIL"
            details = f"File not found: {code_settings}"
        checks.append({
            "name": "Claude Code Integration",
            "status": status,
            "details": details
        })

        # Claude Desktop Config
        desktop_config = self.env["claude_desktop_config"]
        if desktop_config.exists():
            data = self._read_json(desktop_config)
            has_mcp = bool(data.get("mcpServers", {}).get("repowise"))
            status = "PASS" if has_mcp else "WARN"
            details = f"Repowise MCP: {'OK' if has_mcp else 'Not configured'}"
        else:
            status = "WARN"
            details = f"File not found (Claude Desktop might not be opened yet): {desktop_config}"
        checks.append({
            "name": "Claude Desktop GUI Integration",
            "status": status,
            "details": details
        })

        # Local Repo MCP
        local_mcp = self.env["repo_root"] / ".mcp.json"
        if local_mcp.exists():
            data = self._read_json(local_mcp)
            has_mcp = bool(data.get("mcpServers", {}).get("repowise"))
            status = "PASS" if has_mcp else "WARN"
            details = f"Repowise MCP: {'OK' if has_mcp else 'Missing'}"
        else:
            status = "WARN"
            details = f"Local .mcp.json not found in {self.env['repo_root']}"
        checks.append({
            "name": "Local Repo MCP Config",
            "status": status,
            "details": details
        })

        overall = "PASS" if all(c["status"] == "PASS" for c in checks) else ("WARN" if all(c["status"] != "FAIL" for c in checks) else "FAIL")
        return {
            "overall_status": overall,
            "repo_root": str(self.env["repo_root"]),
            "checks": checks
        }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="DEV_CORE Claude & AI Clients Portable Setup")
    parser.add_argument("--target", choices=["claude", "desktop", "all"], default="all", help="Integration target")
    parser.add_argument("--repo-root", default=None, help="Custom repository root path")
    parser.add_argument("--dry-run", action="store_true", help="Simulate changes without modifying files")
    parser.add_argument("--verify", action="store_true", help="Verify integration status")

    args = parser.parse_args()
    installer = ClaudeInstaller(repo_root=args.repo_root, dry_run=args.dry_run)

    if args.verify:
        report = installer.verify()
        print(json.dumps(report, indent=2))
        return

    print(f"=== DEV_CORE AI Integration Setup (Target: {args.target}) ===")
    if args.target == "claude":
        res = installer.install_claude_code()
    elif args.target == "desktop":
        res = installer.install_claude_desktop()
    else:
        res = installer.install_universal()

    for action in res.get("actions", []):
        print(f"  [OK] {action}")

    print("\n--- Diagnostic & Verification ---")
    report = installer.verify()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
