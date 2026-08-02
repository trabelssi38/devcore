import http.server
import socketserver
import urllib.parse
import json
import gzip
import subprocess
from pathlib import Path
import os
import re
import sys
import hmac
import hashlib
import secrets
from datetime import datetime
import time
import random

PORT = 20129
PLATFORM_ROOT = os.getenv("DEVCORE_PLATFORM_ROOT", "C:/devcore/DEV_CORE")
DATA_ROOT = os.getenv("DEVCORE_DATA_ROOT", "C:/devcore/DEV_CORE_DATA")
API_SCHEMA_VERSION = 1
DASHBOARD_COMMAND_TIMEOUT_SEC = 90.0
PLUGIN_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")
SAFE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")
PUBLIC_BIND_HOSTS = {"0.0.0.0", "::", ""}
PUBLIC_PATHS = {"/", "/index.html", "/index_terminal.html", "/favicon.ico", "/api/status", "/api/dashboard", "/api/dashboard/stream", "/api/dashboard/tasks", "/api/dashboard/events", "/api/dashboard/tokens"}
TOKEN_BYTES = 32
CSRF_BYTES = 32
CSRF_HEADER = "X-CSRF-Token"
DEFAULT_ALLOWED_ORIGINS = ["http://127.0.0.1:20129", "http://localhost:20129"]
DEFAULT_MAX_REQUEST_BODY_BYTES = 1024 * 1024
DEFAULT_DASHBOARD_RESOURCE_PAGE_SIZE = 20
MAX_DASHBOARD_RESOURCE_PAGE_SIZE = 100
CACHE_CONTROL_HEADER = "private, max-age=5, must-revalidate"
GZIP_MIN_RESPONSE_BYTES = 1024
DASHBOARD_SSE_POLL_SECONDS = 2.0
DASHBOARD_SSE_HEARTBEAT_SECONDS = 15.0
SENSITIVE_SETTING_KEYS = {"gemini_api_key", "anthropic_api_key"}
RUNTIME_SETTING_KEYS = {"active_client"}
DEFAULT_PUBLIC_SETTINGS = {
    "auto_refresh_seconds": 15,
    "services": {
        "qdrant": True,
        "gemini_router": True,
        "dashboard_api": True,
        "headroom": True,
        "hermes_daemon": True,
        "repowise": True,
    },
}


class RequestTooLarge(ValueError):
    pass


def canonical_path(path):
    return Path(path).resolve()


def ensure_within_root(path, root):
    resolved_root = canonical_path(root)
    resolved_path = canonical_path(path)
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"Path escapes allowed root: {resolved_root}") from exc
    return resolved_path


def get_platform_path(*parts):
    return ensure_within_root(Path(PLATFORM_ROOT).joinpath(*parts), PLATFORM_ROOT)


def get_data_path(*parts):
    return ensure_within_root(Path(DATA_ROOT).joinpath(*parts), DATA_ROOT)


def validate_safe_id(value, label):
    value = str(value or "").strip()
    if (
        not SAFE_ID_PATTERN.fullmatch(value)
        or "/" in value
        or "\\" in value
        or ":" in value
        or ".." in value
    ):
        raise ValueError(f"Invalid {label}: {value}")
    return value


def header_value(headers, name, default=""):
    if not headers or not hasattr(headers, "get"):
        return default
    return headers.get(name) or headers.get(name.lower()) or default


def make_response_etag(body):
    return f'"sha256-{hashlib.sha256(body).hexdigest()}"'


def client_accepts_gzip(headers):
    accepted = header_value(headers, "Accept-Encoding", "")
    return "gzip" in [item.strip().split(";", 1)[0].lower() for item in accepted.split(",")]


def build_cached_json_response(payload, request_headers):
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    etag = make_response_etag(body)
    response_headers = {
        "Content-Type": "application/json; charset=utf-8",
        "ETag": etag,
        "X-Payload-Hash": etag.strip('"'),
        "Cache-Control": CACHE_CONTROL_HEADER,
        "Vary": "Accept-Encoding",
    }

    if header_value(request_headers, "If-None-Match", "").strip() == etag:
        response_headers["Content-Length"] = "0"
        return {"status": 304, "headers": response_headers, "body": b""}

    if client_accepts_gzip(request_headers) and len(body) >= GZIP_MIN_RESPONSE_BYTES:
        body = gzip.compress(body)
        response_headers["Content-Encoding"] = "gzip"

    response_headers["Content-Length"] = str(len(body))
    return {"status": 200, "headers": response_headers, "body": body}


