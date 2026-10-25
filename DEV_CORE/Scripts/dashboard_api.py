
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
import sqlite3
from contextlib import closing, contextmanager
from queue import Empty, LifoQueue
from threading import BoundedSemaphore
from datetime import datetime
import time
import random
import uuid

sys.path.append(str(Path(__file__).resolve().parent))
from dashboard.snapshots import resolve_snapshot, read_snapshot_artifact, pin_snapshot
from dashboard.refresh_coordinator import RefreshCoordinator
from dashboard.input_watcher import InputWatcher
from dashboard.error_reporter import SseErrorReporter
from dashboard.stream_admission import AdmittedStreamingResponse, StreamCapacityExceeded, StreamSlots
from dashboard.sse_cursor import parse_snapshot_cursor, event_frame

PORT = 20129
PLATFORM_ROOT = os.getenv("DEVCORE_PLATFORM_ROOT", str(Path(__file__).resolve().parent.parent))
DATA_ROOT = os.getenv("DEVCORE_DATA_ROOT", str(Path(PLATFORM_ROOT).parent / "DEV_CORE_DATA"))
API_SCHEMA_VERSION = 1
DASHBOARD_COMMAND_TIMEOUT_SEC = 90.0
PLUGIN_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")
SAFE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")
PUBLIC_BIND_HOSTS = {"0.0.0.0", "::", ""}
PUBLIC_PATHS = {"/", "/index.html", "/index_terminal.html", "/favicon.ico", "/api/status", "/api/dashboard", "/api/dashboard/stream", "/api/dashboard/events", "/api/dashboard/tokens", "/api/memory/search"}
TOKEN_BYTES = 32
CSRF_BYTES = 32
CSRF_HEADER = "X-CSRF-Token"
DEFAULT_ALLOWED_ORIGINS = ["http://127.0.0.1:20129", "http://localhost:20129"]
DEFAULT_MAX_REQUEST_BODY_BYTES = 1024 * 1024
DEFAULT_DASHBOARD_RESOURCE_PAGE_SIZE = 20
DASHBOARD_AUTH_PROFILE = os.environ.get("DEVCORE_DASHBOARD_AUTH_PROFILE", "legacy").strip()
POSTGRES_DASHBOARD = os.environ.get("DEVCORE_IDENTITY_READ_MODE", "").strip().lower() == "postgres"
POSTGRES_DSN = os.environ.get("DEVCORE_DATABASE_URL", "").strip()
if DASHBOARD_AUTH_PROFILE not in {"legacy", "individual"}:
    raise ValueError("Unknown DEVCORE_DASHBOARD_AUTH_PROFILE")
HTTP_CONTEXT_MAX_BYTES = int(os.environ.get("DEVCORE_HTTP_CONTEXT_MAX_BYTES", "12000"))
if not 256 <= HTTP_CONTEXT_MAX_BYTES <= 65536:
    raise ValueError("DEVCORE_HTTP_CONTEXT_MAX_BYTES must be 256..65536")
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


env_local = os.getenv("DEVCORE_LOCAL_ROOT")
if env_local:
    LOCAL_ROOT = Path(env_local)
elif os.name == "nt" and os.getenv("LOCALAPPDATA"):
    LOCAL_ROOT = Path(os.getenv("LOCALAPPDATA")) / "DEV_CORE_LOCAL"
else:
    LOCAL_ROOT = Path(DATA_ROOT).parent / "DEV_CORE_DATA_local"


def get_local_path(*parts):
    return Path(LOCAL_ROOT).joinpath(*parts)


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
    target_path = memory_root / safe_project / "tasks.json"
    if not target_path.exists() and memory_root.exists():
        for p_dir in memory_root.iterdir():
            if p_dir.is_dir() and p_dir.name.lower() == safe_project.lower():
                alt_path = p_dir / "tasks.json"
                if alt_path.exists():
                    return ensure_within_root(alt_path, memory_root)
    return ensure_within_root(target_path, memory_root)



def get_settings_file_path():
    return get_platform_path("Config", "settings.json")


def get_settings_secrets_path():
    return get_data_path("Security", "dashboard_settings_secrets.json")


def get_active_client_runtime_path():
    return get_local_path("Runtime", "active_client.txt")


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
    if os.getenv("DEVCORE_REQUIRE_AUTH_ALL") == "1":
        return path not in {"/", "/index.html", "/index_terminal.html", "/favicon.ico"}
    if path == "/api/dashboard/tasks":
        return True
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
    if DASHBOARD_AUTH_PROFILE == "individual" or os.getenv("DEVCORE_SUPPRESS_HTML_TOKEN") == "1":
        return html_content
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
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if os.name == "nt" else 0
    result = subprocess.run(
        cmd,
        capture_output=True,
        encoding="utf-8",
        timeout=DASHBOARD_COMMAND_TIMEOUT_SEC,
        env=env,
        creationflags=creationflags,
    )
    if result.returncode != 0:
        details = (result.stderr or result.stdout or "plugin check failed").strip()
        raise RuntimeError(details)
    return json.loads(result.stdout)


def get_dashboard_read_model_path():
    return get_local_path("Dashboard", "read_model.json")


def get_cached_dashboard_payload_path():
    """Unreserved diagnostic/setup path; use pinned reads for production contents."""
    snapshot = resolve_snapshot(get_local_path("Dashboard"))
    if snapshot is not None:
        return snapshot[0] / "dashboard_payload.json"
    return get_local_path("Dashboard", "dashboard_payload.json")


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
        "cache": {"hit": False, "snapshot_cursor": None},
    }


def read_cached_dashboard_payload():
    snapshot_cursor = None
    with pin_snapshot(get_local_path("Dashboard")) as snapshot:
        if snapshot is not None:
            cache_path = snapshot.directory / "dashboard_payload.json"
            snapshot_cursor = "snapshot:" + snapshot.manifest["generation"]
            payload = json.loads(read_snapshot_artifact(snapshot, "dashboard_payload.json"))
            modified_at = os.fstat(snapshot.streams["dashboard_payload.json"].fileno()).st_mtime
        else:
            cache_path = get_local_path("Dashboard", "dashboard_payload.json")
            try:
                with cache_path.open("r", encoding="utf-8") as stream:
                    payload = json.load(stream)
                    modified_at = os.fstat(stream.fileno()).st_mtime
            except FileNotFoundError:
                return None
    if payload.get("schema_version") != API_SCHEMA_VERSION:
        raise RuntimeError(f"Unsupported dashboard schema: {payload.get('schema_version')}")
    payload["read_model"] = load_dashboard_read_model()
    payload["cache"] = {"hit": True, "path": str(cache_path), "modified_at": modified_at,
                        "snapshot_cursor": snapshot_cursor}
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
    cached = read_cached_dashboard_payload()
    if cached:
        # Timestamp and contents were read from the same open file descriptor.
        age = datetime.now().timestamp() - cached["cache"]["modified_at"]
        if 0 <= age < 5:
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
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if os.name == "nt" else 0
    result = subprocess.run(cmd, capture_output=True, encoding="utf-8", timeout=DASHBOARD_COMMAND_TIMEOUT_SEC, creationflags=creationflags)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "Dashboard generator failed").strip())

    payload_text = result.stdout.strip()
    if not payload_text:
        raise RuntimeError("Dashboard generator returned an empty payload")

    payload = json.loads(payload_text)
    if payload.get("schema_version") != API_SCHEMA_VERSION:
        raise RuntimeError(f"Unsupported dashboard schema: {payload.get('schema_version')}")
    # The locked generator owns the cache and its hash. Enrichment is response-only.
    payload["read_model"] = load_dashboard_read_model()
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

