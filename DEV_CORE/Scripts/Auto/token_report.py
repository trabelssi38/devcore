import argparse
import json
import os
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path


INPUT_TOKEN_PRICE = 0.000003
CACHED_INPUT_TOKEN_PRICE = 0.00000045
OUTPUT_TOKEN_PRICE = 0.000015
ESTIMATED_INPUT_PER_MODEL_TURN = 15000
ESTIMATED_CACHE_RATIO = 0.85
DEFAULT_PRICING_PROFILE = {
    "provider": "devcore",
    "pricing_per_million_usd": {
        "input": INPUT_TOKEN_PRICE * 1_000_000,
        "cached_input": CACHED_INPUT_TOKEN_PRICE * 1_000_000,
        "output": OUTPUT_TOKEN_PRICE * 1_000_000,
    },
}


def record_metric(metric_type, value, unit, payload=None, project="devcore", task_id=""):
    platform_root = Path(os.environ.get("DEVCORE_PLATFORM_ROOT", Path(__file__).resolve().parents[2]))
    metrics_script = platform_root / "Scripts" / "metrics_service.ps1"
    if not metrics_script.exists():
        return
    try:
        subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(metrics_script),
                "-Action",
                "Record",
                "-Source",
                "token_report",
                "-Project",
                project,
                "-TaskId",
                task_id,
                "-MetricType",
                metric_type,
                "-Value",
                str(float(value or 0)),
                "-Unit",
                unit,
                "-PayloadJson",
                json.dumps(payload or {}, ensure_ascii=False),
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except Exception:
        pass


