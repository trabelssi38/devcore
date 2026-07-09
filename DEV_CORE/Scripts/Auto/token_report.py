import argparse
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path


INPUT_TOKEN_PRICE = 0.000003
CACHED_INPUT_TOKEN_PRICE = 0.00000045
OUTPUT_TOKEN_PRICE = 0.000015
ESTIMATED_INPUT_PER_MODEL_TURN = 15000
ESTIMATED_CACHE_RATIO = 0.85


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


def calculate_cost(tokens, cache_hits, output_tokens):
    normal_in = max(tokens - cache_hits - output_tokens, 0)
    return (
        normal_in * INPUT_TOKEN_PRICE
        + cache_hits * CACHED_INPUT_TOKEN_PRICE
        + output_tokens * OUTPUT_TOKEN_PRICE
    )


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
    left["cost_usd"] += calculate_cost(
        int(right.get("tokens", 0)),
        int(right.get("cache_hits", 0)),
        int(right.get("output_tokens", 0)),
    )


def empty_bucket():
    return {"tokens": 0, "cache_hits": 0, "output_tokens": 0, "turns": 0, "cost_usd": 0.0}


def discover_projects(memory_path):
    valid_projects = ["devcore", "cea_dashboard", "job_tracker", "default"]
    task_to_project = {}
    memory_root = Path(memory_path)
    if not memory_root.exists():
        return valid_projects, task_to_project

    for project_dir in memory_root.iterdir():
        if not project_dir.is_dir():
            continue
        name = project_dir.name.lower()
        if name not in ["archive", "patterns", "scores", "default"] and name not in valid_projects:
            valid_projects.append(name)

        tasks_file = project_dir / "tasks.json"
        if not tasks_file.exists():
            continue
        try:
            board = json.loads(tasks_file.read_text(encoding="utf-8"))
            for task in board.get("tasks", []):
                tid = task.get("id")
                if tid:
                    task_to_project[tid.upper()] = name
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
    home = Path(userprofile)
    sources = []

    antigravity_brain = home / ".gemini" / "antigravity" / "brain"
    if antigravity_brain.exists():
        for folder in antigravity_brain.iterdir():
            if not folder.is_dir() or folder.name == "tempmediaStorage":
                continue
            overview = folder / ".system_generated" / "logs" / "overview.txt"
            transcript = folder / ".system_generated" / "logs" / "transcript.jsonl"
            if overview.exists():
                sources.append({"client": "antigravity", "app": "antigravity", "session_id": folder.name, "path": overview})
            elif transcript.exists():
                sources.append({"client": "antigravity", "app": "antigravity", "session_id": folder.name, "path": transcript})

    codex_sessions = home / ".codex" / "sessions"
    if codex_sessions.exists():
        for path in codex_sessions.rglob("*.jsonl"):
            sources.append({"client": "codex", "app": "codex", "session_id": path.stem, "path": path})

    claude_projects = home / ".claude" / "projects"
    if claude_projects.exists():
        for path in claude_projects.rglob("*.jsonl"):
            if "\\subagents\\" in str(path).lower() or "/subagents/" in str(path).lower():
                continue
            sources.append({"client": "claude", "app": "claude-code", "session_id": path.stem, "path": path})

    opencode_home = Path(os.environ.get("OPENCODE_HOME", home / ".config" / "opencode"))
    if opencode_home.exists():
        for path in opencode_home.rglob("*.jsonl"):
            if "node_modules" in [part.lower() for part in path.parts]:
                continue
            sources.append({"client": "opencode", "app": "opencode", "session_id": path.stem, "path": path})

    return sources


def parse_source(source, valid_projects, task_to_project):
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
                mapped_project = task_to_project.get(task_id.upper())
                if mapped_project:
                    detected_project = mapped_project

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
            model_turns += usage["turns"]
            targets = task_ids or ([current_task] if current_task else ["Sans tache"])
            share = max(len(targets), 1)
            for task_id in targets:
                if task_id not in task_tokens:
                    task_tokens[task_id] = {"tokens": 0, "cache_hits": 0, "output_tokens": 0, "turns": 0}
                task_tokens[task_id]["tokens"] += usage["tokens"] // share
                task_tokens[task_id]["cache_hits"] += usage["cache_hits"] // share
                task_tokens[task_id]["output_tokens"] += usage["output_tokens"] // share
                task_tokens[task_id]["turns"] += max(usage["turns"] // share, 1)

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
        "_task_tokens": task_tokens,
    }


def aggregate_sessions(sessions):
    totals = {"tokens": 0, "cache_hits": 0, "output_tokens": 0, "duration_seconds": 0, "sessions_count": 0, "cost_usd": 0.0}
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

        project = session["project"]
        if project not in projects_data:
            projects_data[project] = {"tokens": 0, "cache_hits": 0, "output_tokens": 0, "sessions": 0, "cost_usd": 0.0}
        projects_data[project]["tokens"] += session["tokens"]
        projects_data[project]["cache_hits"] += session["cache_hits"]
        projects_data[project]["output_tokens"] += session["output_tokens"]
        projects_data[project]["sessions"] += 1
        projects_data[project]["cost_usd"] += session["cost_usd"]

        client = session["client"]
        if client not in clients_data:
            clients_data[client] = {"tokens": 0, "cache_hits": 0, "output_tokens": 0, "sessions": 0, "cost_usd": 0.0}
        clients_data[client]["tokens"] += session["tokens"]
        clients_data[client]["cache_hits"] += session["cache_hits"]
        clients_data[client]["output_tokens"] += session["output_tokens"]
        clients_data[client]["sessions"] += 1
        clients_data[client]["cost_usd"] += session["cost_usd"]

        for tid, usage in session["_task_tokens"].items():
            task_key = f"{project}_{tid}"
            if task_key not in tasks_data:
                tasks_data[task_key] = {"project": project, "tokens": 0, "cache_hits": 0, "output_tokens": 0, "turns": 0, "cost_usd": 0.0}
            add_usage(tasks_data[task_key], usage)

        public_session = {k: v for k, v in session.items() if not k.startswith("_")}
        public_sessions.append(public_session)

    totals["duration_minutes"] = int(totals.pop("duration_seconds", 0) // 60)
    totals["cost_usd"] = round(totals["cost_usd"], 4)
    for collection in (projects_data, tasks_data, clients_data):
        for values in collection.values():
            values["cost_usd"] = round(values["cost_usd"], 4)

    return {
        "totals": totals,
        "projects": projects_data,
        "clients": clients_data,
        "tasks": tasks_data,
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
    devcore_data = os.environ.get("DEVCORE_DATA_ROOT", r"C:\devcore\DEV_CORE_DATA")
    reports_dir = Path(devcore_data) / "Logs" / "token_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    memory_path = Path(devcore_data) / "Memory"

    valid_projects, task_to_project = discover_projects(memory_path)
    sources = discover_sources(userprofile)
    sessions = []
    for source in sources:
        session = parse_source(source, valid_projects, task_to_project)
        if session:
            sessions.append(session)

    result_summary = aggregate_sessions(sessions)
    summary_path = reports_dir / "token_metrics_summary.json"
    summary_path.write_text(json.dumps(result_summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[SUCCESS] Resume consolide ecrit dans {summary_path}")

    write_html_report(result_summary, reports_dir, tdate)


if __name__ == "__main__":
    main()
