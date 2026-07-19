# gen_dashboard.py -- Python implementation of DEV_CORE Dashboard payload generator
import os
import sys
import json
import socket
import argparse
import subprocess
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

def get_context_composition_html(projects) -> str:
    rows_html = ""
    for p in projects:
        active_tasks = [t for t in p.get("tasks", []) if t.get("status") == "active"]
        if not active_tasks:
            done_tasks = [t for t in p.get("tasks", []) if t.get("status") == "done"]
            if done_tasks:
                active_tasks = [done_tasks[-1]]
        for task in active_tasks:
            query = task.get("title") or task.get("id") or ""
            task_type = task.get("mode") or "devcore"
            rows_html += f"""
        <div class="context-task-card" data-project="{p['name']}" style="background:#1a1d27; border:1px solid #2d3148; border-radius:6px; padding:10px; margin-bottom:8px;">
          <div style="display:flex; justify-content:space-between; gap:8px; align-items:center;">
            <div style="min-width:0;">
              <div style="font-size:11px; color:#f8fafc; font-weight:600; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{p['name']} / {task['id']}</div>
              <div style="font-size:9px; color:#64748b; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="{query}">{query}</div>
            </div>
            <span style="font-size:9px; color:#cbd5e1; border:1px solid #312e81; border-radius:4px; padding:2px 5px;">{task_type}</span>
          </div>
        </div>
            """
    if not rows_html:
        rows_html = "<div style='font-size:10px; color:#64748b; padding:8px 0;'>Aucune tâche active.</div>"

    return f"""
<div id="context-composition-inner">
  <h2>Composition du Contexte</h2>
  <div style="margin-bottom:6px; font-size:9px; color:#64748b; line-height:1.35;">Sources incluses/exclues pour la tâche active.</div>
  {rows_html}
</div>
"""

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

    # Sort projects — 'devcore' always first, then alphabetical
    projects.sort(key=lambda p: (0 if p["name"] == "devcore" else 1, p["name"]))

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
        <div class="project-row" data-project="{p['name']}" onclick="toggleProjectFilter(this, '{p['name']}')">
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
        tasks_html += f"<details open class='project-tasks-group' data-project='{p['name']}'><summary><h2>Projet : {p['name']}</h2></summary><div style='padding: 10px 0;'>"
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

    # Compute context composition html
    context_composition_html = get_context_composition_html(projects)

    # Load token metrics from headroom_stats.json
    token_activity_html = "<h2>Supervision des Jets de Jetons (Headroom)</h2>"
    stats_json_path = DATA_ROOT / "Metrics" / "headroom_stats.json"
    if stats_json_path.exists():
        try:
            stats_data = json.loads(stats_json_path.read_text(encoding="utf-8"))
            tasks_stats = stats_data.get("tasks", {})
            if tasks_stats:
                token_activity_html += '<table style="width:100%; border-collapse:collapse; font-size:11px; margin-top:8px;">'
                token_activity_html += '<tr style="border-bottom:1px solid #334155; color:#94a3b8; text-align:left;"><th style="padding:4px;">Tâche</th><th style="padding:4px;">Mode</th><th style="padding:4px;">In</th><th style="padding:4px;">Out</th><th style="padding:4px;">Total</th><th style="padding:4px;">Statut</th></tr>'
                
                thresholds = {
                    "coding": 500000,
                    "reasoning": 2000000,
                    "bulk": 1000000
                }
                
                for tid, tinfo in tasks_stats.items():
                    mode = tinfo.get("mode", "coding")
                    t_in = tinfo.get("tokens_in", 0)
                    t_out = tinfo.get("tokens_out", 0)
                    t_total = tinfo.get("total_tokens", 0)
                    limit = thresholds.get(mode, 1000000)
                    
                    status_badge = '<span style="color:#10b981; font-weight:bold;">OK</span>'
                    if t_total > limit:
                        status_badge = '<span style="color:#ef4444; font-weight:bold;">ALERTE</span>'
                        
                    token_activity_html += f'<tr style="border-bottom:1px solid #1e293b; color:#cbd5e1;"><td style="padding:4px; font-weight:bold;">{tid}</td><td style="padding:4px;">{mode}</td><td style="padding:4px;">{t_in:,}</td><td style="padding:4px;">{t_out:,}</td><td style="padding:4px; font-weight:bold;">{t_total:,}</td><td style="padding:4px;">{status_badge}</td></tr>'
                token_activity_html += "</table>"
            else:
                token_activity_html += "<div>Aucune donnée de supervision enregistrée.</div>"
        except Exception as e:
            token_activity_html += f"<div>Erreur de lecture de la supervision: {e}</div>"
    else:
        token_activity_html += "<div>Aucune donnée de supervision (Headroom inactif ou pas encore d'appels).</div>"

    # Load recent alerts from alerts.log
    alerts_html = "<h2>Alerte de Consommation & Événements</h2>"
    alerts_path = DATA_ROOT / "Logs" / "scripts" / "alerts.log"
    alerts_list = []
    if alerts_path.exists():
        try:
            with open(alerts_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                # Get last 5 alerts, reversed to show most recent first
                alerts_list = [l.strip() for l in lines if l.strip()][-5:]
                alerts_list.reverse()
        except Exception:
            pass
            
    if alerts_list:
        for alert in alerts_list:
            alerts_html += f"""
            <div style="padding:6px; margin-bottom:4px; background-color:rgba(239,68,68,0.1); border-left:3px solid #ef4444; border-radius:3px; font-size:10.5px; color:#fca5a5;">
              {alert}
            </div>
            """
    else:
        alerts_html += "<div style='color:#64748b; font-size:11px;'>Aucune alerte de budget déclenchée. Tous les agents respectent les quotas.</div>"

    # Protocol Compliance section
    protocol_html = "<h2>Conformité Protocole Agent</h2>"
    ephemeral_path = DATA_ROOT / "Runtime" / "ephemeral_session.json"
    violations_path = DATA_ROOT / "Logs" / "scripts" / "protocol_violations.log"
    
    status_color = "#22c55e"
    status_label = "🟢 CONFORME"
    ephemeral_text = "Aucune session éphémère active."
    
    if ephemeral_path.exists():
        try:
            eph_data = json.loads(ephemeral_path.read_text(encoding="utf-8"))
            sid = eph_data.get("session_id", "EPH-?")
            vcount = eph_data.get("violation_count", 0)
            status_color = "#eab308"
            status_label = "🟡 SESSION ÉPHÉMÈRE ACTIVE"
            ephemeral_text = f"Session {sid} en cours — {vcount} requêtes sans tâche active."
        except Exception:
            pass
            
    v_count_24h = 0
    if violations_path.exists():
        try:
            v_lines = violations_path.read_text(encoding="utf-8").strip().splitlines()
            v_count_24h = len(v_lines)
            if v_count_24h > 10 and not ephemeral_path.exists():
                status_color = "#ef4444"
                status_label = "🔴 VIOLATIONS RÉPÉTÉES"
        except Exception:
            pass
            
    protocol_html += f"""
    <div style="padding:8px; background:#1a1d27; border:1px solid #2d3148; border-radius:6px; font-size:11px;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
        <span style="font-weight:600; color:{status_color};">{status_label}</span>
        <span style="font-size:10px; color:#94a3b8;">Violations totales: {v_count_24h}</span>
      </div>
      <div style="color:#cbd5e1; font-size:10.5px;">{ephemeral_text}</div>
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
            "token_activity_report": token_activity_html,
            "context_composition": context_composition_html,
            "metrics_service_summary": f"<div>Events count: {len(events)}</div>",
            "event_bus_recent": alerts_html + "<div style='margin-top:12px;'></div>" + protocol_html,
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

    token_activity_html = ""
    context_composition_html = get_context_composition_html(projects)
    alerts_html = ""

    # Render template.html -> index.html
    template_file = PLATFORM_ROOT / "Dashboard" / "template.html"
    output_file = PLATFORM_ROOT / "Dashboard" / "index.html"
    if template_file.exists():
        try:
            template = template_file.read_text(encoding="utf-8")
            template = template.replace('{{PROJECT_CARDS}}', cards_html)
            template = template.replace('{{TASKS_PIPELINE}}', tasks_html)
            template = template.replace('{{SERVICES_MONITORING}}', services_html)
            template = template.replace('{{AUTOMATION_HOOKS}}', "")
            template = template.replace('{{TOKEN_ACTIVITY_REPORT}}', token_activity_html)
            template = template.replace('{{CONTEXT_COMPOSITION}}', context_composition_html)
            template = template.replace('{{METRICS_SERVICE_SUMMARY}}', f"<div>Events: {len(events)}</div>")
            template = template.replace('{{EVENT_BUS_RECENT}}', alerts_html)
            template = template.replace('{{KNOWLEDGE_GRAPH_SUMMARY}}', f"<div>Nodes: {kg_summary['nodes_count']}</div>")
            template = template.replace('{{PLUGIN_STATUS}}', "<div>Plugins active</div>")
            template = template.replace('{{TASK_DETAILS_MAP}}', json.dumps(task_details))
            template = template.replace('{{TOKEN_METRICS_JSON}}', json.dumps(token_metrics))
            # Ensure version string is up-to-date in generated output
            template = template.replace('DEV_CORE v9.0 Cockpit', 'DEV_CORE v10.0 — Cockpit')
            template = template.replace('DEV_CORE v9.0 —', 'DEV_CORE v10.0 —')
            
            output_file.write_text(template, encoding="utf-8")
            print("[gen_dashboard.py] Dashboard index.html generated successfully.")
        except Exception as e:
            print(f"[gen_dashboard.py] Error generating dashboard: {e}")

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