def format_duration(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    if h > 0:
        return f"{h}h {m}m"
    return f"{m}m"


def clean_task_id(text):
    match = re.search(r"\bT-(\d+)\b", text or "", re.IGNORECASE)
    if match:
        return f"T-{int(match.group(1)):02d}"
    return None


def task_ids_from_text(text):
    return sorted({clean_task_id(match) for match in re.findall(r"\bT-\d+\b", text or "", re.IGNORECASE) if clean_task_id(match)})


def parse_created_at(created_at_str):
    if not created_at_str:
        return None
    s = str(created_at_str).replace("Z", "")
    if "+" in s:
        s = s.split("+")[0]
    if "-" in s[10:]:
        s = s[:10] + s[10:].split("-")[0]

    if "." in s:
        main_part, frac_part = s.split(".", 1)
        frac_part = frac_part[:6].ljust(6, "0")
        try:
            return datetime.strptime(f"{main_part}.{frac_part}", "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
            pass

    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s.split("+")[0], fmt)
        except ValueError:
            continue
    return None


def read_jsonl(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    yield json.loads(line)
                except Exception:
                    continue
    except Exception:
        return


def as_text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                parts.append(as_text(item.get("text") or item.get("content") or item.get("output") or item.get("input")))
            else:
                parts.append(as_text(item))
        return "\n".join(part for part in parts if part)
    if isinstance(value, dict):
        if "text" in value:
            return as_text(value.get("text"))
        if "content" in value:
            return as_text(value.get("content"))
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def default_model_pricing():
    return {
        "schema_version": 1,
        "default_model": "default-current",
        "models": {"default-current": DEFAULT_PRICING_PROFILE},
        "aliases": {},
        "client_defaults": {},
    }


def load_model_pricing():
    platform_root = Path(os.environ.get("DEVCORE_PLATFORM_ROOT", Path(__file__).resolve().parents[2]))
    pricing_path = Path(os.environ.get("DEVCORE_MODEL_PRICING_PATH", platform_root / "Config" / "model_pricing.json"))
    registry = default_model_pricing()
    if not pricing_path.exists():
        return registry
    try:
        loaded = json.loads(pricing_path.read_text(encoding="utf-8-sig"))
    except Exception:
        return registry
    if not isinstance(loaded, dict) or not isinstance(loaded.get("models"), dict):
        return registry
    registry.update(loaded)
    registry.setdefault("models", {}).setdefault("default-current", DEFAULT_PRICING_PROFILE)
    registry.setdefault("aliases", {})
    registry.setdefault("client_defaults", {})
    registry.setdefault("default_model", "default-current")
    return registry


def normalize_model_name(model):
    value = str(model or "").strip().lower()
    value = re.sub(r"\s*\([^)]*\)\s*$", "", value).strip()
    value = re.sub(r"\s+", "-", value)
    if value.startswith("models/"):
        value = value.split("/", 1)[1]
    return value


INVALID_MODEL_FRAGMENTS = (
    "comment-on-this-change",
    "ask-about-it",
    "if-reporting-what-model",
    "human-readable-name",
    "exact-string",
)


def valid_model_candidate(model):
    normalized = normalize_model_name(model)
    if not normalized:
        return False
    return not any(fragment in normalized for fragment in INVALID_MODEL_FRAGMENTS)


def resolve_model_pricing(model, registry):
    registry = registry or default_model_pricing()
    models = registry.get("models", {})
    aliases = {normalize_model_name(k): normalize_model_name(v) for k, v in registry.get("aliases", {}).items()}
    default_model = normalize_model_name(registry.get("default_model") or "default-current")
    requested = normalize_model_name(model)
    profile_id = aliases.get(requested, requested) if requested else default_model
    if profile_id not in models:
        profile_id = default_model if default_model in models else "default-current"
    return profile_id, models.get(profile_id, DEFAULT_PRICING_PROFILE)


def default_model_for_client(client, app, registry):
    defaults = registry.get("client_defaults", {}) if registry else {}
    for key in (app, client):
        normalized = normalize_model_name(key)
        if normalized in defaults:
            return defaults[normalized]
    return None


def pricing_token_value(profile, key, fallback):
    try:
        per_million = profile.get("pricing_per_million_usd", {}).get(key)
        if per_million is not None:
            return float(per_million) / 1_000_000
    except Exception:
        pass
    return fallback


def calculate_cost(tokens, cache_hits, output_tokens, pricing_profile=None):
    pricing_profile = pricing_profile or DEFAULT_PRICING_PROFILE
    input_price = pricing_token_value(pricing_profile, "input", INPUT_TOKEN_PRICE)
    cached_input_price = pricing_token_value(pricing_profile, "cached_input", CACHED_INPUT_TOKEN_PRICE)
    output_price = pricing_token_value(pricing_profile, "output", OUTPUT_TOKEN_PRICE)
    normal_in = max(tokens - cache_hits - output_tokens, 0)
    return (
        normal_in * input_price
        + cache_hits * cached_input_price
        + output_tokens * output_price
    )


def first_model_value(value, depth=0):
    if depth > 4:
        return None
    if isinstance(value, dict):
        for key in ("model", "model_slug", "model_name", "selected_model", "requested_model", "original_model"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate
        for key, nested in value.items():
            if key in {"content", "text", "output", "arguments"}:
                continue
            candidate = first_model_value(nested, depth + 1)
            if candidate:
                return candidate
    if isinstance(value, list):
        for item in value[:8]:
            candidate = first_model_value(item, depth + 1)
            if candidate:
                return candidate
    return None


def model_from_settings_change(text):
    match = re.search(
        r"`?Model Selection`?\s+from\s+(.+?)\s+to\s+(.+?)(?:\.\s+(?:No need|If reporting)|<|\n|$)",
        text or "",
        re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return None
    model = re.sub(r"\s*\([^)]*\)\s*$", "", match.group(2).strip().rstrip(" ."))
    return model if valid_model_candidate(model) else None


def detect_model(payload, row):
    candidates = (
        first_model_value(payload),
        first_model_value(row),
        model_from_settings_change(as_text(payload.get("content") if isinstance(payload, dict) else "")),
        model_from_settings_change(as_text(row.get("content") if isinstance(row, dict) else "")),
    )
    return next((candidate for candidate in candidates if valid_model_candidate(candidate)), None)


def resolve_turn_model(explicit_model, current_model, client_default_model):
    if explicit_model:
        return explicit_model, "payload"
    if current_model:
        return current_model, "timeline"
    if client_default_model:
        return client_default_model, "client_default"
    return None, "default_model"


def usage_from_payload(payload):
    usage = payload.get("token_usage") or payload.get("usage") or {}
    if not isinstance(usage, dict):
        return None

    input_tokens = int(
        usage.get("input_tokens")
        or usage.get("prompt_tokens")
        or usage.get("total_input_tokens")
        or 0
    )
    cache_hits = int(
        usage.get("cached_input_tokens")
        or usage.get("cache_read_input_tokens")
        or usage.get("cache_hits")
        or 0
    )
    output_tokens = int(
        usage.get("output_tokens")
        or usage.get("completion_tokens")
        or usage.get("total_output_tokens")
        or 0
    )
    total_tokens = int(usage.get("total_tokens") or input_tokens + output_tokens)

    if total_tokens <= 0 and input_tokens <= 0 and output_tokens <= 0:
        return None

    if input_tokens <= 0:
        input_tokens = max(total_tokens - output_tokens, 0)

    return {
        "tokens": max(total_tokens, input_tokens + output_tokens),
        "cache_hits": cache_hits,
        "output_tokens": output_tokens,
        "turns": 1,
        "estimated": False,
    }


def estimated_usage_from_text(text):
    output_tokens = max(len(text or "") // 4, 0)
    input_tokens = ESTIMATED_INPUT_PER_MODEL_TURN
    return {
        "tokens": input_tokens + output_tokens,
        "cache_hits": int(input_tokens * ESTIMATED_CACHE_RATIO),
        "output_tokens": output_tokens,
        "turns": 1,
        "estimated": True,
    }


def add_usage(left, right):
    left["tokens"] += int(right.get("tokens", 0))
    left["cache_hits"] += int(right.get("cache_hits", 0))
    left["output_tokens"] += int(right.get("output_tokens", 0))
    left["turns"] += int(right.get("turns", 0))
    if "cost_usd" in right:
        left["cost_usd"] += float(right.get("cost_usd") or 0)
    else:
        left["cost_usd"] += calculate_cost(
            int(right.get("tokens", 0)),
            int(right.get("cache_hits", 0)),
            int(right.get("output_tokens", 0)),
        )


def empty_model_usage():
    return {
        "tokens": 0,
        "cache_hits": 0,
        "output_tokens": 0,
        "turns": 0,
        "cost_usd": 0.0,
        "sources": {},
        "pricing_fallback": False,
    }


def add_model_usage(collection, model_id, usage, source):
    if model_id not in collection:
        collection[model_id] = empty_model_usage()
    bucket = collection[model_id]
    bucket["tokens"] += int(usage.get("tokens", 0))
    bucket["cache_hits"] += int(usage.get("cache_hits", 0))
    bucket["output_tokens"] += int(usage.get("output_tokens", 0))
    turns = int(usage.get("turns", 0))
    bucket["turns"] += turns
    bucket["cost_usd"] += float(usage.get("cost_usd") or 0)
    bucket["pricing_profile"] = usage.get("pricing_profile")
    bucket["pricing_fallback"] = bool(bucket.get("pricing_fallback") or usage.get("pricing_fallback"))
    bucket["sources"][source] = bucket["sources"].get(source, 0) + max(turns, 1)


def merge_model_usage(left, right):
    for model_id, usage in (right or {}).items():
        if model_id not in left:
            left[model_id] = empty_model_usage()
        bucket = left[model_id]
        bucket["tokens"] += int(usage.get("tokens", 0))
        bucket["cache_hits"] += int(usage.get("cache_hits", 0))
        bucket["output_tokens"] += int(usage.get("output_tokens", 0))
        bucket["turns"] += int(usage.get("turns", 0))
        bucket["cost_usd"] += float(usage.get("cost_usd") or 0)
        bucket["pricing_profile"] = usage.get("pricing_profile") or bucket.get("pricing_profile")
        bucket["pricing_fallback"] = bool(bucket.get("pricing_fallback") or usage.get("pricing_fallback"))
        for source, count in usage.get("sources", {}).items():
            bucket["sources"][source] = bucket["sources"].get(source, 0) + int(count)


def finalize_model_usage(model_usage):
    finalized = {}
    for model_id, usage in sorted((model_usage or {}).items()):
        item = dict(usage)
        item["cost_usd"] = round(float(item.get("cost_usd") or 0), 4)
        finalized[model_id] = item
    return finalized


def cost_by_model(model_usage):
    return {
        model_id: round(float(usage.get("cost_usd") or 0), 4)
        for model_id, usage in sorted((model_usage or {}).items())
    }


def fallback_models(model_usage):
    return sorted(
        model_id
        for model_id, usage in (model_usage or {}).items()
        if usage.get("pricing_fallback")
    )


def empty_bucket():
    return {"tokens": 0, "cache_hits": 0, "output_tokens": 0, "turns": 0, "cost_usd": 0.0}


def empty_stats_bucket(include_sessions=False):
    bucket = {"tokens": 0, "cache_hits": 0, "output_tokens": 0, "cost_usd": 0.0, "model_usage": {}}
    if include_sessions:
        bucket["sessions"] = 0
    return bucket


def discover_projects(memory_path):
    valid_projects = ["devcore", "cea_dashboard", "job_tracker", "default"]
    task_to_project = {}

    # 1. Read tasks from devcore.db
    devcore_data = Path(memory_path).parent
    db_path = devcore_data / "devcore.db"
    if db_path.exists():
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT id, project FROM tasks")
            for tid, proj in cur.fetchall():
                if proj and proj.lower() not in valid_projects:
                    valid_projects.append(proj.lower())
                tid_upper = tid.upper()
                if tid_upper not in task_to_project:
                    task_to_project[tid_upper] = []
                if proj.lower() not in task_to_project[tid_upper]:
                    task_to_project[tid_upper].append(proj.lower())
            conn.close()
        except Exception:
            pass

    # 2. Read tasks from Memory directory
    memory_root = Path(memory_path)
    if memory_root.exists():
        for project_dir in memory_root.iterdir():
            if not project_dir.is_dir():
                continue
            name = project_dir.name.lower()
            if name not in ["archive", "patterns", "scores", "default", "scripts"] and name not in valid_projects:
                valid_projects.append(name)

            tasks_file = project_dir / "tasks.json"
            if not tasks_file.exists():
                continue
            try:
                board = json.loads(tasks_file.read_text(encoding="utf-8-sig"))
                for task in board.get("tasks", []):
                    tid = task.get("id")
                    if tid:
                        tid_upper = tid.upper()
                        if tid_upper not in task_to_project:
                            task_to_project[tid_upper] = []
                        if name not in task_to_project[tid_upper]:
                            task_to_project[tid_upper].append(name)
            except Exception:
                continue

    return valid_projects, task_to_project


def detect_project(text, valid_projects, fallback="devcore"):
    normalized = (text or "").replace("\\\\", "/").replace("\\", "/").lower()
    best_project = fallback
    best_idx = -1
    for project in valid_projects:
        project_lower = project.lower()
        if f"/{project_lower}/" in normalized or normalized.endswith(f"/{project_lower}") or project_lower in normalized:
            idx = normalized.rfind(project_lower)
            if idx > best_idx:
                best_idx = idx
                best_project = project_lower
    return best_project


def discover_sources(userprofile):
    import time
    cutoff = time.time() - 180 * 86400
    home = Path(userprofile)
    sources = []

    antigravity_brain = home / ".gemini" / "antigravity" / "brain"
    if antigravity_brain.exists():
        for folder in antigravity_brain.iterdir():
            if not folder.is_dir() or folder.name == "tempmediaStorage":
                continue
            overview = folder / ".system_generated" / "logs" / "overview.txt"
            transcript = folder / ".system_generated" / "logs" / "transcript.jsonl"
            target_path = None
            if transcript.exists():
                target_path = transcript
            elif overview.exists():
                target_path = overview
            
            if target_path:
                try:
                    if target_path.stat().st_mtime >= cutoff:
                        sources.append({"client": "antigravity", "app": "antigravity", "session_id": folder.name, "path": target_path})
                except Exception:
                    pass

    codex_sessions = home / ".codex" / "sessions"
    if codex_sessions.exists():
        for path in codex_sessions.rglob("*.jsonl"):
            try:
                if path.stat().st_mtime >= cutoff:
                    sources.append({"client": "codex", "app": "codex", "session_id": path.stem, "path": path})
            except Exception:
                pass

    claude_projects = home / ".claude" / "projects"
    if claude_projects.exists():
        for path in claude_projects.rglob("*.jsonl"):
            if "\\subagents\\" in str(path).lower() or "/subagents/" in str(path).lower():
                continue
            try:
                if path.stat().st_mtime >= cutoff:
                    sources.append({"client": "claude", "app": "claude-code", "session_id": path.stem, "path": path})
            except Exception:
                pass

    opencode_home = Path(os.environ.get("OPENCODE_HOME", home / ".config" / "opencode"))
    if opencode_home.exists():
        for path in opencode_home.rglob("*.jsonl"):
            if "node_modules" in [part.lower() for part in path.parts]:
                continue
            try:
                if path.stat().st_mtime >= cutoff:
                    sources.append({"client": "opencode", "app": "opencode", "session_id": path.stem, "path": path})
            except Exception:
                pass

    return sources


def parse_source(source, valid_projects, task_to_project, pricing_registry=None):
    client = source["client"]
    session_id = source["session_id"]
    app = source.get("app", client)
    timestamps = []
    user_turns = 0
    model_turns = 0
    session_tasks = set()
    current_task = "Sans tache"
    detected_project = "devcore"
    task_tokens = {}
    cwd_hint = ""
    session_models = set()
    session_pricing_profiles = set()
    session_model_usage = {}
    prompt_model_turns = []
    current_model = None

    for row in read_jsonl(source["path"]):
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else row

        if client == "codex" and row.get("type") == "session_meta":
            session_id = payload.get("session_id") or payload.get("id") or session_id
            app = payload.get("originator") or payload.get("source") or app
            cwd_hint = payload.get("cwd") or cwd_hint
            detected_project = detect_project(cwd_hint, valid_projects, detected_project)
            ts = parse_created_at(payload.get("timestamp") or row.get("timestamp"))
            if ts:
                timestamps.append(ts + timedelta(hours=1))
            continue

        row_model = detect_model(payload, row)
        if row_model:
            current_model = row_model

        ts = parse_created_at(row.get("created_at") or row.get("timestamp") or payload.get("timestamp"))
        if ts:
            timestamps.append(ts + timedelta(hours=1))

        content = "\n".join(
            part
            for part in [
                as_text(payload.get("content")),
                as_text(payload.get("message", {}).get("content") if isinstance(payload.get("message"), dict) else ""),
                as_text(payload.get("arguments")),
                as_text(payload.get("output")),
                as_text(payload.get("tool_calls")),
                cwd_hint,
                str(source["path"]),
            ]
            if part
        )

        detected_project = detect_project(content, valid_projects, detected_project)
        task_ids = task_ids_from_text(content)
        if task_ids:
            for task_id in task_ids:
                current_task = task_id
                session_tasks.add(task_id)
                proj_list = task_to_project.get(task_id.upper())
                if proj_list:
                    if detected_project in proj_list:
                        pass
                    else:
                        detected_project = proj_list[0]

        role = payload.get("role") or payload.get("source") or payload.get("type") or row.get("type")
        role_text = str(role).lower()
        is_user = "user" in role_text
        is_model = any(marker in role_text for marker in ["assistant", "model", "planner_response"]) or (
            client == "codex" and payload.get("type") == "message" and payload.get("role") == "assistant"
        )

        if is_user:
            user_turns += 1

        usage = usage_from_payload(payload)
        if not usage and is_model:
            usage = estimated_usage_from_text(content)

        if usage:
            explicit_model = detect_model(payload, row)
            client_default_model = default_model_for_client(client, app, pricing_registry)
            detected_model, model_source = resolve_turn_model(explicit_model, current_model, client_default_model)
            pricing_profile_id, pricing_profile = resolve_model_pricing(detected_model, pricing_registry)
            model_id = normalize_model_name(detected_model) if detected_model else pricing_profile_id
            default_profile_id = normalize_model_name((pricing_registry or {}).get("default_model") or "default-current")
            usage["model"] = model_id
            usage["pricing_profile"] = pricing_profile_id
            usage["pricing_fallback"] = bool(detected_model and pricing_profile_id == default_profile_id and model_id != default_profile_id)
            usage["cost_usd"] = calculate_cost(
                int(usage.get("tokens", 0)),
                int(usage.get("cache_hits", 0)),
                int(usage.get("output_tokens", 0)),
                pricing_profile,
            )
            session_models.add(model_id)
            session_pricing_profiles.add(pricing_profile_id)
            add_model_usage(session_model_usage, model_id, usage, model_source)
            model_turns += usage["turns"]
            targets = task_ids or ([current_task] if current_task else ["Sans tache"])
            prompt_model_turns.append(
                {
                    "index": model_turns,
                    "model": model_id,
                    "source": model_source,
                    "pricing_profile": pricing_profile_id,
                    "tokens": int(usage.get("tokens", 0)),
                    "cache_hits": int(usage.get("cache_hits", 0)),
                    "output_tokens": int(usage.get("output_tokens", 0)),
                    "cost_usd": round(float(usage.get("cost_usd") or 0), 4),
                    "estimated": bool(usage.get("estimated")),
                    "tasks": targets,
                }
            )
            share = max(len(targets), 1)
            for task_id in targets:
                task_proj = detected_project
                proj_list = task_to_project.get(task_id.upper())
                if proj_list:
                    if detected_project in proj_list:
                        task_proj = detected_project
                    else:
                        task_proj = proj_list[0]

                if task_id not in task_tokens:
                    task_tokens[task_id] = {
                        "project": task_proj,
                        "tokens": 0,
                        "cache_hits": 0,
                        "output_tokens": 0,
                        "turns": 0,
                        "cost_usd": 0.0,
                        "model_usage": {},
                    }
                task_tokens[task_id]["tokens"] += usage["tokens"] // share
                task_tokens[task_id]["cache_hits"] += usage["cache_hits"] // share
                task_tokens[task_id]["output_tokens"] += usage["output_tokens"] // share
                task_tokens[task_id]["turns"] += max(usage["turns"] // share, 1)
                task_tokens[task_id]["cost_usd"] += usage["cost_usd"] / share
                split_usage = {
                    "tokens": usage["tokens"] // share,
                    "cache_hits": usage["cache_hits"] // share,
                    "output_tokens": usage["output_tokens"] // share,
                    "turns": max(usage["turns"] // share, 1),
                    "cost_usd": usage["cost_usd"] / share,
                    "pricing_profile": pricing_profile_id,
                }
                add_model_usage(task_tokens[task_id]["model_usage"], model_id, split_usage, model_source)

    if not timestamps or not task_tokens:
        return None

    min_dt = min(timestamps)
    max_dt = max(timestamps)
    duration_sec = max((max_dt - min_dt).total_seconds(), 60)
    session_usage = empty_bucket()
    for usage in task_tokens.values():
        add_usage(session_usage, usage)

    return {
        "id": session_id,
        "client": client,
        "app": app,
        "project": detected_project,
        "tasks": sorted(session_tasks) if session_tasks else ["Sans tache"],
        "date": min_dt.strftime("%Y-%m-%d"),
        "start_time": min_dt.strftime("%H:%M:%S"),
        "end_time": max_dt.strftime("%H:%M:%S"),
        "duration": format_duration(duration_sec),
        "tokens": session_usage["tokens"],
        "cache_hits": session_usage["cache_hits"],
        "output_tokens": session_usage["output_tokens"],
        "turns": model_turns + user_turns,
        "cost_usd": round(session_usage["cost_usd"], 4),
        "models": sorted(session_models),
        "pricing_profiles": sorted(session_pricing_profiles),
        "model_usage": finalize_model_usage(session_model_usage),
        "model_turns": prompt_model_turns,
        "_task_tokens": task_tokens,
    }


def recalculate_session_pricing(session, registry):
    registry = registry or default_model_pricing()
    default_profile_id = normalize_model_name(registry.get("default_model") or "default-current")
    
    total_cost = 0.0
    new_model_usage = {}
    
    model_usage = session.get("model_usage", {})
    for model_name, usage in model_usage.items():
        pricing_profile_id, pricing_profile = resolve_model_pricing(model_name, registry)
        normalized_name = normalize_model_name(model_name)
        is_fallback = bool(model_name and pricing_profile_id == default_profile_id and normalized_name != default_profile_id)
        
        cost = calculate_cost(
            int(usage.get("tokens", 0)),
            int(usage.get("cache_hits", 0)),
            int(usage.get("output_tokens", 0)),
            pricing_profile
        )
        
        usage_copy = dict(usage)
        usage_copy["pricing_profile"] = pricing_profile_id
        usage_copy["pricing_fallback"] = is_fallback
        usage_copy["cost_usd"] = round(cost, 4)
        
        new_model_usage[model_name] = usage_copy
        total_cost += cost
        
    session["model_usage"] = new_model_usage
    session["cost_usd"] = round(total_cost, 4)


def aggregate_sessions(sessions):
    totals = {
        "tokens": 0,
        "cache_hits": 0,
        "output_tokens": 0,
        "duration_seconds": 0,
        "sessions_count": 0,
        "cost_usd": 0.0,
        "model_usage": {},
    }
    projects_data = {}
    tasks_data = {}
    clients_data = {}
    public_sessions = []

    for session in sessions:
        totals["tokens"] += session["tokens"]
        totals["cache_hits"] += session["cache_hits"]
        totals["output_tokens"] += session["output_tokens"]
        totals["sessions_count"] += 1
        totals["cost_usd"] += session["cost_usd"]
        merge_model_usage(totals["model_usage"], session.get("model_usage", {}))

        project = session["project"]
        if project not in projects_data:
            projects_data[project] = empty_stats_bucket(include_sessions=True)
        projects_data[project]["tokens"] += session["tokens"]
        projects_data[project]["cache_hits"] += session["cache_hits"]
        projects_data[project]["output_tokens"] += session["output_tokens"]
        projects_data[project]["sessions"] += 1
        projects_data[project]["cost_usd"] += session["cost_usd"]
        merge_model_usage(projects_data[project]["model_usage"], session.get("model_usage", {}))

        client = session["client"]
        if client not in clients_data:
            clients_data[client] = empty_stats_bucket(include_sessions=True)
        clients_data[client]["tokens"] += session["tokens"]
        clients_data[client]["cache_hits"] += session["cache_hits"]
        clients_data[client]["output_tokens"] += session["output_tokens"]
        clients_data[client]["sessions"] += 1
        clients_data[client]["cost_usd"] += session["cost_usd"]
        merge_model_usage(clients_data[client]["model_usage"], session.get("model_usage", {}))

        for tid, usage in session.get("_task_tokens", {}).items():
            proj = usage.get("project", project)
            task_key = f"{proj}_{tid}"
            if task_key not in tasks_data:
                tasks_data[task_key] = {
                    "project": proj,
                    "tokens": 0,
                    "cache_hits": 0,
                    "output_tokens": 0,
                    "turns": 0,
                    "cost_usd": 0.0,
                    "model_usage": {},
                }
            add_usage(tasks_data[task_key], usage)
            merge_model_usage(tasks_data[task_key]["model_usage"], usage.get("model_usage", {}))

        public_session = {
            k: v for k, v in session.items()
            if not k.startswith("_")
        }
        public_sessions.append(public_session)

    totals["duration_minutes"] = int(totals.pop("duration_seconds", 0) // 60)
    totals["cost_usd"] = round(totals["cost_usd"], 4)
    totals["model_usage"] = finalize_model_usage(totals["model_usage"])
    totals["cost_by_model"] = cost_by_model(totals["model_usage"])
    totals["unregistered_models"] = fallback_models(totals["model_usage"])
    for collection in (projects_data, tasks_data, clients_data):
        for values in collection.values():
            values["cost_usd"] = round(values["cost_usd"], 4)
            values["model_usage"] = finalize_model_usage(values.get("model_usage", {}))
            values["cost_by_model"] = cost_by_model(values["model_usage"])
            values["unregistered_models"] = fallback_models(values["model_usage"])

    return {
        "totals": totals,
        "projects": projects_data,
        "clients": clients_data,
        "tasks": tasks_data,
        "model_costs": {
            "global": totals["cost_by_model"],
            "unregistered": totals["unregistered_models"],
            "projects": {
                project: values["cost_by_model"]
                for project, values in sorted(projects_data.items())
            },
            "project_unregistered": {
                project: values["unregistered_models"]
                for project, values in sorted(projects_data.items())
                if values.get("unregistered_models")
            },
        },
        "sessions": sorted(public_sessions, key=lambda x: x["date"] + " " + x["start_time"], reverse=True),
    }


def write_html_report(result_summary, reports_dir, tdate):
    day_sessions = [s for s in result_summary["sessions"] if s["date"] == tdate]
    day_tokens = sum(s["tokens"] for s in day_sessions)
    day_cache = sum(s["cache_hits"] for s in day_sessions)
    day_cost = sum(s["cost_usd"] for s in day_sessions)

    def fmt_tokens(value):
        if value > 1_000_000:
            return f"{value / 1_000_000:.2f} M"
        if value > 0:
            return f"{value / 1000:.1f} K"
        return "0"

    if day_sessions:
        rows = []
        for session in day_sessions:
            tasks = ", ".join(session["tasks"])
            rows.append(
                f"<div class='session-item'><b>{session['client']}</b> {session['id']} | "
                f"{session['start_time']} - {session['end_time']} | {tasks} | "
                f"{session['tokens']:,} tokens | ${session['cost_usd']:.2f}</div>"
            )
        sessions_html = "\n".join(rows)
    else:
        sessions_html = "<div class='no-sessions'>Aucune session active enregistree pour cette journee.</div>"

    html = f"""<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <title>Rapport de Tokens DEV_CORE - {tdate}</title>
  <style>
    body {{ font-family: Arial, sans-serif; background:#0f172a; color:#f8fafc; padding:32px; }}
    .card {{ background:#1e293b; border:1px solid #334155; border-radius:8px; padding:18px; margin:12px 0; }}
    .grid {{ display:grid; grid-template-columns:repeat(4,minmax(120px,1fr)); gap:12px; }}
    .value {{ font-size:24px; font-weight:700; }}
    .label {{ color:#94a3b8; font-size:12px; text-transform:uppercase; }}
    .session-item {{ padding:10px 0; border-bottom:1px solid #334155; }}
  </style>
</head>
<body>
  <h1>DEV_CORE - Rapport tokens {tdate}</h1>
  <div class="grid">
    <div class="card"><div class="value">{fmt_tokens(day_tokens)}</div><div class="label">Tokens</div></div>
    <div class="card"><div class="value">{fmt_tokens(day_cache)}</div><div class="label">Cache</div></div>
    <div class="card"><div class="value">${day_cost:.2f}</div><div class="label">Cout</div></div>
    <div class="card"><div class="value">{len(day_sessions)}</div><div class="label">Sessions</div></div>
  </div>
  <div class="card">{sessions_html}</div>
</body>
</html>"""

    report_path = Path(reports_dir) / f"{tdate}-report.html"
    report_path.write_text(html, encoding="utf-8")
    print(f"[SUCCESS] Rapport de tokens HTML genere pour {tdate} -> {report_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate DEV_CORE token report by project, task, and coding client.")
    parser.add_argument("--date", type=str, help="Date au format YYYY-MM-DD (par defaut aujourd'hui)")
    args = parser.parse_args()

    tdate = args.date or datetime.now().strftime("%Y-%m-%d")
    userprofile = os.environ.get("USERPROFILE") or str(Path.home())
    devcore_data = os.environ.get("DEVCORE_DATA_ROOT", str(Path(__file__).resolve().parents[4] / "DEV_CORE_DATA"))
    reports_dir = Path(devcore_data) / "Logs" / "token_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    memory_path = Path(devcore_data) / "Memory"

    valid_projects, task_to_project = discover_projects(memory_path)
    pricing_registry = load_model_pricing()
    sources = discover_sources(userprofile)
    sessions = []
    for source in sources:
        session = parse_source(source, valid_projects, task_to_project, pricing_registry)
        if session:
            sessions.append(session)

    # Load and merge historical archived sessions to preserve old models/costs (e.g. gemini-3.1-flash, codex)
    archive_dir = reports_dir / "archive"
    archived_sessions = []
    if archive_dir.exists():
        for archive_file in archive_dir.glob("*.json"):
            try:
                loaded = json.loads(archive_file.read_text(encoding="utf-8"))
                if isinstance(loaded, list):
                    archived_sessions.extend(loaded)
            except Exception as e:
                print(f"[WARNING] Error reading archive {archive_file.name}: {e}")

    active_ids = {s["id"] for s in sessions}
    for s in archived_sessions:
        if s.get("id") not in active_ids:
            sessions.append(s)

    for session in sessions:
        recalculate_session_pricing(session, pricing_registry)

    result_summary = aggregate_sessions(sessions)
    
    # Merge Headroom Proxy stats to capture untagged / direct requests
    headroom_stats_path = Path(devcore_data) / "Metrics" / "headroom_stats.json"
    if headroom_stats_path.exists():
        try:
            h_data = json.loads(headroom_stats_path.read_text(encoding="utf-8-sig"))
            h_tasks = h_data.get("tasks", {})
            auc_stats = h_tasks.get("Aucune")
            if auc_stats:
                h_tokens = int(auc_stats.get("total_tokens", 0))
                h_out = int(auc_stats.get("tokens_out", 0))
                h_in = int(auc_stats.get("tokens_in", 0))
                h_cache = int(h_in * 0.85)
                h_cost = calculate_cost(h_tokens, h_cache, h_out)
                
                # Add to totals
                result_summary["totals"]["tokens"] += h_tokens
                result_summary["totals"]["cache_hits"] += h_cache
                result_summary["totals"]["output_tokens"] += h_out
                result_summary["totals"]["cost_usd"] += h_cost
                
                # Add to client "headroom-proxy"
                if "clients" not in result_summary:
                    result_summary["clients"] = {}
                if "headroom-proxy" not in result_summary["clients"]:
                    result_summary["clients"]["headroom-proxy"] = empty_stats_bucket(include_sessions=True)
                result_summary["clients"]["headroom-proxy"]["tokens"] += h_tokens
                result_summary["clients"]["headroom-proxy"]["cache_hits"] += h_cache
                result_summary["clients"]["headroom-proxy"]["output_tokens"] += h_out
                result_summary["clients"]["headroom-proxy"]["cost_usd"] += h_cost
                result_summary["clients"]["headroom-proxy"]["sessions"] += 1
                
                # Add to project "devcore"
                if "devcore" not in result_summary["projects"]:
                    result_summary["projects"]["devcore"] = empty_stats_bucket(include_sessions=True)
                result_summary["projects"]["devcore"]["tokens"] += h_tokens
                result_summary["projects"]["devcore"]["cache_hits"] += h_cache
                result_summary["projects"]["devcore"]["output_tokens"] += h_out
                result_summary["projects"]["devcore"]["cost_usd"] += h_cost
                
                print(f"[TokenReport] Merged {h_tokens:,} headroom-proxy tokens for untagged tasks.")
        except Exception as e:
            print(f"[WARNING] Error merging headroom stats: {e}")

    # Keep only the 50 most recent sessions in the summary JSON to avoid bloat
    if "sessions" in result_summary:
        result_summary["sessions"] = result_summary["sessions"][:50]

    # Keep only tasks referenced by the 50 most recent sessions, plus all current workspace tasks to avoid bloat
    if "tasks" in result_summary:
        recent_task_keys = set()
        for session in result_summary.get("sessions", []):
            for t in session.get("tasks", []):
                # Structure of task keys in result_summary['tasks']: f"{session.get('project')}_{t}"
                recent_task_keys.add(f"{session.get('project')}_{t}".lower())
        for tid, proj_val in task_to_project.items():
            if isinstance(proj_val, list):
                for p_item in proj_val:
                    recent_task_keys.add(f"{p_item}_{tid}".lower())
            else:
                recent_task_keys.add(f"{proj_val}_{tid}".lower())
            
        result_summary["tasks"] = {
            k: v for k, v in result_summary["tasks"].items()
            if k.lower() in recent_task_keys
        }

    summary_path = reports_dir / "token_metrics_summary.json"
    summary_path.write_text(json.dumps(result_summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[SUCCESS] Resume consolide ecrit dans {summary_path}")

    write_html_report(result_summary, reports_dir, tdate)
    totals = result_summary.get("totals", {})
    record_metric("tokens", totals.get("tokens", 0), "tokens", {"date": tdate, "clients": list(result_summary.get("clients", {}).keys())})
    record_metric("cache_hits", totals.get("cache_hits", 0), "tokens", {"date": tdate})
    record_metric("cost", totals.get("cost_usd", 0), "usd", {"date": tdate, "models": result_summary.get("model_costs", {}).get("global", {})})
    record_metric("sessions", len(result_summary.get("sessions", [])), "count", {"date": tdate})


if __name__ == "__main__":
    main()
