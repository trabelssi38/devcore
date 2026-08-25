import os
import sys
import json
import html
import socket
import subprocess
import re
from datetime import datetime
from pathlib import Path

# Load environment or default paths
PLATFORM_ROOT = Path(os.environ.get("DEVCORE_PLATFORM_ROOT", str(Path(__file__).resolve().parents[3] / "DEV_CORE")))
DATA_ROOT = Path(os.environ.get("DEVCORE_DATA_ROOT", str(Path(__file__).resolve().parents[3] / "DEV_CORE_DATA")))
env_local = os.environ.get("DEVCORE_LOCAL_ROOT")
if env_local:
    LOCAL_ROOT = Path(env_local)
elif os.name == "nt" and os.getenv("LOCALAPPDATA"):
    LOCAL_ROOT = Path(os.getenv("LOCALAPPDATA")) / "DEV_CORE_LOCAL"
else:
    LOCAL_ROOT = DATA_ROOT.parent / "DEV_CORE_DATA_local"
IS_IN_DOCKER = Path("/.dockerenv").exists() or os.getenv("DEVCORE_PLATFORM_ROOT") == "/app/DEV_CORE"

SERVICE_HOSTS = {
    "qdrant": os.environ.get("QDRANT_HOST", "127.0.0.1"),
    "gemini_router": os.environ.get("GEMINI_ROUTER_HOST", "127.0.0.1"),
    "dashboard_api": os.environ.get("DASHBOARD_API_HOST", "127.0.0.1"),
    "headroom": os.environ.get("HEADROOM_HOST", "host.docker.internal" if IS_IN_DOCKER else "127.0.0.1"),
    "api": os.environ.get("API_HOST", "127.0.0.1"),
    "repowise": os.environ.get("REPOWISE_HOST", "127.0.0.1"),
}

def esc_html(val) -> str:
    """HTML escape for standard text content."""
    if val is None:
        return ""
    return html.escape(str(val))

def esc_attr(val) -> str:
    """HTML escape for attributes, with quotes enabled."""
    if val is None:
        return ""
    return html.escape(str(val), quote=True)

def format_time_ago(dt) -> str:
    if not dt:
        return "Jamais"
    ts = datetime.now() - dt
    if ts.days >= 1:
        return f"{round(ts.days)} jours"
    hours = ts.seconds // 3600
    if hours >= 1:
        return f"{round(hours)} heures"
    minutes = (ts.seconds % 3600) // 60
    if minutes >= 1:
        return f"{round(minutes)} mins"
    return f"{round(ts.seconds)} s"

def format_tokens(tokens) -> str:
    """Consolidated token format logic."""
    try:
        tokens_val = float(tokens)
    except (ValueError, TypeError):
        return "0"
    if tokens_val > 1000000:
        return f"{round(tokens_val/1000000, 2)}M"
    elif tokens_val > 0:
        return f"{round(tokens_val/1000, 1)}K"
    return "0"

def get_last_log_time(prefix: str, data_root: Path = None) -> datetime:
    search_dirs = []
    if data_root:
        search_dirs.append(data_root / "Logs" / "scripts")
    else:
        search_dirs.append(LOCAL_ROOT / "Logs" / "scripts")
        search_dirs.append(DATA_ROOT / "Logs" / "scripts")
    
    files = []
    for d in search_dirs:
        if d.exists():
            try:
                files.extend(list(d.glob(f"{prefix}*.log")))
            except Exception:
                pass
    if not files:
        return None
    try:
        files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        return datetime.fromtimestamp(files[0].stat().st_mtime)
    except Exception:
        return None

def is_process_running(script_name: str) -> bool:
    try:
        if sys.platform == "win32":
            cmd = ["wmic", "process", "where", "name='python.exe' or name='pythonw.exe'", "get", "commandline"]
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if os.name == "nt" else 0
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5, creationflags=creationflags)
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    if script_name in line:
                        return True
        else:
            # Linux / Docker container check
            proc_dir = Path("/proc")
            if proc_dir.exists():
                for pid_dir in proc_dir.glob("[0-9]*"):
                    try:
                        cmdline_file = pid_dir / "cmdline"
                        if cmdline_file.exists():
                            cmdline = cmdline_file.read_text(encoding="utf-8", errors="ignore").replace("\x00", " ")
                            if script_name in cmdline:
                                return True
                    except Exception:
                        pass
    except Exception as e:
        print(f"[Dashboard] Error checking process {script_name}: {e}", file=sys.stderr)
    return False