def stable_json_bytes(value):
    return json.dumps(value or {}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def read_model_fingerprint(read_model):
    return hashlib.sha256(stable_json_bytes(read_model)).hexdigest()


def build_dashboard_delta(previous_read_model, current_read_model):
    previous = previous_read_model or {}
    current = current_read_model or {}
    keys = sorted(set(previous.keys()) | set(current.keys()))
    changed_keys = [key for key in keys if previous.get(key) != current.get(key)]
    return {
        "schema_version": 1,
        "generated_at": datetime.now().isoformat(),
        "has_changes": bool(changed_keys),
        "changed_keys": changed_keys,
        "fingerprint": read_model_fingerprint(current),
        "read_model": {key: current.get(key) for key in changed_keys},
    }


def format_sse_event(event_name, data, event_id=None, retry=None):
    lines = []
    if event_id:
        lines.append(f"id: {event_id}")
    if retry is not None:
        lines.append(f"retry: {int(retry)}")
    lines.append(f"event: {event_name}")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    for line in payload.splitlines() or [""]:
        lines.append(f"data: {line}")
    lines.append("")
    lines.append("")
    return "\n".join(lines).encode("utf-8")


def format_sse_comment(comment):
    return f": {comment}\n\n".encode("utf-8")


def get_project_tasks_file(project):
    safe_project = validate_safe_id(project, "project")
    memory_root = get_data_path("Memory")
    return ensure_within_root(memory_root / safe_project / "tasks.json", memory_root)


def get_settings_file_path():
    return get_platform_path("Config", "settings.json")


def get_settings_secrets_path():
    return get_data_path("Security", "dashboard_settings_secrets.json")


def get_active_client_runtime_path():
    return get_data_path("Runtime", "active_client.txt")


def sanitize_public_settings(data):
    return {
        key: value
        for key, value in dict(data or {}).items()
        if key not in SENSITIVE_SETTING_KEYS and key not in RUNTIME_SETTING_KEYS
    }


def extract_setting_secrets(data):
    return {
        key: str(data.get(key)).strip()
        for key in SENSITIVE_SETTING_KEYS
        if str(data.get(key, "")).strip()
    }


def read_active_client(default="antigravity"):
    runtime_path = get_active_client_runtime_path()
    if runtime_path.exists():
        value = runtime_path.read_text(encoding="utf-8").strip()
        if value:
            return value

    legacy_path = get_platform_path("Config", "active_client.txt")
    if legacy_path.exists():
        value = legacy_path.read_text(encoding="utf-8").strip()
        if value:
            return value

    return default


def write_active_client(value):
    value = str(value or "").strip()
    if not value:
        return
    runtime_path = get_active_client_runtime_path()
    runtime_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_path.write_text(value, encoding="utf-8")


def _read_network_config():
    config_path = get_platform_path("Config", "network.json")
    if not config_path.exists():
        return {}
    try:
        return read_json_with_retry(config_path)
    except Exception as exc:
        print(f"[DashboardAPI] Unable to read network config {config_path}: {exc}")
        return {}


def get_bind_host():
    host = os.getenv("DEVCORE_DASHBOARD_BIND", "").strip()
    if not host:
        config = _read_network_config()
        host = (
            config.get("services", {})
            .get("dashboard_api", {})
            .get("host")
            or config.get("default_bind_host")
            or "127.0.0.1"
        )
    host = str(host).strip()
    if host in PUBLIC_BIND_HOSTS and os.getenv("DEVCORE_ALLOW_PUBLIC_BIND") != "1":
        raise ValueError("Public bind requires DEVCORE_ALLOW_PUBLIC_BIND=1")
    return host or "127.0.0.1"


def _read_security_config():
    config_path = get_platform_path("Config", "security.json")
    if not config_path.exists():
        return {}
    try:
        return read_json_with_retry(config_path)
    except Exception as exc:
        print(f"[DashboardAPI] Unable to read security config {config_path}: {exc}")
        return {}


def get_allowed_origins():
    env_value = os.getenv("DEVCORE_CORS_ALLOWED_ORIGINS", "").strip()
    if env_value:
        return [item.strip() for item in env_value.split(",") if item.strip()]
    config = _read_security_config()
    origins = config.get("cors", {}).get("allowed_origins")
    if isinstance(origins, list) and origins:
        return [str(origin).strip() for origin in origins if str(origin).strip()]
    return list(DEFAULT_ALLOWED_ORIGINS)


def is_origin_allowed(origin):
    if not origin:
        return True
    return origin in get_allowed_origins()


def get_max_request_body_bytes():
    env_value = os.getenv("DEVCORE_MAX_REQUEST_BODY_BYTES", "").strip()
    if env_value:
        try:
            return max(1, int(env_value))
        except ValueError:
            return DEFAULT_MAX_REQUEST_BODY_BYTES
    config = _read_security_config()
    value = config.get("limits", {}).get("max_request_body_bytes", DEFAULT_MAX_REQUEST_BODY_BYTES)
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return DEFAULT_MAX_REQUEST_BODY_BYTES


def is_request_too_large(headers):
    raw_value = headers.get("Content-Length") if hasattr(headers, "get") else None
    if raw_value in (None, ""):
        return False
    try:
        return int(raw_value) > get_max_request_body_bytes()
    except ValueError:
        return True


def get_token_store_path():
    return get_data_path("Security", "dashboard_api_token.json")


def get_csrf_store_path():
    return get_data_path("Security", "dashboard_api_csrf.json")


def hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def write_token_record(token):
    token_path = get_token_store_path()
    token_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "schema_version": 1,
        "token_hash": hash_token(token),
        "created_at": datetime.now().isoformat(),
        "rotated_at": datetime.now().isoformat(),
    }
    write_json_with_retry(token_path, record)


