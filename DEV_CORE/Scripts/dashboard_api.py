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
PUBLIC_PATHS = {"/", "/index.html", "/api/status"}
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
        text=True,
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
    cached = read_cached_dashboard_payload()
    if cached:
        return cached
    return build_fallback_dashboard_payload()


def refresh_dashboard_payload_cache():
    dashboard_script = get_platform_path("Scripts", "gen_dashboard.ps1")
    cmd = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(dashboard_script),
        "-Json",
        "-SkipTokenRefresh",
    ]
    print(f"[DashboardAPI] Running gen_dashboard.ps1 -Json (timeout={DASHBOARD_COMMAND_TIMEOUT_SEC:.0f}s)...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=DASHBOARD_COMMAND_TIMEOUT_SEC)
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

class DashboardAPIHandler(http.server.BaseHTTPRequestHandler):
    def end_headers(self):
        origin = self.headers.get("Origin")
        if origin and is_origin_allowed(origin):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type, X-CSRF-Token, X-Requested-With')
        super().end_headers()

    def do_OPTIONS(self):
        try:
            origin = self.headers.get("Origin")
            if origin and not is_origin_allowed(origin):
                self.send_response(403)
                self.end_headers()
                return
            self.send_response(204)
            self.end_headers()
        except ConnectionError:
            pass

    def log_message(self, format, *args):
        # Silence standard HTTP logs in the background terminal unless needed
        pass

    def get_settings(self):
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

    def save_settings(self, data):
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

    def do_GET(self):
        try:
            self._handle_get()
        except ConnectionError:
            # Silence tracebacks if the client disconnected prematurely
            pass

    def _handle_get(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)
        if requires_authentication(path) and not is_authorized(self.headers):
            self.send_auth_error_response()
            return

        if path == "/api/settings":
            try:
                settings = self.get_settings()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(settings, indent=4).encode("utf-8"))
            except Exception as e:
                self.send_error_response(str(e))
            return


        if path == "/api/done":
            self.send_method_not_allowed_response("POST")

        elif path == "/api/delete":
            self.send_method_not_allowed_response("DELETE")

        elif path in ["/", "/index.html"]:
            try:
                index_path = get_platform_path("Dashboard", "index.html")
                if index_path.exists():
                    with open(index_path, "r", encoding="utf-8") as f:
                        html_content = inject_auth_fetch(f.read())
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(html_content.encode("utf-8"))
                else:
                    self.send_error_response("index.html not found")
            except ConnectionError:
                pass
            except Exception as e:
                self.send_error_response(str(e))
        elif path == "/api/status":
            self.send_success_response("API Server Active")
        elif path == "/api/dashboard":
            try:
                payload = build_dashboard_payload()
                self.send_cached_json_response(payload)
            except subprocess.TimeoutExpired as te:
                print(f"[DashboardAPI] Timeout calling gen_dashboard.ps1 -Json: {te}")
                self.send_error_response(f"Dashboard payload generation timed out after {DASHBOARD_COMMAND_TIMEOUT_SEC:.0f}s")
            except Exception as e:
                self.send_error_response(str(e))
        elif path == "/api/dashboard/resource":
            resource_name = query.get("name", [""])[0]
            try:
                payload = build_dashboard_resource(
                    resource_name,
                    page=query.get("page", ["1"])[0],
                    page_size=query.get("page_size", [str(DEFAULT_DASHBOARD_RESOURCE_PAGE_SIZE)])[0],
                )
                self.send_cached_json_response(payload)
            except Exception as e:
                self.send_error_response(str(e))
        elif path == "/api/dashboard/stream":
            try:
                self.send_dashboard_stream_response(once=query.get("once", ["0"])[0] == "1")
            except Exception as e:
                self.send_error_response(str(e))
        elif path == "/api/plugin/check":
            plugin_id = query.get("id", [""])[0]
            if not plugin_id:
                self.send_error_response("Missing plugin id")
                return
            try:
                result = run_plugin_check(plugin_id)
                self.send_json_response(result)
            except subprocess.TimeoutExpired as te:
                print(f"[DashboardAPI] Timeout calling dc plugin check: {te}")
                self.send_error_response(f"Plugin check timed out after {DASHBOARD_COMMAND_TIMEOUT_SEC:.0f}s")
            except Exception as e:
                self.send_error_response(str(e))
        elif path == "/api/refresh":
            self.send_method_not_allowed_response("POST")
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        try:
            self._handle_post()
        except ConnectionError:
            pass

    def _handle_post(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if requires_authentication(path) and not is_authorized(self.headers):
            self.send_auth_error_response()
            return
        if requires_csrf("POST", path) and not is_csrf_authorized(self.headers):
            self.send_csrf_error_response()
            return

        if path == "/api/settings":
            try:
                data = self.read_json_body()
                self.save_settings(data)
                self.send_success_response("Settings saved successfully")
            except RequestTooLarge as e:
                self.send_payload_too_large_response(str(e))
            except Exception as e:
                self.send_error_response(str(e))
        elif path == "/api/done":
            try:
                data = self.read_json_body()
                project = data.get("project", "")
                task_id = data.get("id", "")
                if not project or not task_id:
                    self.send_error_response("Missing project or id")
                    return

                success, msg = self.complete_task(project, task_id)
                if success:
                    self.send_success_response(msg)
                else:
                    self.send_error_response(msg)
            except RequestTooLarge as e:
                self.send_payload_too_large_response(str(e))
            except Exception as e:
                self.send_error_response(str(e))
        elif path == "/api/refresh":
            try:
                payload = refresh_dashboard_payload_cache()
                self.send_json_response(payload)
            except subprocess.TimeoutExpired as te:
                print(f"[DashboardAPI] Timeout calling gen_dashboard.ps1: {te}")
                self.send_error_response(f"Dashboard regeneration timed out after {DASHBOARD_COMMAND_TIMEOUT_SEC:.0f}s")
            except Exception as e:
                self.send_error_response(str(e))
        else:
            self.send_response(404)
            self.end_headers()

    def do_DELETE(self):
        try:
            self._handle_delete()
        except ConnectionError:
            pass

    def _handle_delete(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if requires_authentication(path) and not is_authorized(self.headers):
            self.send_auth_error_response()
            return
        if requires_csrf("DELETE", path) and not is_csrf_authorized(self.headers):
            self.send_csrf_error_response()
            return

        if path == "/api/delete":
            try:
                data = self.read_json_body()
                project = data.get("project", "")
                task_id = data.get("id", "")
                if not project or not task_id:
                    self.send_error_response("Missing project or id")
                    return

                success, msg = self.delete_task(project, task_id)
                if success:
                    self.send_success_response(msg)
                else:
                    self.send_error_response(msg)
            except RequestTooLarge as e:
                self.send_payload_too_large_response(str(e))
            except Exception as e:
                self.send_error_response(str(e))
        else:
            self.send_response(404)
            self.end_headers()

    def read_json_body(self):
        if is_request_too_large(self.headers):
            raise RequestTooLarge(f"Request body exceeds {get_max_request_body_bytes()} bytes")
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length <= 0:
            return {}
        post_data = self.rfile.read(content_length)
        return json.loads(post_data.decode('utf-8'))

    def send_success_response(self, message):
        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "message": message}).encode("utf-8"))
        except ConnectionError:
            pass

    def send_json_response(self, payload):
        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        except ConnectionError:
            pass

    def send_cached_json_response(self, payload):
        try:
            response = build_cached_json_response(payload, self.headers)
            self.send_response(response["status"])
            for key, value in response["headers"].items():
                self.send_header(key, value)
            self.end_headers()
            if response["body"]:
                self.wfile.write(response["body"])
        except ConnectionError:
            pass

    def send_dashboard_stream_response(self, once=False):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        previous = load_dashboard_read_model() or {}
        event_id = read_model_fingerprint(previous)
        snapshot = {
            "schema_version": 1,
            "generated_at": datetime.now().isoformat(),
            "fingerprint": event_id,
            "read_model": previous,
        }
        self.wfile.write(format_sse_event("dashboard.snapshot", snapshot, event_id=event_id, retry=3000))
        self.wfile.flush()
        if once:
            return

        last_heartbeat = time.monotonic()
        while True:
            time.sleep(DASHBOARD_SSE_POLL_SECONDS)
            current = load_dashboard_read_model() or {}
            delta = build_dashboard_delta(previous, current)
            if delta["has_changes"]:
                self.wfile.write(
                    format_sse_event("dashboard.delta", delta, event_id=delta["fingerprint"])
                )
                self.wfile.flush()
                previous = current
                last_heartbeat = time.monotonic()
            elif time.monotonic() - last_heartbeat >= DASHBOARD_SSE_HEARTBEAT_SECONDS:
                self.wfile.write(format_sse_comment("heartbeat"))
                self.wfile.flush()
                last_heartbeat = time.monotonic()

    def send_error_response(self, error):
        try:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "error": error}).encode("utf-8"))
        except ConnectionError:
            pass

    def send_auth_error_response(self):
        try:
            self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.send_header("WWW-Authenticate", "Bearer")
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "error": "Unauthorized"}).encode("utf-8"))
        except ConnectionError:
            pass

    def send_csrf_error_response(self):
        try:
            self.send_response(403)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "error": "CSRF validation failed"}).encode("utf-8"))
        except ConnectionError:
            pass

    def send_payload_too_large_response(self, error):
        try:
            self.send_response(413)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "error": error}).encode("utf-8"))
        except ConnectionError:
            pass

    def send_method_not_allowed_response(self, allowed_method):
        try:
            self.send_response(405)
            self.send_header("Content-Type", "application/json")
            self.send_header("Allow", allowed_method)
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "error": "Method Not Allowed"}).encode("utf-8"))
        except ConnectionError:
            pass

    def complete_task(self, project, task_id):
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

            # Write the file first with retries
            write_json_with_retry(tasks_file, board)
            print(f"[DashboardAPI] Successfully saved completed task status in tasks.json.")

            # If it was the active task, run the official task_done.ps1 to execute hooks
            if is_active:
                task_done_script = get_platform_path("Scripts", "task_done.ps1")
                cmd = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", 
                       str(task_done_script), "-Force"]
                print(f"[DashboardAPI] Running task_done.ps1 for active task completion (timeout={DASHBOARD_COMMAND_TIMEOUT_SEC:.0f}s)...")
                subprocess.run(cmd, capture_output=True, timeout=DASHBOARD_COMMAND_TIMEOUT_SEC)
                return True, f"Active task {task_id} completed successfully via task_done.ps1"
            else:
                # Regenerate the dashboard
                dashboard_script = get_platform_path("Scripts", "gen_dashboard.ps1")
                cmd = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", 
                       str(dashboard_script)]
                print(f"[DashboardAPI] Running gen_dashboard.ps1 for dashboard refresh (timeout={DASHBOARD_COMMAND_TIMEOUT_SEC:.0f}s)...")
                subprocess.run(cmd, capture_output=True, timeout=DASHBOARD_COMMAND_TIMEOUT_SEC)
                return True, f"Task {task_id} completed successfully"

        except subprocess.TimeoutExpired as te:
            print(f"[DashboardAPI] Timeout expired executing completion script: {te}")
            return True, f"Task {task_id} completed but post-completion command timed out"
        except Exception as e:
            print(f"[DashboardAPI] Error completing task: {e}")
            return False, str(e)

    def delete_task(self, project, task_id):
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

            # Regenerate the dashboard
            dashboard_script = get_platform_path("Scripts", "gen_dashboard.ps1")
            cmd = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", 
                   str(dashboard_script)]
            print(f"[DashboardAPI] Running gen_dashboard.ps1 for dashboard refresh (timeout={DASHBOARD_COMMAND_TIMEOUT_SEC:.0f}s)...")
            subprocess.run(cmd, capture_output=True, timeout=DASHBOARD_COMMAND_TIMEOUT_SEC)
            return True, f"Task {task_id} deleted successfully"

        except subprocess.TimeoutExpired as te:
            print(f"[DashboardAPI] Timeout expired executing delete refresh script: {te}")
            return True, f"Task {task_id} deleted but dashboard refresh timed out"
        except Exception as e:
            print(f"[DashboardAPI] Error deleting task: {e}")
            return False, str(e)

def main():
    if "--rotate-token" in sys.argv:
        token = rotate_api_token()
        print(token)
        return

    ensure_api_token()
    ensure_csrf_token()
    server_class = http.server.HTTPServer
    if hasattr(http.server, "ThreadingHTTPServer"):
        server_class = http.server.ThreadingHTTPServer

    socketserver.TCPServer.allow_reuse_address = True
    
    bind_host = get_bind_host()
    with server_class((bind_host, PORT), DashboardAPIHandler) as httpd:
        print(f"DEV_CORE Dashboard API Server listening on {bind_host}:{PORT}...")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down API Server.")
            sys.exit(0)

if __name__ == "__main__":
    main()
