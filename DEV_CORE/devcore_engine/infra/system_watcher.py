"""
system_watcher.py -- DEV_CORE Automated System Health Watcher & Auto-Healer
Continuously audits all core platform ports and services, automatically restarting any downed service.
"""

from __future__ import annotations
import sys
import os
import socket
import sqlite3
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

# Ensure DEV_CORE is on sys.path
DEV_CORE_ROOT = Path(__file__).parent.parent.parent.resolve()
if str(DEV_CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(DEV_CORE_ROOT))

from devcore_engine.db import init_db, get_data_root
from devcore_engine.services.events import EventBus

DETACHED_FLAG = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)


def check_port(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


class SystemWatcher:
    def __init__(self, conn: Optional[sqlite3.Connection] = None):
        self.conn = conn or init_db()
        self.data_root = get_data_root()
        self.local_root = get_local_data_root()
        self.event_bus = EventBus(self.conn)
        self.log_dir = self.local_root / "Logs" / "scripts"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / f"system_watcher_{time.strftime('%Y-%m-%d')}.log"

    def log(self, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        line = f"[{timestamp}] [WATCHDOG] {message}\n"
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            pass

    def check_and_heal_service(self, name: str, host: str, port: int, launch_cmd: List[str], cwd: Optional[Path] = None, wait_timeout: float = 15.0) -> bool:
        is_online = check_port(host, port)
        if is_online:
            return True

        self.log(f"WARNING: Service '{name}' on {host}:{port} is OFFLINE. Attempting auto-restart...")

        try:
            work_dir = cwd or DEV_CORE_ROOT
            subprocess.Popen(
                launch_cmd,
                cwd=str(work_dir),
                creationflags=DETACHED_FLAG,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Wait up to `wait_timeout` seconds for recovery
            recovered = False
            iterations = int(wait_timeout / 0.5)
            for _ in range(iterations):
                time.sleep(0.5)
                if check_port(host, port):
                    recovered = True
                    break

            if recovered:
                self.log(f"SUCCESS: Service '{name}' auto-restarted and is now ONLINE on port {port}.")
                self.event_bus.publish(
                    "ServiceAutoHealed",
                    {"service": name, "port": port, "status": "ONLINE"},
                    project="devcore"
                )
                return True
            else:
                self.log(f"ERROR: Failed to restart service '{name}' on port {port} after {wait_timeout} seconds.")
                return False
        except Exception as e:
            self.log(f"ERROR: Exception while restarting '{name}': {e}")
            return False

    def ensure_scheduler_daemon(self) -> bool:
        """Ensure DevCore scheduler_tick daemon is running."""
        try:
            # Check via wmic or tasklist on Windows
            proc = subprocess.run(
                ["wmic", "process", "where", "name='python.exe'", "get", "commandline"],
                capture_output=True,
                text=True,
                timeout=3
            )
            if "scheduler_tick" in proc.stdout:
                return True
        except Exception:
            pass

        self.log("WARNING: DevCore Scheduler Daemon (scheduler_tick.py) is OFFLINE. Launching background daemon...")
        try:
            scheduler_script = DEV_CORE_ROOT / "Scheduler" / "scheduler_tick.py"
            subprocess.Popen(
                [sys.executable, str(scheduler_script)],
                cwd=str(DEV_CORE_ROOT),
                creationflags=DETACHED_FLAG,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.log("SUCCESS: Scheduler Daemon started in background.")
            return True
        except Exception as e:
            self.log(f"ERROR: Failed to start Scheduler Daemon: {e}")
            return False

    def check_docker_status(self) -> Dict[str, Any]:
        result = {"available": False, "containers": []}
        try:
            proc = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}|{{.Status}}|{{.Ports}}"],
                capture_output=True,
                text=True,
                timeout=3
            )
            if proc.returncode == 0:
                result["available"] = True
                lines = proc.stdout.strip().split("\n")
                for l in lines:
                    if l.strip():
                        parts = l.split("|")
                        result["containers"].append({
                            "name": parts[0] if len(parts) > 0 else "",
                            "status": parts[1] if len(parts) > 1 else "",
                            "ports": parts[2] if len(parts) > 2 else ""
                        })
        except Exception:
            pass
        return result

    def audit_and_heal(self) -> Dict[str, Any]:
        self.log("Starting system health audit...")
        report = {}

        # 0. Ensure Scheduler Daemon is running
        report["scheduler_daemon"] = self.ensure_scheduler_daemon()

        # 1. Gemini Router (20130)
        router_cmd = [sys.executable, str(DEV_CORE_ROOT / "Scripts" / "gemini_router.py")]
        report["gemini_router"] = self.check_and_heal_service("Gemini Router", "127.0.0.1", 20130, router_cmd, wait_timeout=5.0)

        # 2. Dashboard API (20129)
        dash_cmd = [sys.executable, str(DEV_CORE_ROOT / "Scripts" / "dashboard_api.py")]
        report["dashboard_api"] = self.check_and_heal_service("Dashboard API", "127.0.0.1", 20129, dash_cmd, wait_timeout=5.0)

        # 3. Headroom Proxy (8787) - needs 15s start timeout
        # Align headroom_config.yaml paths with dynamic self.data_root
        headroom_cfg = DEV_CORE_ROOT / "Config" / "headroom_config.yaml"
        if headroom_cfg.exists():
            try:
                cache_p = (self.local_root / "Cache" / "headroom").as_posix()
                stats_p = (self.data_root / "Metrics" / "headroom_stats.json").as_posix()
                (self.local_root / "Cache" / "headroom").mkdir(parents=True, exist_ok=True)
                (self.data_root / "Metrics").mkdir(parents=True, exist_ok=True)
                cfg_content = headroom_cfg.read_text(encoding="utf-8")
                lines = []
                for line in cfg_content.splitlines():
                    if "cache_dir:" in line:
                        lines.append(f'  cache_dir: "{cache_p}"')
                    elif "output:" in line and "headroom_stats.json" in line:
                        lines.append(f'  output: "{stats_p}"')
                    else:
                        lines.append(line)
                headroom_cfg.write_text("\n".join(lines) + "\n", encoding="utf-8")
            except Exception:
                pass

        import shutil
        headroom_exe = shutil.which("headroom")
        if not headroom_exe:
            py_scripts_headroom = Path(sys.prefix) / "Scripts" / "headroom.exe"
            if py_scripts_headroom.exists():
                headroom_exe = str(py_scripts_headroom)
        if not headroom_exe:
            custom_paths = [
                Path(os.path.expanduser(r"~\AppData\Roaming\Python\Python313\Scripts\headroom.exe")),
                Path(os.path.expanduser(r"~\AppData\Roaming\Python\Python314\Scripts\headroom.exe")),
                Path(r"C:\Users\trb_m\AppData\Roaming\Python\Python313\Scripts\headroom.exe"),
                Path(os.path.expanduser(r"~\AppData\Roaming\Python\Scripts\headroom.exe")),
                Path(r"C:\Program Files\Python313\Scripts\headroom.exe"),
            ]
            for p in custom_paths:
                if p.exists():
                    headroom_exe = str(p)
                    break

        if headroom_exe:
            headroom_cmd = [headroom_exe, "proxy", "--port", "8787", "--openai-api-url", "http://127.0.0.1:20130/v1"]
        else:
            ps_exe = "powershell.exe" if os.name == "nt" else "pwsh"
            headroom_cmd = [ps_exe, "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-NonInteractive", "-NoProfile", "-File", str(DEV_CORE_ROOT / "Scripts" / "headroom_start.ps1")]

        report["headroom_proxy"] = self.check_and_heal_service("Headroom Proxy", "127.0.0.1", 8787, headroom_cmd, wait_timeout=15.0)

        # 4. Anthropic Adapter (8788)
        anthropic_cmd = [sys.executable, str(DEV_CORE_ROOT / "Scripts" / "anthropic_adapter.py")]
        report["anthropic_adapter"] = self.check_and_heal_service("Anthropic Adapter", "127.0.0.1", 8788, anthropic_cmd, wait_timeout=5.0)

        # 5. Repowise Server (7337)
        import shutil
        repowise_exe = shutil.which("repowise") or r"C:\Program Files\Python313\Scripts\repowise.exe"
        if Path(repowise_exe).exists():
            repowise_cmd = [repowise_exe, "serve", "--host", "127.0.0.1", "--port", "7337", "--no-ui"]
        else:
            repowise_cmd = [sys.executable, str(DEV_CORE_ROOT / "Scripts" / "start_repowise_server.py")]
        report["repowise_server"] = self.check_and_heal_service("Repowise Server", "127.0.0.1", 7337, repowise_cmd, wait_timeout=5.0)

        # 6. Docker Audit
        docker_status = self.check_docker_status()
        report["docker"] = docker_status

        # 7. Multi-Project Git Scan
        try:
            from devcore_engine.infra.multi_project_git_scanner import MultiProjectGitScanner
            git_scanner = MultiProjectGitScanner(self.conn)
            scan_res = git_scanner.scan_all_projects(days=14)
            report["git_scan"] = scan_res
        except Exception as e:
            self.log(f"Git scan warning: {e}")

        all_ok = all(v is True for k, v in report.items() if k not in ("docker", "git_scan"))
        self.log(f"System audit completed. Overall status: {'HEALTHY' if all_ok else 'DEGRADED'}")

        return {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "HEALTHY" if all_ok else "DEGRADED",
            "services": report
        }


if __name__ == "__main__":
    watcher = SystemWatcher()
    res = watcher.audit_and_heal()
    print(f"[SystemWatcher] Audit result: {res}")