def read_token_record():
    token_path = get_token_store_path()
    if not token_path.exists():
        return None
    return read_json_with_retry(token_path)


def write_csrf_record(token):
    token_path = get_csrf_store_path()
    token_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "schema_version": 1,
        "token_hash": hash_token(token),
        "created_at": datetime.now().isoformat(),
        "rotated_at": datetime.now().isoformat(),
    }
    write_json_with_retry(token_path, record)


def read_csrf_record():
    token_path = get_csrf_store_path()
    if not token_path.exists():
        return None
    return read_json_with_retry(token_path)


def ensure_csrf_token():
    record = read_csrf_record()
    bootstrap_path = get_data_path("Security", "dashboard_api_csrf.bootstrap")
    if record and record.get("token_hash"):
        if bootstrap_path.exists():
            return bootstrap_path.read_text(encoding="utf-8").strip()
        return ""

    token = secrets.token_urlsafe(CSRF_BYTES)
    write_csrf_record(token)
    bootstrap_path.parent.mkdir(parents=True, exist_ok=True)
    bootstrap_path.write_text(token, encoding="utf-8")
    return token


def validate_csrf_token(token):
    if not token:
        return False
    record = read_csrf_record()
    if not record or not record.get("token_hash"):
        return False
    return hmac.compare_digest(hash_token(token), str(record["token_hash"]))


def ensure_api_token():
    record = read_token_record()
    bootstrap_path = get_data_path("Security", "dashboard_api_token.bootstrap")
    if record and record.get("token_hash"):
        if bootstrap_path.exists():
            return bootstrap_path.read_text(encoding="utf-8").strip()
        return ""

    token = secrets.token_urlsafe(TOKEN_BYTES)
    write_token_record(token)
    bootstrap_path.parent.mkdir(parents=True, exist_ok=True)
    bootstrap_path.write_text(token, encoding="utf-8")
    return token


def rotate_api_token():
    token = secrets.token_urlsafe(TOKEN_BYTES)
    write_token_record(token)
    bootstrap_path = get_data_path("Security", "dashboard_api_token.bootstrap")
    bootstrap_path.parent.mkdir(parents=True, exist_ok=True)
    bootstrap_path.write_text(token, encoding="utf-8")
    return token


def validate_api_token(token):
    if not token:
        return False
    record = read_token_record()
    if not record or not record.get("token_hash"):
        return False
    return hmac.compare_digest(hash_token(token), str(record["token_hash"]))


def requires_authentication(path):
    if path.startswith("/api/dashboard"):
        return False
    return path not in PUBLIC_PATHS


def is_authorized(headers):
    authorization = headers.get("Authorization") if hasattr(headers, "get") else None
    if not authorization or not authorization.startswith("Bearer "):
        return False
    token = authorization[len("Bearer "):].strip()
    return validate_api_token(token)


