"""
system_watcher.py -- DEV_CORE Automated System Health Watcher & Auto-Healer
Continuously audits all core platform ports and services, automatically restarting any downed service.
"""

from __future__ import annotations
import sys
import os
import json
import socket
import sqlite3
import subprocess
import time
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional

# Resolve DEV_CORE platform root dynamically
platform_root_env = os.environ.get('DEVCORE_PLATFORM_ROOT')
if platform_root_env and Path(platform_root_env).exists():
    DEV_CORE_ROOT = Path(platform_root_env).resolve()
else:
    candidate = Path(__file__).parent.parent.parent.resolve()
    if (candidate / 'Scheduler').exists():
        DEV_CORE_ROOT = candidate
    else:
        cwd = Path.cwd().resolve()
        if (cwd / 'DEV_CORE' / 'Scheduler').exists():
            DEV_CORE_ROOT = (cwd / 'DEV_CORE').resolve()
        elif (cwd / 'Scheduler').exists():
            DEV_CORE_ROOT = cwd
        else:
            DEV_CORE_ROOT = candidate

if str(DEV_CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(DEV_CORE_ROOT))

scheduler_path = DEV_CORE_ROOT / 'Scheduler'
if scheduler_path.exists() and str(scheduler_path) not in sys.path:
    sys.path.insert(0, str(scheduler_path))

from devcore_engine.db import init_db, get_data_root, get_local_data_root
from devcore_engine.services.events import EventBus
from devcore_engine.infra.restart_budget import RestartBudget

try:
    from scheduler_presence import instance_available, child_ready, adopt_ready
    from scheduler_control import is_paused
    from service_control import services_paused, launch_guard
except ImportError as scheduler_import_error:
    import contextlib

    _scheduler_unavailable = str(scheduler_import_error)

    def _require_scheduler() -> None:
        raise RuntimeError(
            f"Scheduler unavailable under {DEV_CORE_ROOT}: {_scheduler_unavailable}"
        )

    def instance_available(root: Any) -> bool:
        _require_scheduler()

    def child_ready(*args: Any, **kwargs: Any) -> bool:
        _require_scheduler()

    def adopt_ready(*args: Any, **kwargs: Any) -> bool:
        _require_scheduler()

    def is_paused(root: Any) -> bool:
        _require_scheduler()

    def services_paused(root: Any) -> bool:
        _require_scheduler()

    @contextlib.contextmanager
    def launch_guard(root: Any):
        _require_scheduler()
        yield

DETACHED_FLAG = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
HEALTH_PROBE_SCRIPT = DEV_CORE_ROOT / "Scripts" / "probe_headroom_health.py"