from devcore_engine.services.task_mutations import (
    TaskMutationConflict,
    complete_task_usecase,
    transition_task_usecase,
    delete_task_usecase,
)


def complete_task(project, task_id, expected_version=None, *, context=None):
    if POSTGRES_DASHBOARD:
        return _postgres_task_mutation(project, task_id, expected_version, "task.complete", "done", context)
    return complete_task_usecase(
        project,
        task_id,
        expected_version=expected_version,
        context=context,
        db_path=get_local_path("devcore.db"),
    )


def transition_individual_task(project, task_id, expected_version, *, operation, context):
    if POSTGRES_DASHBOARD:
        target = "paused" if operation == "pause" else "in_progress"
        return _postgres_task_mutation(project, task_id, expected_version, f"task.{operation}", target, context)[0]
    return transition_task_usecase(
        project,
        task_id,
        operation,
        expected_version=expected_version,
        context=context,
        db_path=get_local_path("devcore.db"),
    )


def delete_task(project, task_id, expected_version=None, *, context=None):
    if POSTGRES_DASHBOARD:
        return _postgres_task_mutation(project, task_id, expected_version, "task.delete", "deleted", context)
    return delete_task_usecase(
        project,
        task_id,
        expected_version=expected_version,
        context=context,
        db_path=get_local_path("devcore.db"),
    )


def _postgres_connect():
    from urllib.parse import urlparse
    import pg8000.dbapi
    parsed = urlparse(POSTGRES_DSN.replace("postgresql+pg8000://", "postgresql://", 1))
    return pg8000.dbapi.connect(user=parsed.username, password=parsed.password,
        host=parsed.hostname or "127.0.0.1", port=parsed.port or 5432,
        database=(parsed.path or "/postgres").lstrip("/"))


_task_read_idle = LifoQueue(maxsize=20)
_task_read_slots = BoundedSemaphore(20)


@contextmanager
def _postgres_task_read_connection():
    """Bound reused connections; rollback removes transaction-local RLS context."""
    if not _task_read_slots.acquire(timeout=5):
        raise RuntimeError("PostgreSQL task reader capacity reached")
    conn = None
    try:
        try:
            conn = _task_read_idle.get_nowait()
        except Empty:
            conn = _postgres_connect()
        yield conn
    finally:
        if conn is not None:
            try:
                conn.rollback()
                _task_read_idle.put_nowait(conn)
            except Exception:
                conn.close()
        _task_read_slots.release()


def _postgres_scoped_browser_tasks(secret, project, origin, limit, offset):
    """Authorize and project tasks on one connection in one worker thread."""
    from devcore_engine.security.identity import READ, AuthenticationRequired, ProjectAccessDenied, IdentityUnavailable
    from devcore_engine.security.postgres_browser_sessions import authorize_session

    try:
        with _postgres_task_read_connection() as conn:
            authorize_session(POSTGRES_DSN, secret, project, READ, origin, connection=conn)
            cur = conn.cursor()
            cur.execute("SELECT set_config('app.current_project_id', %s, true)", (project,))
            cur.execute("SELECT legacy_id, project_id, title, status, mode, steps_total, steps_done, started_at, completed_at, version FROM tasks WHERE project_id = %s AND status <> 'deleted' ORDER BY created_at, task_number LIMIT %s OFFSET %s", (project, limit, offset))
            rows = cur.fetchall()
        return [{"id": r[0], "project": r[1], "title": r[2], "status": r[3],
                 "mode": r[4], "steps_total": r[5], "steps_done": r[6],
                 "started_at": r[7], "completed_at": r[8], "version": r[9]} for r in rows]
    except (AuthenticationRequired, ProjectAccessDenied, IdentityUnavailable):
        raise
    except Exception as exc:
        raise IdentityUnavailable("PostgreSQL task reader unavailable") from exc