def requires_csrf(method, path):
    if method.upper() in {"GET", "HEAD", "OPTIONS"}:
        return False
    return path.startswith("/api/")


def is_csrf_authorized(headers):
    token = headers.get(CSRF_HEADER) if hasattr(headers, "get") else None
    return validate_csrf_token(token)


def inject_auth_fetch(html_content):
    token = ensure_api_token()
    csrf_token = ensure_csrf_token()
    if not token:
        return html_content
    snippet = f"""
<script>
window.DEVCORE_API_TOKEN = {json.dumps(token)};
window.DEVCORE_CSRF_TOKEN = {json.dumps(csrf_token)};
(function() {{
  const originalFetch = window.fetch;
  window.fetch = function(resource, options) {{
    options = options || {{}};
    const url = typeof resource === 'string' ? resource : (resource && resource.url) || '';
    if (url.startsWith('/api/') || url.includes('127.0.0.1:20129/api/') || url.includes('localhost:20129/api/')) {{
      options.headers = Object.assign({{}}, options.headers || {{}}, {{
        Authorization: 'Bearer ' + window.DEVCORE_API_TOKEN,
        'X-CSRF-Token': window.DEVCORE_CSRF_TOKEN
      }});
    }}
    return originalFetch(resource, options);
  }};
}})();
</script>
"""
    if "</head>" in html_content:
        return html_content.replace("</head>", snippet + "\n</head>", 1)
    return snippet + html_content

def read_json_with_retry(file_path, retries=5, delay=0.05):
    for attempt in range(retries):
        try:
            with open(file_path, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except (IOError, PermissionError) as e:
            print(f"[DashboardAPI] Read attempt {attempt+1}/{retries} failed for {file_path}: {e}")
            if attempt < retries - 1:
                time.sleep(delay + random.uniform(0.01, 0.05))
            else:
                raise
        except json.JSONDecodeError as e:
            print(f"[DashboardAPI] JSON decode failed: {e}")
            if attempt < retries - 1:
                time.sleep(delay + random.uniform(0.01, 0.05))
            else:
                raise

def write_json_with_retry(file_path, data, retries=5, delay=0.05):
    for attempt in range(retries):
        try:
            temp_path = Path(file_path).with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            if Path(file_path).exists():
                os.replace(str(temp_path), str(file_path))
            else:
                temp_path.rename(file_path)
            return
        except (IOError, PermissionError, OSError) as e:
            print(f"[DashboardAPI] Write attempt {attempt+1}/{retries} failed for {file_path}: {e}")
            if attempt < retries - 1:
                time.sleep(delay + random.uniform(0.01, 0.05))
            else:
                raise


def run_plugin_check(plugin_id):
    if not PLUGIN_ID_PATTERN.fullmatch(plugin_id or ""):
        raise ValueError(f"Invalid plugin id: {plugin_id}")

    dc_script = get_platform_path("Scripts", "dc.ps1")
    cmd = [
        "powershell.exe",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(dc_script),
        f"plugin check {plugin_id} --json",
    ]
    env = os.environ.copy()
    env["DEVCORE_DATA_ROOT"] = DATA_ROOT
    result = subprocess.run(
        cmd,
        capture_output=True,
        encoding="utf-8",
        timeout=DASHBOARD_COMMAND_TIMEOUT_SEC,
        env=env,
    )
    if result.returncode != 0:
        details = (result.stderr or result.stdout or "plugin check failed").strip()
        raise RuntimeError(details)
    return json.loads(result.stdout)


def get_dashboard_read_model_path():
    return get_data_path("Dashboard", "read_model.json")


def get_cached_dashboard_payload_path():
    return get_data_path("Dashboard", "dashboard_payload.json")


def load_dashboard_read_model():
    read_model_path = get_dashboard_read_model_path()
    if not read_model_path.exists():
        return None
    return read_json_with_retry(read_model_path)


def build_fallback_dashboard_payload():
    return {
        "schema_version": API_SCHEMA_VERSION,
        "generated_at": datetime.now().isoformat(),
        "sections": {},
        "task_details": {},
        "token_metrics": {},
        "read_model": load_dashboard_read_model(),
        "cache": {"hit": False},
    }


def read_cached_dashboard_payload():
    cache_path = get_cached_dashboard_payload_path()
    if not cache_path.exists():
        return None
    payload = read_json_with_retry(cache_path)
    if payload.get("schema_version") != API_SCHEMA_VERSION:
        raise RuntimeError(f"Unsupported dashboard schema: {payload.get('schema_version')}")
    payload["read_model"] = load_dashboard_read_model()
    payload["cache"] = {"hit": True, "path": str(cache_path)}
    return payload


def get_nested_value(data, dotted_path):
    current = data
    for part in str(dotted_path or "").split("."):
        if not part:
            raise ValueError("resource path is required")
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            raise ValueError(f"Unknown dashboard resource: {dotted_path}")
    return current


def validate_page_value(value, name, default, max_value=None):
    if value in (None, ""):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid {name}: {value}") from exc
    if parsed < 1:
        raise ValueError(f"Invalid {name}: {value}")
    if max_value:
        parsed = min(parsed, max_value)
    return parsed


def paginate_items(items, page=1, page_size=DEFAULT_DASHBOARD_RESOURCE_PAGE_SIZE):
    page = validate_page_value(page, "page", 1)
    page_size = validate_page_value(
        page_size,
        "page_size",
        DEFAULT_DASHBOARD_RESOURCE_PAGE_SIZE,
        MAX_DASHBOARD_RESOURCE_PAGE_SIZE,
    )
    item_list = list(items if isinstance(items, list) else [items])
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "page": page,
        "page_size": page_size,
        "total": len(item_list),
        "has_next": end < len(item_list),
        "items": item_list[start:end],
    }