def probe_headroom_health(route: str, timeout: float = 3.0) -> bool:
    from devcore_engine.infra.llm_route_contract import PORTS, validate_health
    if route not in PORTS:
        raise ValueError("Unknown route")
    if not 0 < timeout <= 3:
        raise ValueError("Health deadline must be positive and at most three seconds")
    try:
        result = subprocess.run([sys.executable, "-I", str(HEALTH_PROBE_SCRIPT), "--route", route],
            capture_output=True, text=True, timeout=timeout,
            creationflags=DETACHED_FLAG if os.name == "nt" else 0)
        return result.returncode == 0 and validate_health(json.loads(result.stdout), route)
    except Exception:
        return False


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
        if not 0 < wait_timeout <= 30:
            raise ValueError('Service startup wait must be positive and at most 30 seconds')
        if services_paused(self.local_root):
            return False
        try:
            with launch_guard(self.local_root):
                if services_paused(self.local_root):
                    return False
                return self._check_and_heal_service(name, host, port, launch_cmd, cwd, wait_timeout)
        except OSError as exc:
            self.log(f'WARNING: Service launch gate busy/unavailable: {exc}')
            return False

    def _check_and_heal_service(self, name, host, port, launch_cmd, cwd, wait_timeout):
        if not 0 < wait_timeout <= 30:
            raise ValueError("Service startup wait must be positive and at most 30 seconds")
        is_online = check_port(host, port)
        route = {8787: "native", 8789: "auxiliary"}.get(port) if host == "127.0.0.1" else None
        if is_online:
            return probe_headroom_health(route) if route else True

        budget = RestartBudget(self.local_root / "Runtime" / "service_restarts.sqlite3")
        service_key = f"{host}:{port}"
        try:
            owner, reason = budget.reserve(service_key)
        except Exception as exc:
            self.log(f"ERROR: Restart reservation unavailable for '{name}': {exc}")
            return False
        if owner is None:
            self.log(f"WARNING: Service '{name}' restart withheld: {reason}")
            return False

        self.log(f"WARNING: Service '{name}' on {host}:{port} is OFFLINE. Attempting bounded auto-restart...")

        try:
            # Another instance may have recovered the service before reservation.
            if check_port(host, port):
                return probe_headroom_health(route) if route else True
            work_dir = cwd or DEV_CORE_ROOT
            process = subprocess.Popen(
                launch_cmd,
                env=dict(os.environ, DEVCORE_LOCAL_ROOT=str(self.local_root),
                    DEVCORE_DATA_ROOT=str(self.data_root), DEVCORE_PLATFORM_ROOT=str(DEV_CORE_ROOT)),
                cwd=str(work_dir),
                creationflags=DETACHED_FLAG if os.name == "nt" else 0,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Wait up to `wait_timeout` seconds for recovery
            recovered = False
            deadline = time.monotonic() + wait_timeout
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    self.log(f"ERROR: Service '{name}' exited during startup (code {process.returncode}).")
                    return False
                time.sleep(min(0.5, max(0, deadline - time.monotonic())))
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                if check_port(host, port, timeout=min(0.5, remaining)):
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        break
                    if route and not probe_headroom_health(route, timeout=min(3, remaining)):
                        continue
                    if time.monotonic() >= deadline:
                        break
                    if process.poll() is not None:
                        self.log(f"ERROR: Service '{name}' exited before recovery validation (code {process.returncode}).")
                        return False
                    recovered = True
                    break

            if recovered:
                self.log(f"SUCCESS: Service '{name}' auto-restarted and is now ONLINE on port {port}.")
                self.event_bus.publish(
                    "ServiceAutoHealed",
                    {"service": name, "port": port, "status": "READY" if route else "ONLINE",
                     "verification": "route_contract" if route else "tcp_listener"},
                    project="devcore"
                )
                return True
            else:
                self.log(f"ERROR: Failed to restart service '{name}' on port {port} after {wait_timeout} seconds.")
                return False
        except Exception as e:
            self.log(f"ERROR: Exception while restarting '{name}': {e}")
            return False
        finally:
            try:
                budget.release(service_key, owner)
            except Exception as exc:
                self.log(f"ERROR: Restart lease release failed for '{name}': {exc}")

    def ensure_scheduler_daemon(self, wait_timeout: float = 5.0) -> bool:
        if type(wait_timeout) not in (int, float) or not 0 < wait_timeout <= 30:
            raise ValueError('Scheduler wait must be positive and at most 30 seconds')
        if services_paused(self.local_root):
            return False
        try:
            with launch_guard(self.local_root):
                if services_paused(self.local_root):
                    return False
                return self._ensure_scheduler_daemon(wait_timeout)
        except OSError as exc:
            self.log(f'WARNING: Scheduler launch gate busy/unavailable: {exc}')
            return False

    def _ensure_scheduler_daemon(self, wait_timeout):
        """Bounded launch or point-in-time identity/profile verification."""
        if type(wait_timeout) not in (int, float) or not 0 < wait_timeout <= 30:
            raise ValueError('Scheduler wait must be positive and at most 30 seconds')
        if is_paused(self.local_root):
            self.log('WARNING: Scheduler explicitly paused; no launch or readiness claim')
            return False
        process = getattr(self, '_scheduler_process', None)
        if process is not None and process.poll() is None:
            return child_ready(self.local_root, self._scheduler_token, process)
        if not instance_available(self.local_root):
            ready = adopt_ready(self.local_root, self.data_root, DEV_CORE_ROOT)
            if not ready:
                self.log('WARNING: Scheduler busy/unavailable; identity/readiness not confirmed, no duplicate launch')
            return ready
        budget = RestartBudget(self.local_root / 'Runtime/service_restarts.sqlite3')
        key = 'scheduler-daemon'
        owner = None
        try:
            owner, reason = budget.reserve(key)
            if owner is None:
                self.log(f'WARNING: Scheduler restart withheld: {reason}')
                return False
            if not instance_available(self.local_root):
                return False
            deadline = time.monotonic() + wait_timeout
            token = uuid.uuid4().hex
            env = dict(os.environ, DEVCORE_LOCAL_ROOT=str(self.local_root),
                DEVCORE_DATA_ROOT=str(self.data_root), DEVCORE_PLATFORM_ROOT=str(DEV_CORE_ROOT),
                DEVCORE_SCHEDULER_START_TOKEN=token)
            scheduler_script = DEV_CORE_ROOT / "Scheduler" / "scheduler_tick.py"
            process = subprocess.Popen(
                [sys.executable, str(scheduler_script)],
                cwd=str(DEV_CORE_ROOT),
                creationflags=DETACHED_FLAG if os.name == 'nt' else 0,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self._scheduler_process, self._scheduler_token = process, token
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    break
                if child_ready(self.local_root, token, process) and time.monotonic() < deadline:
                    self.log('SUCCESS: Scheduler child initialized history and loaded valid registry')
                    return True
                time.sleep(min(.1, max(0, deadline - time.monotonic())))
            self.log('WARNING: Scheduler startup not confirmed; pending child retained, no blind repeat')
            return False
        except Exception as e:
            self.log(f"ERROR: Failed to start Scheduler Daemon: {e}")
            return False
        finally:
            if owner is not None:
                try:
                    budget.release(key, owner)
                except Exception as exc:
                    self.log(f'ERROR: Scheduler restart reservation release failed: {exc}')

    def check_docker_status(self) -> Dict[str, Any]:
        result = {"available": False, "containers": []}
        try:
            proc = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}|{{.Status}}|{{.Ports}}"],
                capture_output=True,
                text=True,
                timeout=3,
                creationflags=DETACHED_FLAG
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
        if services_paused(self.local_root):
            return {'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'PAUSED', 'services': {}}
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

        # 3. Separate guarded Headroom processes; no shared config rewrite.
        import shutil
        headroom_exe = shutil.which("headroom")
        if not headroom_exe:
            py_scripts_headroom = Path(sys.prefix) / "Scripts" / "headroom.exe"
            if py_scripts_headroom.exists():
                headroom_exe = str(py_scripts_headroom)
        if not headroom_exe:
            custom_paths = [
                Path(os.path.expanduser(r"~\AppData\Roaming\Python\Python314\Scripts\headroom.exe")),
                Path(os.path.expanduser(r"~\AppData\Roaming\Python\Python313\Scripts\headroom.exe")),
                Path(os.path.expanduser(r"~\AppData\Roaming\Python\Scripts\headroom.exe")),
                Path(r"C:\Python314\Scripts\headroom.exe"),
                Path(r"C:\Python313\Scripts\headroom.exe"),
                Path(r"C:\Program Files\Python313\Scripts\headroom.exe"),
            ]
            for p in custom_paths:
                if p.exists():
                    headroom_exe = str(p)
                    break

        if headroom_exe:
            headroom_python = (Path(headroom_exe).parent.parent / "python.exe") if os.name == "nt" else Path(headroom_exe).with_name("python")
            if not headroom_python.exists():
                headroom_python = Path(sys.executable)
            for route, port, key in (("native", 8787, "headroom_proxy"), ("auxiliary", 8789, "headroom_auxiliary")):
                command = [str(headroom_python), str(DEV_CORE_ROOT / "Scripts" / "headroom_routes.py"), "--route", route]
                report[key] = self.check_and_heal_service(f"Headroom {route}", "127.0.0.1", port, command, wait_timeout=15.0)
                if report[key]:
                    report[key] = probe_headroom_health(route)
                    if not report[key]:
                        self.log(f"Port {port} occupied by an unqualified route; explicit restart required")
        else:
            report["headroom_proxy"] = False
            report["headroom_auxiliary"] = False
            self.log("Headroom runtime unavailable; install/qualify it explicitly")

        # Port 8788 is optional auxiliary translation, never native Claude.

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