def _postgres_task_mutation(project, task_id, expected_version, action, target, context):
    if context is None or context.project_id != project or not context.user_id:
        raise TaskMutationConflict("Project mutation principal required", "project_access_denied")
    if type(expected_version) is not int or expected_version < 1:
        raise TaskMutationConflict("Task version required", "task_version_required")
    conn = _postgres_connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT set_config('app.current_project_id', %s, false)", (project,))
        cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (project,))
        cur.execute("SELECT task_uuid, legacy_id, status, version, depends_on_uuid FROM tasks WHERE project_id=%s AND (legacy_id=%s OR task_uuid::text=%s) FOR UPDATE", (project, task_id, task_id))
        rows = cur.fetchall()
        if len(rows) > 1:
            raise TaskMutationConflict("Ambiguous task identifier", "ambiguous_task_identifier")
        row = rows[0] if rows else None
        if row is None:
            return (False, f"Task {task_id} not found in project")
        task_uuid, legacy_id, before, version, dependency_uuid = row
        if expected_version is not None and expected_version != version:
            raise TaskMutationConflict("Task version conflict", "stale_task_version")
        allowed = {"task.pause": "in_progress", "task.resume": "paused", "task.complete": None, "task.delete": None}
        if action in ("task.pause", "task.resume") and before != allowed[action]:
            raise TaskMutationConflict("Task transition is not valid", "invalid_transition")
        if before == "deleted":
            return (False, f"Task {task_id} not found in project")
        if action == "task.complete" and before == "done":
            conn.commit()
            return (True, "Task already completed")
        if action == "task.delete":
            cur.execute("SELECT legacy_id FROM tasks WHERE project_id=%s AND depends_on_uuid=%s AND status IN ('todo','in_progress') LIMIT 1", (project, task_uuid))
            dependent = cur.fetchone()
            if dependent:
                conn.rollback()
                return (False, f"Task {task_id} is required by {dependent[0]}")
        if action == "task.resume":
            cur.execute("SELECT 1 FROM tasks WHERE project_id=%s AND status='in_progress' LIMIT 1", (project,))
            if cur.fetchone():
                raise TaskMutationConflict("Project already has an active task", "task_transition_conflict")
            if dependency_uuid:
                cur.execute("SELECT status FROM tasks WHERE project_id=%s AND task_uuid=%s", (project, dependency_uuid))
                dependency = cur.fetchone()
                if dependency is None or dependency[0] != "done":
                    raise TaskMutationConflict("Task dependency incomplete", "task_transition_conflict")
        new_version = version + 1
        cur.execute("UPDATE tasks SET status=%s, version=%s, steps_done=CASE WHEN %s='done' THEN steps_total ELSE steps_done END, completed_at=CASE WHEN %s='done' THEN now() ELSE completed_at END, updated_at=now() WHERE task_uuid=%s", (target, new_version, target, target, task_uuid))
        details = json.dumps({"schema_version": 1, "before": {"status": before, "version": version}, "after": {"status": target, "version": new_version}})
        actor = getattr(context, "user_id", None) or "system"
        cur.execute("INSERT INTO audit_log (id, project_id, task_uuid, actor, action, entity_type, entity_id, details) VALUES (%s,%s,%s,%s,%s,'task',%s,%s::jsonb)", (str(uuid.uuid4()), project, task_uuid, actor, action, legacy_id or str(task_uuid), details))
        event_type = {"task.complete": "TaskCompleted", "task.delete": "TaskDeleted",
                      "task.pause": "TaskPaused", "task.resume": "TaskResumed"}[action]
        payload = json.dumps({"task_id": legacy_id or str(task_uuid), "before_status": before,
                              "after_status": target, "version": new_version})
        cur.execute("INSERT INTO events (id, project_id, task_uuid, event_type, source, payload) VALUES (%s,%s,%s,%s,%s,%s::jsonb)",
                    (str(uuid.uuid4()), project, task_uuid, event_type, "dashboard", payload))
        conn.commit()
        return (True, "Task transition completed" if action in ("task.pause", "task.resume") else "Task updated")
    except TaskMutationConflict:
        conn.rollback()
        raise
    finally:
        conn.close()


def _postgres_task_audit(principal, limit, before_id, task_id):
    from devcore_engine.services.task_audit import (
        InvalidAuditCursor, TaskAuditUnavailable, QUALIFIED_ACTIONS, audit_identifier,
        safe_identifier, MAX_AUDIT_BYTES,
    )
    from devcore_engine.services.project_context import encode_context
    if not 1 <= limit <= 100:
        raise ValueError("Invalid audit limit")
    if before_id is not None:
        try:
            audit_identifier(before_id)
        except (ValueError, TypeError, AttributeError) as exc:
            raise InvalidAuditCursor("Invalid scoped audit cursor") from exc
    if task_id is not None:
        safe_identifier(task_id)
    conn = _postgres_connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT set_config('app.current_project_id', %s, false)", (principal.project_id,))
        where = "a.project_id=%s AND a.entity_type='task' AND a.action IN ('task.complete','task.delete','task.pause','task.resume')"
        values = [principal.project_id]
        if task_id is not None:
            where += " AND a.entity_id=%s"
            values.append(task_id)
        if before_id is not None:
            cur.execute("SELECT created_at,id FROM audit_log WHERE " + where.replace("a.", "") + " AND id=%s", (*values, before_id))
            boundary = cur.fetchone()
            if boundary is None:
                raise InvalidAuditCursor("Invalid scoped audit cursor")
            where += " AND (a.created_at,a.id)<(%s,%s)"
            values.extend(boundary)
        cur.execute("SELECT a.id,a.entity_id,a.actor,a.action,a.created_at,a.details FROM audit_log a WHERE " + where + " ORDER BY a.created_at DESC,a.id DESC LIMIT %s", (*values, limit + 1))
        rows = cur.fetchall()
        result = {"success": True, "project": principal.project_id, "events": [],
                  "supported_actions": list(QUALIFIED_ACTIONS), "next_before_id": None,
                  "has_more": len(rows) > limit}
        for row in rows[:limit]:
            details = row[5] if isinstance(row[5], dict) else json.loads(row[5])
            if details.get("schema_version") != 1 or not all(
                isinstance(details.get(state), dict) and details[state].get("status") in
                {"todo", "in_progress", "paused", "done", "blocked", "deleted"}
                and type(details[state].get("version")) is int for state in ("before", "after")):
                raise TaskAuditUnavailable("Qualified task audit unavailable")
            event = {"id": audit_identifier(row[0]), "project": principal.project_id,
                     "task_id": safe_identifier(row[1]), "actor": row[2], "action": row[3],
                     "created_at": row[4].strftime("%Y-%m-%d %H:%M:%S"),
                     "before": details["before"], "after": details["after"]}
            result["events"].append(event)
            result["next_before_id"] = event["id"] if result["has_more"] else None
            if len((encode_context(result) + "\n").encode("utf-8")) > MAX_AUDIT_BYTES:
                result["events"].pop()
                if not result["events"]:
                    raise TaskAuditUnavailable("Qualified task audit unavailable")
                result["has_more"] = True
                result["next_before_id"] = result["events"][-1]["id"]
                break
        return result
    finally:
        conn.close()

# FastAPI imports and Application Setup
from fastapi import FastAPI, Request, HTTPException, Response, Query
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import uvicorn
import shutil
try:
    import httpx
except ImportError:
    httpx = None

app = FastAPI(title="DEV_CORE Dashboard API Server", version="10.2.0")