def build_dashboard_resource(resource_name, page=1, page_size=DEFAULT_DASHBOARD_RESOURCE_PAGE_SIZE):
    page = validate_page_value(page, "page", 1)
    page_size = validate_page_value(
        page_size,
        "page_size",
        DEFAULT_DASHBOARD_RESOURCE_PAGE_SIZE,
        MAX_DASHBOARD_RESOURCE_PAGE_SIZE,
    )
    read_model = load_dashboard_read_model() or {}
    root = {"read_model": read_model}
    value = get_nested_value(root, resource_name)
    response = paginate_items(value, page=page, page_size=page_size)
    response["schema_version"] = 1
    response["resource"] = resource_name
    return response


def build_dashboard_payload():
    cache_path = get_cached_dashboard_payload_path()
    # If cache exists and is fresh (< 5 seconds), use cached payload, otherwise regenerate on the fly
    if cache_path.exists():
        age = datetime.now().timestamp() - cache_path.stat().st_mtime
        if age < 5:
            cached = read_cached_dashboard_payload()
            if cached:
                return cached
    
    try:
        refresh_dashboard_payload_cache()
        cached = read_cached_dashboard_payload()
        if cached:
            return cached
    except Exception as e:
        print(f"[DashboardAPI] On-the-fly dashboard refresh failed, using cached payload: {e}")
        cached = read_cached_dashboard_payload()
        if cached:
            return cached
            
    return build_fallback_dashboard_payload()


def refresh_dashboard_payload_cache():
    dashboard_script = get_platform_path("Scripts", "gen_dashboard.py")
    cmd = [
        sys.executable,
        str(dashboard_script),
        "-Json",
        "-SkipTokenRefresh",
    ]
    print(f"[DashboardAPI] Running gen_dashboard.py -Json (timeout={DASHBOARD_COMMAND_TIMEOUT_SEC:.0f}s)...")
    result = subprocess.run(cmd, capture_output=True, encoding="utf-8", timeout=DASHBOARD_COMMAND_TIMEOUT_SEC)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "Dashboard generator failed").strip())

    payload_text = result.stdout.strip()
    if not payload_text:
        raise RuntimeError("Dashboard generator returned an empty payload")

    payload = json.loads(payload_text)
    if payload.get("schema_version") != API_SCHEMA_VERSION:
        raise RuntimeError(f"Unsupported dashboard schema: {payload.get('schema_version')}")
    payload["read_model"] = load_dashboard_read_model()
    cache_path = get_cached_dashboard_payload_path()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    write_json_with_retry(cache_path, payload)
    return payload

# Standalone functions extracted from DashboardAPIHandler
def get_settings():
    settings_file = get_settings_file_path()
    if not settings_file.exists():
        defaults = dict(DEFAULT_PUBLIC_SETTINGS)
        defaults["active_client"] = read_active_client()
        return defaults
    try:
        settings = sanitize_public_settings(read_json_with_retry(settings_file))
        settings.setdefault("auto_refresh_seconds", DEFAULT_PUBLIC_SETTINGS["auto_refresh_seconds"])
        settings.setdefault("services", DEFAULT_PUBLIC_SETTINGS["services"])
        settings["active_client"] = read_active_client()
        return settings
    except Exception:
        return {}