def check_port(service_name_or_port, port: int = None) -> bool:
    """Check if TCP port is open for given service or host."""
    if isinstance(service_name_or_port, str):
        service_name = service_name_or_port
        target_port = port
    else:
        service_name = "default"
        target_port = service_name_or_port

    clean_name = service_name.replace("-", "_") if isinstance(service_name, str) else service_name
    host = SERVICE_HOSTS.get(clean_name, service_name if isinstance(service_name, str) else "127.0.0.1")
    if host == "localhost":
        host = "127.0.0.1"
    elif not IS_IN_DOCKER and host in ["gemini-router", "dashboard-api", "headroom"]:
        host = "127.0.0.1"

    timeout_val = 0.1 if host in ("127.0.0.1", "localhost", "::1", "host.docker.internal") else 0.5
    try:
        with socket.create_connection((host, target_port), timeout=timeout_val):
            return True
    except Exception:
        if host != "127.0.0.1":
            try:
                with socket.create_connection(("127.0.0.1", target_port), timeout=0.1):
                    return True
            except Exception:
                pass
        return False

def get_task_datetime(t) -> datetime:
    for prop in ["committed_at", "completed_at", "started_at", "updated_at", "created_at"]:
        val = t.get(prop)
        if val:
            try:
                dt_part = val.strip()
                for sign in ["+", "-"]:
                    if sign in dt_part[10:]:
                        idx = 10 + dt_part[10:].index(sign)
                        dt_part = dt_part[:idx]
                        break
                dt_part = dt_part.strip()
                if "." in dt_part:
                    base, frac = dt_part.split(".", 1)
                    dt_part = f"{base}.{frac[:6]}"
                for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M"]:
                    try:
                        return datetime.strptime(dt_part, fmt)
                    except Exception:
                        pass
            except Exception:
                pass
    return datetime.min

def get_task_id_number(t) -> int:
    tid = t.get("id", "")
    if tid:
        if tid.startswith("T-GIT-"):
            return 0
        nums = re.findall(r"\d+", tid)
        if nums:
            try:
                return int("".join(nums))
            except Exception:
                pass
    return 0

def get_active_project(data_root: Path = DATA_ROOT) -> str:
    # Use cached env var if present
    cached = os.environ.get("DEVCORE_ACTIVE_PROJECT_NAME")
    if cached:
        return cached
    # Read active_project.txt if present
    try:
        txt_file = LOCAL_ROOT / "Runtime" / "active_project.txt"
        if not txt_file.exists():
            txt_file = DATA_ROOT / "Runtime" / "active_project.txt"
        if txt_file.exists():
            return txt_file.read_text(encoding="utf-8-sig").strip()
    except Exception:
        pass
    return "devcore"

def map_project_path(path_str: str) -> str:
    if not path_str:
        return ""
    in_docker = os.path.exists("/.dockerenv") or Path("/.dockerenv").exists()
    if in_docker:
        p_clean = path_str.replace("\\", "/")
        if p_clean.startswith("C:/src/"):
            return p_clean.replace("C:/src/", "/src/")
        if p_clean.startswith("C:/devcore"):
            return p_clean.replace("C:/devcore", "/app")
    return path_str

def load_project_paths(platform_root: Path = PLATFORM_ROOT) -> dict:
    paths = {}
    config_file = platform_root / "Config" / "projects.json"
    if config_file.exists():
        try:
            data = json.loads(config_file.read_text(encoding="utf-8-sig"))
            for p in data.get("projects", []):
                name = p.get("name")
                path = p.get("path")
                if name and path:
                    paths[name.lower()] = path
        except Exception:
            pass
    if "devcore" not in paths:
        paths["devcore"] = str(platform_root.parent)
    return paths

def count_project_files(project_path: str) -> int:
    if not project_path:
        return 0
    p_path = map_project_path(project_path)
    if not os.path.exists(p_path) or not os.path.isdir(p_path):
        return 0
    
    count = 0
    excluded_dirs = {".git", "node_modules", "venv", ".venv", ".pytest_cache", "__pycache__", ".repowise", "dist", "build"}
    try:
        for root, dirs, files in os.walk(p_path):
            dirs[:] = [d for d in dirs if d not in excluded_dirs]
            count += len(files)
    except Exception:
        pass
    return count