# CORS setup matching get_allowed_origins()
allowed_origins = get_allowed_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def individual_project_access(request: Request, call_next):
    """Opt-in qualification profile: scoped tasks and registered project context.

    Global HTML/projections/SSE/search remain closed until their ACL adapters
    and browser sessions are qualified. Legacy mode is preserved for cutover.
    """
    if DASHBOARD_AUTH_PROFILE != "individual":
        return await call_next(request)
    path, method = request.url.path, request.method
    # Let the CORS middleware answer preflights before the project-route
    # allowlist. The actual mutation still passes this guard.
    if method == "OPTIONS":
        return await call_next(request)
    if path == "/api/status" and method == "GET":
        return await call_next(request)
    if path == "/api/auth/session" and method in {"GET", "POST", "DELETE"}:
        return await call_next(request)
    if path in {"/project", "/project.js"} and method == "GET":
        return await call_next(request)
    supported = {("GET", "/api/dashboard/tasks"), ("GET", "/api/project/context"), ("GET", "/api/project/task-audit"),
                 ("POST", "/api/done"), ("DELETE", "/api/delete"),
                 ("POST", "/api/pause"), ("POST", "/api/resume")}
    if (method, path) not in supported:
        return JSONResponse(status_code=403, content={"detail": {"code": "individual_route_unavailable", "message": "Route not qualified for individual access"}})
    authorization = request.headers.get("Authorization", "")
    browser_secret = request.cookies.get("devcore_session") if not authorization else None
    if not authorization.startswith("Bearer ") and not browser_secret:
        return JSONResponse(status_code=401, content={"detail": {"code": "individual_credential_required", "message": "Individual credential required"}}, headers={"WWW-Authenticate": "Bearer"})
    # Browser task access requires the scoped cookie and session CSRF checks.
    if not browser_secret and request.headers.get("Origin"):
        return JSONResponse(status_code=403, content={"detail": {"code": "browser_session_unavailable", "message": "Browser sessions not qualified"}})
    try:
        if method == "GET":
            project = validate_safe_id(request.query_params.get("project"), "project")
        else:
            if is_request_too_large(request.headers):
                raise RequestTooLarge()
            body = await request.body()
            if len(body) > get_max_request_body_bytes():
                raise RequestTooLarge()
            data = json.loads(body)
            if not isinstance(data, dict):
                raise ValueError("JSON object required")
            project = validate_safe_id(data.get("project"), "project")
            version = data.get("expected_version")
            if type(version) is not int or version < 1:
                raise ValueError("Positive expected_version required")
    except RequestTooLarge:
        return JSONResponse(status_code=413, content={"detail": "Request body too large"})
    except (ValueError, TypeError, UnicodeError):
        return JSONResponse(status_code=400, content={"detail": {"code": "invalid_arguments", "message": "Explicit project and valid task arguments required"}})
    engine_source = str(Path(__file__).resolve().parent.parent)
    if engine_source not in sys.path:
        sys.path.insert(0, engine_source)
    from devcore_engine.security.identity import (
        SqliteIdentityProvider, PostgresIdentityProvider, AuthenticationRequired, ProjectAccessDenied,
        IdentityUnavailable, READ, WRITE, CONTEXT_READ, AUDIT_READ,
    )
    identity_path = os.environ.get("DEVCORE_IDENTITY_STORE", str(get_local_path("Security", "individual_identity.db")))
    action = ({"/api/project/context": CONTEXT_READ, "/api/project/task-audit": AUDIT_READ}.get(path, READ)
              if method == "GET" else WRITE)
    try:
        if POSTGRES_DASHBOARD and browser_secret and method == "GET" and path == "/api/dashboard/tasks":
            try:
                limit = int(request.query_params.get("limit", "20"))
                offset = int(request.query_params.get("offset", "0"))
            except (TypeError, ValueError):
                return JSONResponse(status_code=422, content={"detail": "Invalid pagination"})
            if not 1 <= limit <= 100 or offset < 0:
                return JSONResponse(status_code=400, content={"detail": "Invalid pagination"})
            origin = trusted_session_origin(request)
            tasks = await asyncio.to_thread(
                _postgres_scoped_browser_tasks, browser_secret, project, origin, limit, offset,
            )
            from fastapi.encoders import jsonable_encoder
            return JSONResponse(content=jsonable_encoder(tasks), headers={"Cache-Control": "no-store"})
        provider = PostgresIdentityProvider(POSTGRES_DSN) if POSTGRES_DASHBOARD else SqliteIdentityProvider(identity_path)
        if browser_secret:
            if POSTGRES_DASHBOARD:
                from devcore_engine.security.postgres_browser_sessions import authorize_session
            else:
                from devcore_engine.security.browser_sessions import authorize_session
            origin = trusted_session_origin(request, require_origin=method != "GET")
            session = await asyncio.to_thread(
                authorize_session, POSTGRES_DSN if POSTGRES_DASHBOARD else identity_path, browser_secret, project,
                action, origin,
                csrf=request.headers.get(CSRF_HEADER), mutate=method != "GET",
            )
            principal = session.principal
            request.state.browser_session = session
        else:
            principal = await asyncio.to_thread(provider.authorize, authorization, project, action)
    except AuthenticationRequired:
        return JSONResponse(status_code=401, content={"detail": {"code": "invalid_individual_credential", "message": "Invalid or expired individual credential"}}, headers={"WWW-Authenticate": "Bearer"})
    except ProjectAccessDenied:
        return JSONResponse(status_code=403, content={"detail": {"code": "project_access_denied", "message": "Project action denied"}})
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    except (IdentityUnavailable, ValueError, sqlite3.Error):
        return JSONResponse(status_code=503, content={"detail": {"code": "identity_unavailable", "message": "Individual identity store unavailable"}})
    request.state.principal = principal
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    return response