def save_settings(data):
    settings_file = get_settings_file_path()
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    write_json_with_retry(settings_file, sanitize_public_settings(data))

    secrets_data = extract_setting_secrets(data)
    if secrets_data:
        secrets_file = get_settings_secrets_path()
        secrets_file.parent.mkdir(parents=True, exist_ok=True)
        write_json_with_retry(secrets_file, secrets_data)

    active_client = data.get("active_client")
    write_active_client(active_client)

def complete_task(project, task_id):
    tasks_file = get_project_tasks_file(project)
    if not tasks_file.exists():
        return False, f"Project board not found: {tasks_file}"

    try:
        print(f"[DashboardAPI] Completing task {task_id} on project {project}...")
        board = read_json_with_retry(tasks_file)

        task_found = False
        is_active = False
        for task in board.get("tasks", []):
            if task.get("id") == task_id:
                task_found = True
                is_active = (task.get("status") == "active")
                task["status"] = "done"
                task["steps_done"] = task.get("steps_total", 1)
                task["completed_at"] = datetime.now().isoformat()
                break

        if not task_found:
            return False, f"Task {task_id} not found in project {project}"

        write_json_with_retry(tasks_file, board)
        print(f"[DashboardAPI] Successfully saved completed task status in tasks.json.")

        if is_active:
            task_done_script = get_platform_path("Scripts", "task_done.ps1")
            ps_exe = shutil.which("powershell.exe") or shutil.which("powershell") or shutil.which("pwsh") or r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
            cmd = [ps_exe, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", 
                   str(task_done_script), "-Force"]
            print(f"[DashboardAPI] Running task_done.ps1 for active task completion (timeout={DASHBOARD_COMMAND_TIMEOUT_SEC:.0f}s)...")
            subprocess.run(cmd, capture_output=True, timeout=DASHBOARD_COMMAND_TIMEOUT_SEC)
            return True, f"Active task {task_id} completed successfully via task_done.ps1"
        else:
            dashboard_script = get_platform_path("Scripts", "gen_dashboard.py")
            cmd = [sys.executable, str(dashboard_script)]
            print(f"[DashboardAPI] Running gen_dashboard.py for dashboard refresh (timeout={DASHBOARD_COMMAND_TIMEOUT_SEC:.0f}s)...")
            subprocess.run(cmd, capture_output=True, timeout=DASHBOARD_COMMAND_TIMEOUT_SEC)
            return True, f"Task {task_id} completed successfully"

    except subprocess.TimeoutExpired as te:
        print(f"[DashboardAPI] Timeout expired executing completion script: {te}")
        return True, f"Task {task_id} completed but post-completion command timed out"
    except Exception as e:
        print(f"[DashboardAPI] Error completing task: {e}")
        return False, str(e)

def delete_task(project, task_id):
    tasks_file = get_project_tasks_file(project)
    if not tasks_file.exists():
        return False, f"Project board not found: {tasks_file}"

    try:
        print(f"[DashboardAPI] Deleting task {task_id} on project {project}...")
        board = read_json_with_retry(tasks_file)

        original_count = len(board.get("tasks", []))
        board["tasks"] = [t for t in board.get("tasks", []) if t.get("id") != task_id]

        if len(board["tasks"]) == original_count:
            return False, f"Task {task_id} not found in project {project}"

        if board.get("current_task") == task_id:
            board["current_task"] = None

        write_json_with_retry(tasks_file, board)
        print(f"[DashboardAPI] Successfully saved deleted task in tasks.json.")

        dashboard_script = get_platform_path("Scripts", "gen_dashboard.py")
        cmd = [sys.executable, str(dashboard_script)]
        print(f"[DashboardAPI] Running gen_dashboard.py for dashboard refresh (timeout={DASHBOARD_COMMAND_TIMEOUT_SEC:.0f}s)...")
        subprocess.run(cmd, capture_output=True, timeout=DASHBOARD_COMMAND_TIMEOUT_SEC)
        return True, f"Task {task_id} deleted successfully"

    except subprocess.TimeoutExpired as te:
        print(f"[DashboardAPI] Timeout expired executing delete refresh script: {te}")
        return True, f"Task {task_id} deleted but dashboard refresh timed out"
    except Exception as e:
        print(f"[DashboardAPI] Error deleting task: {e}")
        return False, str(e)