def get_status_html(title, desc, is_ok, perf=None, solic=None, impact=None) -> str:
    is_degraded = (is_ok == "degraded")
    if is_degraded:
        status_class = "status-degraded-badge"
        status_icon = "DEGRADED"
        status_label = "Service degraded"
    elif is_ok:
        status_class = "status-ok"
        status_icon = "&#10003;"
        status_label = "Service healthy"
    else:
        status_class = "status-error"
        status_icon = "&#10007;"
        status_label = "Service unavailable"
        
    metrics_html = ""
    if perf or solic or impact:
        metrics_html = '<div class="component-metrics" style="display:flex; flex-wrap:wrap; gap:6px; margin-top:8px; font-size:9px;">'
        if perf:
            metrics_html += f"<span style='padding:2px 6px; background:rgba(16,185,129,0.12); border:1px solid rgba(16,185,129,0.25); border-radius:4px; color:#34d399; font-weight:600;'>Perf: {perf}</span>"
        if solic:
            metrics_html += f"<span style='padding:2px 6px; background:rgba(99,102,241,0.12); border:1px solid rgba(99,102,241,0.25); border-radius:4px; color:#a5b4fc; font-weight:600;'>Solic: {solic}</span>"
        if impact:
            metrics_html += f"<span style='padding:2px 6px; background:rgba(251,191,36,0.12); border:1px solid rgba(251,191,36,0.25); border-radius:4px; color:#fde047; font-weight:600;'>Eff/Imp: {impact}</span>"
        metrics_html += '</div>'
        
    return f"""
<div class="component" style="display:flex; flex-direction:column; align-items:stretch; padding:12px 14px; margin-bottom:8px;">
  <div style="display:flex; justify-content:space-between; align-items:center;">
    <div style="flex: 1; min-width: 0;">
      <div class="component-name" style="font-size:12px; font-weight:600; color:#f1f5f9; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{title}</div>
      <div class="component-detail" style="font-size:10px; color:#94a3b8; margin-top:1px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{desc}</div>
    </div>
    <div class="{status_class}" aria-label="{status_label}" title="{status_label}" style="flex-shrink: 0; margin-left: 12px;">{status_icon}</div>
  </div>
  {metrics_html}
</div>
"""


def get_dropbox_sync_status() -> tuple[str, bool | str, str | None, str | None, str | None]:
    """
    Checks the status of Dropbox synchronization.
    Returns a tuple of: (desc, is_ok_status, perf, solic, impact)
    is_ok_status can be True (healthy), 'degraded' (warning/syncing), or False (offline/error).
    """
    import time
    dropbox_running = False
    if os.name == "nt":
        try:
            flags = 0x08000000
            output = subprocess.check_output(
                'tasklist /FI "IMAGENAME eq Dropbox.exe" /NH',
                shell=True,
                creationflags=flags,
                text=True
            )
            dropbox_running = "Dropbox.exe" in output
        except Exception:
            dropbox_running = False

    data_root = os.getenv("DEVCORE_DATA_ROOT", "")
    if not data_root:
        data_root = str(DATA_ROOT)
    
    normalized_path = data_root.lower()
    is_in_dropbox = "dropbox" in normalized_path

    if not is_in_dropbox:
        return "Non configuré (DEVCORE_DATA_ROOT hors Dropbox)", False, "Inactif", "Aucune", "Données Locales"

    if not dropbox_running:
        return "Dropbox déconnecté (processus non détecté)", "degraded", "Non synchronisé", "En attente", "Risque désynchronisation"

    db_file = Path(data_root) / "devcore.db"
    last_update_str = "Jamais"
    if db_file.exists():
        try:
            mtime = db_file.stat().st_mtime
            elapsed = time.time() - mtime
            if elapsed < 60:
                last_update_str = "A l'instant"
            elif elapsed < 3600:
                last_update_str = f"Il y a {int(elapsed // 60)}m"
            else:
                last_update_str = f"Il y a {int(elapsed // 3600)}h"
        except Exception:
            pass

    return "Dropbox actif & synchronisé", True, "Sync en ligne", f"MàJ base: {last_update_str}", "Sauvegarde Cloud"