class IndividualBodyLimitMiddleware:
    """Bound received bytes before Starlette collects or parses the JSON body."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if DASHBOARD_AUTH_PROFILE != "individual" or scope["type"] != "http" or scope["method"] not in {"POST", "DELETE"}:
            return await self.app(scope, receive, send)
        limit, received = get_max_request_body_bytes(), 0
        async def bounded_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    raise RequestTooLarge()
            return message
        return await self.app(scope, bounded_receive, send)


app.add_middleware(IndividualBodyLimitMiddleware)

def check_auth(request: Request) -> bool:
    if DASHBOARD_AUTH_PROFILE == "individual":
        return getattr(request.state, "principal", None) is not None
    path = request.url.path
    if not requires_authentication(path):
        return True
    
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return False
    token = auth_header[7:]
    return validate_api_token(token)

def check_csrf(request: Request, method: str) -> bool:
    if DASHBOARD_AUTH_PROFILE == "individual":
        return getattr(request.state, "principal", None) is not None and (
            getattr(request.state, "browser_session", None) is not None or not request.headers.get("Origin")
        )
    path = request.url.path
    if not requires_csrf(method, path):
        return True
    
    csrf_header = request.headers.get("X-CSRF-Token")
    if not csrf_header:
        return False
    return validate_csrf_token(csrf_header)


def trusted_session_origin(request, *, require_origin=False):
    origin = f"{request.url.scheme}://{request.url.netloc}"
    supplied = request.headers.get("Origin")
    if (require_origin and not supplied) or (supplied and supplied != origin) or not is_origin_allowed(origin):
        raise HTTPException(403, detail="Invalid session origin")
    if request.url.scheme != "https" and request.url.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise HTTPException(403, detail="Session requires HTTPS or loopback")
    return origin


@app.api_route("/api/auth/session", methods=["GET", "POST", "DELETE"])
async def browser_session_route(request: Request):
    if DASHBOARD_AUTH_PROFILE != "individual":
        raise HTTPException(403, detail="Individual profile required")
    engine_source = str(Path(__file__).resolve().parent.parent)
    if engine_source not in sys.path:
        sys.path.insert(0, engine_source)
    from devcore_engine.security.identity import AuthenticationRequired, ProjectAccessDenied, IdentityUnavailable
    from devcore_engine.security.browser_sessions import (
        COOKIE, create_session, csrf_for_session, session_info, authorize_session, revoke_session,
    )
    if POSTGRES_DASHBOARD:
        from devcore_engine.security.postgres_browser_sessions import (
            create_session as pg_create_session, session_info as pg_session_info,
            authorize_session as pg_authorize_session, revoke_session as pg_revoke_session,
        )
        from devcore_engine.security.postgres_password_sessions import create_password_session as pg_password_session
    origin = trusted_session_origin(request, require_origin=request.method != "GET")
    identity_path = os.environ.get("DEVCORE_IDENTITY_STORE", str(get_local_path("Security", "individual_identity.db")))
    secret = request.cookies.get(COOKIE)
    try:
        if request.method == "POST":
            if is_request_too_large(request.headers):
                raise RequestTooLarge()
            data = json.loads(await request.body())
            if not isinstance(data, dict):
                raise ValueError("JSON object required")
            project = validate_safe_id(data.get("project"), "project")
            authorization = request.headers.get("Authorization")
            if authorization:
                if "user_id" in data or "password" in data:
                    raise ValueError("Mixed authentication methods")
                session, secret = await asyncio.to_thread(
                    pg_create_session if POSTGRES_DASHBOARD else create_session,
                    POSTGRES_DSN if POSTGRES_DASHBOARD else identity_path,
                    authorization, project, origin, previous=secret,
                )
            else:
                from devcore_engine.security.passwords import create_password_session, LoginBusy
                user_id = validate_safe_id(data.get("user_id"), "user")
                try:
                    session, secret = await asyncio.to_thread(
                        pg_password_session if POSTGRES_DASHBOARD else create_password_session,
                        POSTGRES_DSN if POSTGRES_DASHBOARD else identity_path,
                        user_id, data.get("password"), project, origin, previous=secret,
                    )
                except LoginBusy:
                    raise HTTPException(429, detail="Login capacity reached", headers={"Retry-After": "1"})
        else:
            session = await asyncio.to_thread(
                pg_session_info if POSTGRES_DASHBOARD else session_info,
                POSTGRES_DSN if POSTGRES_DASHBOARD else identity_path, secret, origin)
            if request.method == "DELETE":
                await asyncio.to_thread(
                    pg_authorize_session if POSTGRES_DASHBOARD else authorize_session,
                    POSTGRES_DSN if POSTGRES_DASHBOARD else identity_path,
                    secret, session.project_id, "task.read", origin,
                    csrf=request.headers.get(CSRF_HEADER), mutate=True)
                await asyncio.to_thread(
                    pg_revoke_session if POSTGRES_DASHBOARD else revoke_session,
                    POSTGRES_DSN if POSTGRES_DASHBOARD else identity_path, secret)
        content = {"user_id": session.principal.user_id, "project": session.project_id,
                   "expires_at": session.expires_at, "csrf_token": csrf_for_session(secret),
                   "actions": list(session.actions)}
        response = JSONResponse(content={"status": "logged_out"} if request.method == "DELETE" else content,
                                headers={"Cache-Control": "no-store"})
        if request.method == "POST":
            response.set_cookie(COOKIE, secret, max_age=max(0, int(session.expires_at - time.time())),
                                httponly=True, secure=request.url.scheme == "https", samesite="strict", path="/")
        elif request.method == "DELETE":
            response.delete_cookie(COOKIE, path="/", httponly=True, secure=request.url.scheme == "https", samesite="strict")
        return response
    except RequestTooLarge:
        raise HTTPException(413, detail="Request body too large")
    except AuthenticationRequired:
        raise HTTPException(401, detail="Invalid credentials or session")
    except ProjectAccessDenied:
        raise HTTPException(403, detail="Session project action denied")
    except (IdentityUnavailable, sqlite3.Error):
        raise HTTPException(503, detail="Browser session store unavailable")
    except (ValueError, TypeError, UnicodeError):
        raise HTTPException(400, detail="Invalid session arguments")


@app.get("/project")
@app.get("/project.js")
def individual_project_page(request: Request):
    """Public shell only; project data is fetched through session-checked APIs."""
    if DASHBOARD_AUTH_PROFILE != "individual":
        raise HTTPException(403, detail="Individual profile required")
    from fastapi.responses import Response
    filename = "project_tasks.js" if request.url.path == "/project.js" else "project.html"
    path = Path(__file__).resolve().parent.parent / "Dashboard" / filename
    return Response(path.read_text(encoding="utf-8"),
                    media_type="text/javascript" if filename.endswith(".js") else "text/html",
                    headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
                             "Referrer-Policy": "no-referrer",
                             "Content-Security-Policy": "default-src 'none'; script-src 'self'; style-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"})

def get_dashboard_input_signature():
    """Metadata-only probe of local SQL/WAL and the historical event file.

    No active-project lookup, subprocess, global preference or JSON task source.
    Missing/replaced/truncated files change the signature; other I/O fails.
    """
    import stat
    signature = []
    for path in (get_local_path("devcore.db"), get_local_path("devcore.db-wal"),
                 get_local_path("Bus", "events.jsonl")):
        try:
            info = path.stat()
        except FileNotFoundError:
            signature.append((str(path), None))
            continue
        if not stat.S_ISREG(info.st_mode):
            raise RuntimeError("Dashboard watched input is not a regular file")
        signature.append((str(path), info.st_mtime_ns, info.st_size, info.st_ino))
    return tuple(signature)


_sse_inputs = InputWatcher()
_sse_publications = InputWatcher()
_sse_refresh = RefreshCoordinator()
_sse_errors = SseErrorReporter()
_sse_slots = StreamSlots(limit=32)


def get_dashboard_snapshot_cursor():
    with pin_snapshot(get_local_path("Dashboard")) as snapshot:
        if snapshot is None:
            return None
        return "snapshot:" + snapshot.manifest["generation"]


async def event_generator(request: Request):
    previous = parse_snapshot_cursor(getattr(request, "headers", {}).get("last-event-id"))
    # Establish the input baseline before reading/announcing the generation.
    # Changes while the handshake is being consumed must remain observable.
    last_ts = await _sse_inputs.revision(get_dashboard_input_signature)
    last_publication_revision, _ = await _sse_publications.snapshot(get_dashboard_snapshot_cursor)
    current_cursor = await asyncio.to_thread(get_dashboard_snapshot_cursor)
    needs_snapshot = previous is not None and previous != current_cursor
    # Do not advance the browser cursor before the resynchronization frame.
    yield event_frame("message", "Connected", None if needs_snapshot else current_cursor)
    if needs_snapshot:
        yield event_frame("dashboard.delta", {
            "schema_version": 1, "generated_at": datetime.now().isoformat(),
            "has_changes": True, "changed_keys": ["all"],
            "snapshot_required": True, "recovery": "reload_snapshot",
            "cursor": current_cursor, "read_model": {},
        }, current_cursor)

    last_heartbeat = asyncio.get_event_loop().time()
    
    while True:
        if await request.is_disconnected():
            break
        
        await asyncio.sleep(1.0)
        
        try:
            current_ts = await _sse_inputs.revision(get_dashboard_input_signature)
            if current_ts > last_ts:
                # Regenerate dashboard to refresh server cache
                try:
                    await _sse_refresh.refresh(current_ts, refresh_dashboard_payload_cache)
                except Exception as e:
                    _sse_errors.report('cache', e)
                    continue  # Do not announce a failed publication.
                last_ts = current_ts
                
                # Emit delta with has_changes=True to trigger client refresh
                delta = {
                    "schema_version": 1,
                    "generated_at": datetime.now().isoformat(),
                    "has_changes": True,
                    "changed_keys": ["all"],
                    "fingerprint": f"ts_{current_ts}",
                    "read_model": {},
                }
                current_cursor = await asyncio.to_thread(get_dashboard_snapshot_cursor)
                delta["cursor"] = current_cursor
                yield event_frame("dashboard.delta", delta, current_cursor)
                last_heartbeat = asyncio.get_event_loop().time()
                
            else:
                # Another writer can publish without changing watched inputs.
                # Notify from the committed generation without regenerating it.
                publication_revision, published_cursor = await _sse_publications.snapshot(get_dashboard_snapshot_cursor)
                publication_changed = publication_revision > last_publication_revision
                last_publication_revision = publication_revision
                if publication_changed and published_cursor != current_cursor:
                    current_cursor = published_cursor
                    yield event_frame("dashboard.delta", {
                        "schema_version": 1, "generated_at": datetime.now().isoformat(),
                        "has_changes": True, "changed_keys": ["all"],
                        "snapshot_required": True, "recovery": "reload_snapshot",
                        "cursor": current_cursor, "read_model": {},
                    }, current_cursor)
                    last_heartbeat = asyncio.get_event_loop().time()
                elif asyncio.get_event_loop().time() - last_heartbeat >= DASHBOARD_SSE_HEARTBEAT_SECONDS:
                    yield ": heartbeat\n\n"
                    last_heartbeat = asyncio.get_event_loop().time()
        except Exception as e:
            _sse_errors.report('loop', e)

def read_dashboard_html(name):
    with pin_snapshot(get_local_path("Dashboard")) as snapshot:
        if snapshot is not None:
            return read_snapshot_artifact(snapshot, name)
    path = get_platform_path("Dashboard", name)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"{name} not found")
    return path.read_text(encoding="utf-8")


@app.get("/")
@app.get("/index.html", response_class=HTMLResponse)
async def serve_index(request: Request):
    html_content = await asyncio.to_thread(read_dashboard_html, "index.html")
    return HTMLResponse(content=inject_auth_fetch(html_content))

@app.get("/index_terminal.html", response_class=HTMLResponse)
async def serve_terminal_index(request: Request):
    html_content = await asyncio.to_thread(read_dashboard_html, "index_terminal.html")
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
        payload = await asyncio.to_thread(build_dashboard_payload)
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

@app.get("/api/project/context")
def get_project_context_route(request: Request, project: str,
                              budget_bytes: int | None = Query(default=None, ge=256, le=65536),
                              query: str = Query(default="", max_length=4096)):
    """Return the exact measured JSON line after individual project admission."""
    if DASHBOARD_AUTH_PROFILE != "individual":
        raise HTTPException(status_code=403, detail="Individual context admission required")
    from devcore_engine.security.identity import CONTEXT_READ
    from devcore_engine.services.project_context import ContextBudgetExceeded, encode_context
    from devcore_engine.services.registered_project_context import (
        ProjectContextUnavailable, load_registered_project_context,
    )
    principal = getattr(request.state, "principal", None)
    if (principal is None
            or principal.project_id != project or principal.action != CONTEXT_READ):
        raise HTTPException(status_code=403, detail="Individual context admission required")
    budget = HTTP_CONTEXT_MAX_BYTES if budget_bytes is None else budget_bytes
    if budget > HTTP_CONTEXT_MAX_BYTES:
        raise HTTPException(status_code=422, detail="Requested budget exceeds server context limit")
    try:
        if POSTGRES_DASHBOARD:
            from devcore_engine.services.project_context import load_project_context
            conn = _postgres_connect()
            try:
                cur = conn.cursor()
                cur.execute("SELECT set_config('app.current_project_id', %s, false)", (project,))
                cur.execute("SELECT root_path FROM projects WHERE id=%s AND status='active'", (project,))
                row = cur.fetchone()
            finally:
                conn.close()
            if not row:
                raise ProjectContextUnavailable("Registered project context unavailable")
            root = Path(row[0])
            if not root.is_absolute() or not root.is_dir():
                raise ProjectContextUnavailable("Registered project context unavailable")
            root = root.resolve()
            directory = (root / "docs" / "project-context").resolve()
            if not directory.is_relative_to(root) or not directory.is_dir():
                raise ProjectContextUnavailable("Registered project context unavailable")
            result = load_project_context(directory, project, budget_bytes=budget, query=query)
        else:
            result = load_registered_project_context(get_local_path("devcore.db"), principal,
                                                     budget_bytes=budget, query=query)
    except ContextBudgetExceeded as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except ProjectContextUnavailable as exc:
        raise HTTPException(status_code=503, detail="Registered project context unavailable") from exc
    return Response(content=(encode_context(result) + "\n").encode("utf-8"),
                    media_type="application/json", headers={"Cache-Control": "no-store"})


@app.get("/api/project/task-audit")
async def task_audit_route(request: Request, project: str):
    from devcore_engine.security.identity import AUDIT_READ
    from devcore_engine.services.project_context import encode_context
    from devcore_engine.services.task_audit import InvalidAuditCursor, TaskAuditUnavailable, read_task_audit
    principal = getattr(request.state, "principal", None)
    if (DASHBOARD_AUTH_PROFILE != "individual" or principal is None
            or principal.project_id != project or principal.action != AUDIT_READ):
        raise HTTPException(status_code=403, detail="Individual task audit admission required")
    try:
        if set(request.query_params) - {"project", "limit", "before_id", "task_id"}:
            raise ValueError("Unsupported audit arguments")
        limit_text = request.query_params.get("limit", "20")
        if len(limit_text) > 3 or not limit_text.isascii() or not limit_text.isdigit():
            raise ValueError("Invalid limit")
        if POSTGRES_DASHBOARD:
            result = await asyncio.to_thread(_postgres_task_audit, principal,
                int(limit_text), request.query_params.get("before_id"), request.query_params.get("task_id"))
        else:
            result = await asyncio.to_thread(read_task_audit, get_local_path("devcore.db"), principal,
                limit=int(limit_text), before_id=request.query_params.get("before_id"), task_id=request.query_params.get("task_id"))
    except (InvalidAuditCursor, ValueError):
        raise HTTPException(status_code=400, detail={"code": "invalid_audit_arguments", "message": "Invalid scoped audit arguments"})
    except TaskAuditUnavailable:
        raise HTTPException(status_code=503, detail={"code": "task_audit_unavailable", "message": "Qualified task audit unavailable"})
    return Response(content=(encode_context(result) + "\n").encode("utf-8"), media_type="application/json",
                    headers={"Cache-Control": "no-store"})


@app.get("/api/dashboard/tasks")
def get_dashboard_tasks_route(request: Request, project: str, limit: int = 20, offset: int = 0):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        project = validate_safe_id(project, "project")
        if not 1 <= limit <= 100 or offset < 0:
            raise ValueError("Invalid pagination")
        if POSTGRES_DASHBOARD:
            from urllib.parse import urlparse
            import pg8000.dbapi
            parsed = urlparse(POSTGRES_DSN.replace("postgresql+pg8000://", "postgresql://", 1))
            conn = pg8000.dbapi.connect(user=parsed.username, password=parsed.password,
                host=parsed.hostname or "127.0.0.1", port=parsed.port or 5432,
                database=(parsed.path or "/postgres").lstrip("/"))
            try:
                cur = conn.cursor()
                cur.execute("SELECT set_config('app.current_project_id', %s, false)", (project,))
                cur.execute("SELECT legacy_id, project_id, title, status, mode, steps_total, steps_done, started_at, completed_at, version FROM tasks WHERE project_id = %s AND status <> 'deleted' ORDER BY created_at, task_number LIMIT %s OFFSET %s", (project, limit, offset))
                rows = cur.fetchall()
            finally:
                conn.close()
            return [{"id": r[0], "project": r[1], "title": r[2], "status": r[3],
                     "mode": r[4], "steps_total": r[5], "steps_done": r[6],
                     "started_at": r[7], "completed_at": r[8], "version": r[9]} for r in rows]
        db_path = get_local_path("devcore.db")
        if not db_path.is_file():
            raise FileNotFoundError(f"Task database not found: {db_path}")
        import sqlite3
        with closing(sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True, timeout=30.0)) as conn:
            columns = {row[1] for row in conn.execute("PRAGMA table_info(tasks)")}
            version_column = "version" if "version" in columns else "NULL AS version"
            rows = conn.execute(
                f"SELECT id, project_id, title, status, mode, steps_total, steps_done, started_at, completed_at, {version_column} "
                "FROM tasks WHERE project_id = ? AND status <> 'deleted' "
                "ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
                (project, limit, offset),
            ).fetchall()
        tasks = []
        for r in rows:
            tasks.append({
                "id": r[0], "project": r[1], "title": r[2], "status": r[3],
                "mode": r[4], "steps_total": r[5], "steps_done": r[6],
                "started_at": r[7], "completed_at": r[8], "version": r[9]
            })
        return tasks
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def task_mutation_arguments(request: Request):
    try:
        data = await request.json()
        if not isinstance(data, dict):
            raise ValueError("Expected a JSON object")
        project = validate_safe_id(data.get("project", ""), "project")
        task_id = validate_safe_id(data.get("id", ""), "task id")
        version = data.get("expected_version")
        if version is not None and (type(version) is not int or version < 1):
            raise ValueError("expected_version must be a positive integer")
        return project, task_id, version
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def task_actor_context(request: Request, project: str):
    """Use only the principal admitted by middleware, never JSON actor fields."""
    if DASHBOARD_AUTH_PROFILE != "individual":
        return None
    from devcore_engine.context import RequestContext
    from devcore_engine.security.identity import WRITE
    principal = getattr(request.state, "principal", None)
    if principal is None or principal.project_id != project or principal.action != WRITE:
        raise HTTPException(status_code=403, detail="Missing project mutation principal")
    session = getattr(request.state, "browser_session", None)
    return RequestContext(project_id=project, user_id=principal.user_id,
                          session_id=session.session_id if session else None)



@app.post("/api/pause")
@app.post("/api/resume")
async def post_task_transition_route(request: Request):
    # New routes require individual admission, including when the legacy profile is active.
    if DASHBOARD_AUTH_PROFILE != "individual":
        raise HTTPException(403, detail={"code": "individual_route_required"})
    if not check_auth(request):
        raise HTTPException(401, detail="Unauthorized")
    if not check_csrf(request, "POST"):
        raise HTTPException(403, detail="Invalid CSRF Token")
    project, task_id, version = await task_mutation_arguments(request)
    try:
        success = await asyncio.to_thread(
            transition_individual_task, project, task_id, version,
            operation="pause" if request.url.path == "/api/pause" else "resume",
            context=task_actor_context(request, project))
    except TaskMutationConflict as exc:
        raise HTTPException(409, detail={"code": exc.code, "message": str(exc)}) from exc
    except (sqlite3.Error, OSError):
        raise HTTPException(500, detail={"code": "task_transition_unavailable"}) from None
    if not success:
        raise HTTPException(404, detail={"code": "task_not_found"})
    return {"status": "success", "message": "Task transition completed"}

@app.post("/api/done")
async def post_done_route(request: Request):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not check_csrf(request, "POST"):
        raise HTTPException(status_code=403, detail="Invalid CSRF Token")
    
    project, task_id, version = await task_mutation_arguments(request)
    try:
        success, msg = await asyncio.to_thread(complete_task, project, task_id, version,
                                              context=task_actor_context(request, project))
    except TaskMutationConflict as exc:
        raise HTTPException(status_code=409, detail={"code": exc.code, "message": str(exc)}) from exc
    if success:
        return {"status": "success", "message": msg}
    else:
        raise HTTPException(status_code=404 if "not found in project" in msg else 500, detail=msg)

@app.delete("/api/delete")
async def delete_route(request: Request):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not check_csrf(request, "DELETE"):
        raise HTTPException(status_code=403, detail="Invalid CSRF Token")
    
    project, task_id, version = await task_mutation_arguments(request)
    try:
        success, msg = await asyncio.to_thread(delete_task, project, task_id, version,
                                              context=task_actor_context(request, project))
    except TaskMutationConflict as exc:
        raise HTTPException(status_code=409, detail={"code": exc.code, "message": str(exc)}) from exc
    if success:
        return {"status": "success", "message": msg}
    else:
        if "not found in project" in msg:
            raise HTTPException(status_code=404, detail=msg)
        if " is required by " in msg:
            raise HTTPException(status_code=409, detail=msg)
        raise HTTPException(status_code=500, detail=msg)

@app.post("/api/refresh")
async def post_refresh_route(request: Request):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not check_csrf(request, "POST"):
        raise HTTPException(status_code=403, detail="Invalid CSRF Token")
    
    try:
        payload = await asyncio.to_thread(refresh_dashboard_payload_cache)
        return JSONResponse(content=payload)
    except subprocess.TimeoutExpired as te:
        print(f"[DashboardAPI] Timeout calling gen_dashboard.ps1: {te}")
        raise HTTPException(status_code=504, detail=f"Dashboard regeneration timed out after {DASHBOARD_COMMAND_TIMEOUT_SEC:.0f}s")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard/stream")
async def dashboard_stream_route(request: Request):
    try:
        parse_snapshot_cursor(request.headers.get("last-event-id"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Last-Event-ID snapshot cursor")
    try:
        return AdmittedStreamingResponse(event_generator(request), _sse_slots, media_type="text/event-stream")
    except StreamCapacityExceeded:
        raise HTTPException(status_code=503, detail="SSE connection capacity reached", headers={"Retry-After": "5"})

def memory_search_arguments(query, collections, limit):
    allowed = {'decisions', 'lessons', 'patterns', 'codebase'}
    if not isinstance(query, str) or not query.strip() or len(query.encode('utf-8')) > 8192:
        raise HTTPException(status_code=400, detail='Query must be nonempty UTF-8 text <=8192 bytes')
    if type(limit) is not int or not 1 <= limit <= 20:
        raise HTTPException(status_code=400, detail='Memory limit must be 1..20')
    collections = ['decisions', 'lessons', 'patterns', 'codebase'] if collections is None else collections
    if not isinstance(collections, list) or not 1 <= len(collections) <= 4 or any(type(col) is not str or col not in allowed for col in collections) or len(set(collections)) != len(collections):
        raise HTTPException(status_code=400, detail='Invalid memory collections')
    return collections


def memory_embedding_service():
    engine_source = str(Path(__file__).resolve().parents[1])
    if engine_source not in sys.path:
        sys.path.insert(0, engine_source)
    from devcore_engine.services.embedding import EmbeddingService
    return EmbeddingService


async def search_qdrant_collection_async(client, collection: str, query: str, limit: int = 5,
                                         qdrant_url: str = 'http://127.0.0.1:6333', *, vector=None) -> dict:
    memory_search_arguments(query, [collection], limit)
    if client is None or vector is None:
        return {'collection': collection, 'hits': [], 'status': 'degraded', 'reason': 'embedding_unavailable'}
    memory_embedding_service().validate_vector(vector, context='memory_query')
    url = f'{qdrant_url}/collections/{collection}/points/search'
    payload = {'vector': vector, 'limit': limit, 'with_payload': True}
    try:
        async with client.stream('POST', url, json=payload, timeout=3.0,
            headers={'Accept-Encoding': 'identity'}, follow_redirects=False) as response:
            if response.status_code != 200 or response.headers.get('content-encoding', 'identity').lower() != 'identity':
                raise ValueError('Memory backend unavailable')
            raw = bytearray()
            chunks = 0
            async for chunk in response.aiter_raw():
                if len(raw) + len(chunk) > 1024 * 1024:
                    raise ValueError('Memory response exceeds capacity')
                raw.extend(chunk)
                chunks += 1
                if chunks % 64 == 0:
                    await asyncio.sleep(0)
        from devcore_engine.services.memory_results import decode_memory_hits
        hits = await decode_memory_hits(raw, limit)
        return {'collection': collection, 'hits': hits, 'status': 'ok'}
    except Exception:
        return {'collection': collection, 'hits': [], 'status': 'degraded', 'reason': 'memory_backend_unavailable'}


async def search_memory_pipeline_async(query: str, collections: list = None, limit: int = 5, *, client=None) -> dict:
    collections = memory_search_arguments(query, collections, limit)
    result = {'query': query, 'total_hits': 0, 'collections': {},
              'timestamp': datetime.now().isoformat(), 'search_mode': 'unavailable', 'degraded': True}
    async def run(owned_client):
        service = memory_embedding_service()
        vector = await service.embed_query(owned_client, query)
        results = await asyncio.gather(*[search_qdrant_collection_async(owned_client, col, query, limit,
            vector=vector) for col in collections])
        result['embedding'] = {'model': service.QUERY_MODEL, 'dimensions': service.DIMENSIONS,
                               'version': service.CONTRACT_VERSION}
        result['search_mode'] = 'vector'
        result['degraded'] = any(item['status'] != 'ok' for item in results)
        for item in results:
            result['collections'][item['collection']] = {key: value for key, value in item.items() if key != 'collection'}
            result['collections'][item['collection']]['count'] = len(item['hits'])
            result['total_hits'] += len(item['hits'])
    try:
        async with asyncio.timeout(5.0):
            if client is not None:
                await run(client)
            elif httpx is not None:
                async with httpx.AsyncClient(trust_env=False, follow_redirects=False) as owned_client:
                    await run(owned_client)
            else:
                raise ValueError('HTTP client unavailable')
    except Exception:
        result['degraded'] = True
        result['search_mode'] = 'unavailable'
        result['total_hits'] = 0
        result.pop('embedding', None)
        result['collections'] = {col: {'status': 'degraded', 'reason': 'embedding_or_deadline_unavailable',
            'count': 0, 'hits': []} for col in collections}
    return result

@app.get("/api/memory/search")
async def get_memory_search_route(request: Request, q: str = "", limit: int = 5):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    results = await search_memory_pipeline_async(query=q, limit=limit)
    return results

@app.post("/api/memory/search")
async def post_memory_search_route(request: Request):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    data = await request.json()
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="Expected memory query object")
    query = data.get("query", "")
    collections = data.get("collections")
    limit = data.get("limit", 5)
    results = await search_memory_pipeline_async(query=query, collections=collections, limit=limit)
    return results

def main():
    if "--rotate-token" in sys.argv:
        if DASHBOARD_AUTH_PROFILE == "individual":
            raise ValueError("Shared token rotation is disabled in individual profile")
        token = rotate_api_token()
        print(token)
        return

    if DASHBOARD_AUTH_PROFILE == "legacy":
        ensure_api_token()
        ensure_csrf_token()
    
    bind_host = get_bind_host()
    print(f"DEV_CORE Dashboard API Server listening on {bind_host}:{PORT}...")
    try:
        from service_runtime import run_managed
        run_managed(app, host=bind_host, port=PORT, service='dashboard', log_level="warning")
    except KeyboardInterrupt:
        print("\nShutting down API Server.")
        sys.exit(0)

if __name__ == "__main__":
    main()