# FastAPI imports and Application Setup
from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import uvicorn
import shutil

app = FastAPI(title="DEV_CORE Dashboard API Server", version="10.1.0")

# CORS setup matching get_allowed_origins()
allowed_origins = get_allowed_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def check_auth(request: Request) -> bool:
    path = request.url.path
    if not requires_authentication(path):
        return True
    
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return False
    token = auth_header[7:]
    return validate_api_token(token)

def check_csrf(request: Request, method: str) -> bool:
    path = request.url.path
    if not requires_csrf(method, path):
        return True
    
    csrf_header = request.headers.get("X-CSRF-Token")
    if not csrf_header:
        return False
    return validate_csrf_token(csrf_header)

def get_last_modified_timestamp():
    # Watch tasks.json, devcore.db, and events.jsonl
    projName = "devcore" # Default project
    try:
        proj_script = get_platform_path("Scripts", "Get-ActiveProject.ps1")
        if proj_script.exists():
            ps_exe = shutil.which("powershell.exe") or shutil.which("powershell") or shutil.which("pwsh") or r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
            res = subprocess.run([ps_exe, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(proj_script)], capture_output=True, text=True, timeout=2)
            if res.returncode == 0 and res.stdout.strip():
                projName = res.stdout.strip()
    except Exception:
        pass
    
    files_to_watch = [
        get_data_path("Memory", projName, "tasks.json"),
        get_data_path("devcore.db"),
        get_data_path("Bus", "events.jsonl")
    ]
    
    mtimes = []
    for f in files_to_watch:
        if f.exists():
            try:
                mtimes.append(f.stat().st_mtime)
            except Exception:
                pass
    return max(mtimes) if mtimes else 0.0

async def event_generator(request: Request):
    # Emit initial connection event
    yield "event: message\ndata: Connected\n\n"
    
    last_ts = get_last_modified_timestamp()
    last_heartbeat = asyncio.get_event_loop().time()
    
    while True:
        if await request.is_disconnected():
            break
        
        await asyncio.sleep(1.0)
        
        try:
            current_ts = get_last_modified_timestamp()
            if current_ts > last_ts:
                last_ts = current_ts
                # Regenerate dashboard to refresh server cache
                try:
                    refresh_dashboard_payload_cache()
                except Exception as e:
                    print(f"[DashboardAPI-SSE] Error updating cache: {e}")
                
                # Emit delta with has_changes=True to trigger client refresh
                delta = {
                    "schema_version": 1,
                    "generated_at": datetime.now().isoformat(),
                    "has_changes": True,
                    "changed_keys": ["all"],
                    "fingerprint": f"ts_{current_ts}",
                    "read_model": {},
                }
                yield f"event: dashboard.delta\ndata: {json.dumps(delta)}\n\n"
                last_heartbeat = asyncio.get_event_loop().time()
                
            elif asyncio.get_event_loop().time() - last_heartbeat >= DASHBOARD_SSE_HEARTBEAT_SECONDS:
                yield ": heartbeat\n\n"
                last_heartbeat = asyncio.get_event_loop().time()
        except Exception as e:
            print(f"[DashboardAPI-SSE] Error in loop: {e}")

@app.get("/")
@app.get("/index.html", response_class=HTMLResponse)
async def serve_index(request: Request):
    index_path = get_platform_path("Dashboard", "index.html")
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    html_content = index_path.read_text(encoding="utf-8")
    return HTMLResponse(content=inject_auth_fetch(html_content))

@app.get("/index_terminal.html", response_class=HTMLResponse)
async def serve_terminal_index(request: Request):
    term_path = get_platform_path("Dashboard", "index_terminal.html")
    if not term_path.exists():
        raise HTTPException(status_code=404, detail="index_terminal.html not found")
    html_content = term_path.read_text(encoding="utf-8")
    return HTMLResponse(content=inject_auth_fetch(html_content))

@app.get("/api/status")
async def status_route():
    return {"status": "success", "message": "API Server Active"}

@app.get("/api/settings")
async def get_settings_route(request: Request):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return get_settings()

@app.post("/api/settings")
async def post_settings_route(request: Request):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not check_csrf(request, "POST"):
        raise HTTPException(status_code=403, detail="Invalid CSRF Token")
    
    data = await request.json()
    save_settings(data)
    return {"status": "success", "message": "Settings saved successfully"}

