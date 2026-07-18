# gen_dashboard.py -- Python implementation of DEV_CORE Dashboard payload generator
import os
import sys
import json
import socket
import argparse
from datetime import datetime
from pathlib import Path

# Load environment or default paths
PLATFORM_ROOT = Path(os.environ.get("DEVCORE_PLATFORM_ROOT", r"C:\devcore\DEV_CORE"))
DATA_ROOT = Path(os.environ.get("DEVCORE_DATA_ROOT", r"C:\devcore\DEV_CORE_DATA"))

def check_port(port: int) -> bool:
    """Check if local TCP port is open."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except Exception:
        return False

def get_active_project() -> str:
    # Use cached env var if present
    cached = os.environ.get("DEVCORE_ACTIVE_PROJECT_NAME")
    if cached:
        return cached
    # Fallback to directory name
    return Path(os.getcwd()).name

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-Json", "--json", action="store_true")
    parser.add_argument("-SkipTokenRefresh", "--skip-token-refresh", action="store_true")
    args = parser.parse_args()

    generated_at = datetime.now().isoformat()
    memory_dir = DATA_ROOT / "Memory"
    
    projects = []
    task_details = {}
    
    if memory_dir.exists():
        for folder in memory_dir.iterdir():
            if not folder.is_dir() or folder.name == "scripts":
                continue
            tasks_file = folder / "tasks.json"
            if tasks_file.exists():
                try:
                    board = json.loads(tasks_file.read_text(encoding="utf-8-sig"))
                    tasks = board.get("tasks", [])
                    total = len(tasks)
                    done = sum(1 for t in tasks if t.get("status") == "done")
                    pct = int((done / total) * 100) if total > 0 else 0
                    
                    active_task = next((t for t in tasks if t.get("id") == board.get("current_task")), None)
                    active_id = active_task.get("id") if active_task else "Aucune"
                    active_mode = active_task.get("mode") if active_task else "N/A"
                    active_steps = f"{active_task.get('steps_done', 0)}/{active_task.get('steps_total', 1)}" if active_task else ""
                    
                    # Store task details
                    for t in tasks:
                        if t.get("details"):
                            task_details[f"{folder.name}_{t.get('id')}"] = t.get("details")
                    
                    projects.append({
                        "name": folder.name,
                        "active_task": active_id,
                        "mode": active_mode,
                        "progress": pct,
                        "steps": active_steps,
                        "tasks": tasks
                    })
                except Exception:
                    pass

    # Sort projects
    projects.sort(key=lambda p: p["name"])

    # Service statuses
    services = {
        "qdrant": check_port(6333),
        "gemini_router": check_port(20130),
        "dashboard_api": check_port(20129),
        "headroom": check_port(8787),
        "api": check_port(20131),
        "repowise": check_port(7337)
    }

    # Load token metrics
    token_metrics = {}
    token_json = DATA_ROOT / "Logs" / "token_reports" / "token_metrics_summary.json"
    if token_json.exists():
        try:
            token_metrics = json.loads(token_json.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Load plugins
    plugins_registry = {}
    plugins_json = DATA_ROOT / "Plugins" / "plugins_registry.json"
    if plugins_json.exists():
        try:
            plugins_registry = json.loads(plugins_json.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Gather recent events
    events = []
    events_dir = DATA_ROOT / "Bus" / "events"
    if events_dir.exists():
        try:
            files = sorted(events_dir.glob("*.json"), key=lambda f: f.name, reverse=True)[:8]
            for f in files:
                try:
                    events.append(json.loads(f.read_text(encoding="utf-8")))
                except Exception:
                    pass
        except Exception:
            pass

    # Knowledge Graph summary
    kg_summary = {"nodes_count": 0, "edges_count": 0}
    kg_json = DATA_ROOT / "Knowledge" / "graph.json"
    if kg_json.exists():
        try:
            kg_data = json.loads(kg_json.read_text(encoding="utf-8"))
            kg_summary["nodes_count"] = kg_data.get("nodes_count", 0)
            kg_summary["edges_count"] = kg_data.get("edges_count", 0)
        except Exception:
            pass

    # Build backward-compatible HTML blocks for template.html
    cards_html = ""
    for p in projects:
        status_cls = "status-ok" if p["progress"] == 100 else ("status-warn" if p["progress"] > 0 else "status-todo")
        cards_html += f"""
        <div class="project-row" data-project="{p['name']}">
          <div style="display:flex; flex-direction:column; gap:4px; flex:1;">
            <div style="display:flex; align-items:center; gap:8px;">
              <span class="project-dot {status_cls}"></span>
              <span style="font-size:11px; font-weight:600; color:#f8fafc;">{p['name']}</span>
            </div>
            <div style="font-size:9.5px; font-family:'JetBrains Mono',monospace; color:#64748b;">
              {p['active_task']} ({p['mode']})
            </div>
          </div>
          <div>{p['progress']}%</div>
        </div>
        """

    tasks_html = ""
    for p in projects:
        tasks_html += f"<details open class='project-tasks-group'><summary><h2>Projet : {p['name']}</h2></summary><div style='padding: 10px 0;'>"
        for t in p["tasks"]:
            badge = "done" if t.get("status") == "done" else ("active" if t.get("status") == "active" else "todo")
            tasks_html += f"""
            <div class="mission {badge}">
              <div class="mission-header">
                <span class="badge {badge}">{t.get('status', '').upper()}</span>
                <span>{t.get('id')}: {t.get('title')}</span>
              </div>
            </div>
            """
        tasks_html += "</div></details>"

    services_html = "<h2>Services & Infrastructure</h2>"
    for name, alive in services.items():
        status_cls = "status-ok" if alive else "status-error"
        status_icon = "&#10003;" if alive else "&#10007;"
        services_html += f"""
        <div class="component">
          <div>
            <div class="component-name">{name.upper()}</div>
            <div class="component-detail">Status check</div>
          </div>
          <div class="{status_cls}">{status_icon}</div>
        </div>
        """

    # Consolidate payload
    payload = {
        "schema_version": 1,
        "generated_at": generated_at,
        "sections": {
            "project_cards": cards_html,
            "tasks_pipeline": tasks_html,
            "services_monitoring": services_html,
            "automation_hooks": "",
            "token_activity_report": "",
            "context_composition": "",
            "metrics_service_summary": f"<div>Events count: {len(events)}</div>",
            "event_bus_recent": "<div>Recent bus activity</div>",
            "knowledge_graph_summary": f"<div>Nodes: {kg_summary['nodes_count']}</div>",
            "plugin_status": f"<div>Active plugins check</div>"
        },
        "task_details": task_details,
        "token_metrics": token_metrics,
        "projects_raw": projects,  # Added structured data for Next.js frontend!
        "services_raw": services,
        "events_raw": events,
        "plugins_raw": plugins_registry
    }

    # Save JSON payload cache
    cache_path = DATA_ROOT / "Dashboard" / "dashboard_payload.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    # Render template.html -> index.html
    template_file = PLATFORM_ROOT / "Dashboard" / "template.html"
    output_file = PLATFORM_ROOT / "Dashboard" / "index.html"
    if template_file.exists():
        try:
            template = template_file.read_text(encoding="utf-8")
            template = template.Replace('{{PROJECT_CARDS}}', cards_html) if hasattr(template, 'Replace') else template.replace('{{PROJECT_CARDS}}', cards_html)
            template = template.replace('{{TASKS_PIPELINE}}', tasks_html)
            template = template.replace('{{SERVICES_MONITORING}}', services_html)
            template = template.replace('{{AUTOMATION_HOOKS}}', "")
            template = template.replace('{{TOKEN_ACTIVITY_REPORT}}', "")
            template = template.replace('{{CONTEXT_COMPOSITION}}', "")
            template = template.replace('{{METRICS_SERVICE_SUMMARY}}', f"<div>Events: {len(events)}</div>")
            template = template.replace('{{EVENT_BUS_RECENT}}', "<div>Recent bus events</div>")
            template = template.replace('{{KNOWLEDGE_GRAPH_SUMMARY}}', f"<div>Nodes: {kg_summary['nodes_count']}</div>")
            template = template.replace('{{PLUGIN_STATUS}}', "<div>Plugins active</div>")
            template = template.replace('{{TASK_DETAILS_MAP}}', json.dumps(task_details))
            template = template.replace('{{TOKEN_METRICS_JSON}}', json.dumps(token_metrics))
            
            output_file.write_text(template, encoding="utf-8")
        except Exception:
            pass

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