@app.get("/api/dashboard")
async def get_dashboard_route(request: Request, limit: int = None):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        payload = build_dashboard_payload()
        if limit is not None:
            if isinstance(payload.get("events_raw"), list):
                payload["events_raw"] = payload["events_raw"][:limit]
        
        # Build cached/gzip response if possible
        response_data = build_cached_json_response(payload, dict(request.headers))
        if response_data["status"] == 304:
            return Response(status_code=304, headers=response_data["headers"])
        
        return Response(status_code=response_data["status"], headers=response_data["headers"], content=response_data["body"])
    except subprocess.TimeoutExpired as te:
        print(f"[DashboardAPI] Timeout calling gen_dashboard.ps1 -Json: {te}")
        raise HTTPException(status_code=504, detail=f"Dashboard payload generation timed out after {DASHBOARD_COMMAND_TIMEOUT_SEC:.0f}s")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard/tasks")
async def get_dashboard_tasks_route(request: Request, project: str = "", limit: int = 20, offset: int = 0):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        db_path = get_data_path("devcore.db")
        import sqlite3
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        if project:
            cur.execute("SELECT id, project, title, status, mode, steps_total, steps_done, started_at, completed_at FROM tasks WHERE project = ? ORDER BY CAST(SUBSTR(id, 3) AS INTEGER) DESC LIMIT ? OFFSET ?", (project, limit, offset))
        else:
            cur.execute("SELECT id, project, title, status, mode, steps_total, steps_done, started_at, completed_at FROM tasks ORDER BY CAST(SUBSTR(id, 3) AS INTEGER) DESC LIMIT ? OFFSET ?", (limit, offset))
        rows = cur.fetchall()
        tasks = []
        for r in rows:
            tasks.append({
                "id": r[0], "project": r[1], "title": r[2], "status": r[3],
                "mode": r[4], "steps_total": r[5], "steps_done": r[6],
                "started_at": r[7], "completed_at": r[8]
            })
        conn.close()
        return tasks
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/done")
async def post_done_route(request: Request):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not check_csrf(request, "POST"):
        raise HTTPException(status_code=403, detail="Invalid CSRF Token")
    
    data = await request.json()
    project = data.get("project", "")
    task_id = data.get("id", "")
    if not project or not task_id:
        raise HTTPException(status_code=400, detail="Missing project or id")
    
    success, msg = complete_task(project, task_id)
    if success:
        return {"status": "success", "message": msg}
    else:
        raise HTTPException(status_code=500, detail=msg)

@app.delete("/api/delete")
async def delete_route(request: Request):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not check_csrf(request, "DELETE"):
        raise HTTPException(status_code=403, detail="Invalid CSRF Token")
    
    data = await request.json()
    project = data.get("project", "")
    task_id = data.get("id", "")
    if not project or not task_id:
        raise HTTPException(status_code=400, detail="Missing project or id")
    
    success, msg = delete_task(project, task_id)
    if success:
        return {"status": "success", "message": msg}
    else:
        raise HTTPException(status_code=500, detail=msg)

@app.post("/api/refresh")
async def post_refresh_route(request: Request):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not check_csrf(request, "POST"):
        raise HTTPException(status_code=403, detail="Invalid CSRF Token")
    
    try:
        payload = refresh_dashboard_payload_cache()
        return JSONResponse(content=payload)
    except subprocess.TimeoutExpired as te:
        print(f"[DashboardAPI] Timeout calling gen_dashboard.ps1: {te}")
        raise HTTPException(status_code=504, detail=f"Dashboard regeneration timed out after {DASHBOARD_COMMAND_TIMEOUT_SEC:.0f}s")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard/stream")
async def dashboard_stream_route(request: Request):
    return StreamingResponse(event_generator(request), media_type="text/event-stream")

def main():
    if "--rotate-token" in sys.argv:
        token = rotate_api_token()
        print(token)
        return

    ensure_api_token()
    ensure_csrf_token()
    
    bind_host = get_bind_host()
    print(f"DEV_CORE Dashboard API Server listening on {bind_host}:{PORT}...")
    try:
        uvicorn.run(app, host=bind_host, port=PORT, log_level="warning")
    except KeyboardInterrupt:
        print("\nShutting down API Server.")
        sys.exit(0)

if __name__ == "__main__":
    main()
