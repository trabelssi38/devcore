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

SERVICE_HOSTS = {
    "qdrant": os.environ.get("QDRANT_HOST", "127.0.0.1"),
    "gemini_router": os.environ.get("GEMINI_ROUTER_HOST", "127.0.0.1"),
    "dashboard_api": os.environ.get("DASHBOARD_API_HOST", "127.0.0.1"),
    "headroom": os.environ.get("HEADROOM_HOST", "127.0.0.1"),
    "api": os.environ.get("API_HOST", "127.0.0.1"),
    "repowise": os.environ.get("REPOWISE_HOST", "127.0.0.1"),
}

def check_port(service_name_or_port, port: int = None) -> bool:
    """Check if TCP port is open for given service or host."""
    if isinstance(service_name_or_port, str):
        service_name = service_name_or_port
        target_port = port
    else:
        service_name = "default"
        target_port = service_name_or_port

    host = SERVICE_HOSTS.get(service_name, "127.0.0.1")
    try:
        with socket.create_connection((host, target_port), timeout=0.5):
            return True
    except Exception:
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
        import re
        nums = re.findall(r"\d+", tid)
        if nums:
            try:
                return int("".join(nums))
            except Exception:
                pass
    return 0

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
                    
                    active_task = next((t for t in tasks if t.get("id") == board.get("current_task") and t.get("status") in ["todo", "active", "paused"]), None)
                    if not active_task and tasks:
                        # Fallback to the last task (most recent)
                        active_task = tasks[-1]

                    active_id = active_task.get("id") if active_task else "Aucune"
                    active_mode = active_task.get("mode") if active_task else "N/A"
                    active_steps = f"{active_task.get('steps_done', 0)}/{active_task.get('steps_total', 1)}" if active_task else ""
                    
                    # Keep active/todo tasks, plus the last 20 completed ones (sorted chronologically before slicing)
                    active_tasks = [t for t in tasks if t.get("status") in ["todo", "active", "paused"] or t.get("id") == board.get("current_task")]
                    completed_tasks = [t for t in tasks if t.get("status") == "done" and t.get("id") != board.get("current_task")]
                    completed_tasks.sort(key=lambda t: (get_task_datetime(t), get_task_id_number(t)))
                    limited_tasks = completed_tasks[-20:] + active_tasks
                    # Sort to preserve original order
                    limited_tasks.sort(key=lambda t: tasks.index(t))
                    
                    # Store task details only for the limited tasks
                    for t in limited_tasks:
                        if t.get("details"):
                            task_details[f"{folder.name}_{t.get('id')}"] = t.get("details")
                    
                    projects.append({
                        "name": folder.name,
                        "active_task": active_id,
                        "mode": active_mode,
                        "progress": pct,
                        "steps": active_steps,
                        "tasks": limited_tasks
                    })
                except Exception:
                    pass

    # Sort projects — 'devcore' always first, then alphabetical
    projects.sort(key=lambda p: (0 if p["name"] == "devcore" else 1, p["name"]))

    # Service statuses
    services = {
        "qdrant": check_port("qdrant", 6333),
        "gemini_router": check_port("gemini_router", 20130),
        "dashboard_api": check_port("dashboard_api", 20129),
        "headroom": check_port("headroom", 8787),
        "api": check_port("api", 20131),
        "repowise": check_port("repowise", 7337)
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

    # Gather recent events from Event Bus JSONL files
    events = []
    events_dir = DATA_ROOT / "Bus" / "events"
    events_jsonl = DATA_ROOT / "Bus" / "events.jsonl"

    if events_jsonl.exists():
        try:
            with open(events_jsonl, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in reversed(lines[-20:]):
                    if line.strip():
                        try:
                            events.append(json.loads(line.strip()))
                        except Exception:
                            pass
        except Exception:
            pass

    if not events and events_dir.exists():
        try:
            # Glob all events-*.jsonl files and sort by name in reverse (most recent first)
            jsonl_files = sorted(events_dir.glob("events-*.jsonl"), key=lambda f: f.name, reverse=True)
            for f in jsonl_files:
                if len(events) >= 20:
                    break
                try:
                    lines = f.read_text(encoding="utf-8").splitlines()
                    for line in reversed(lines):
                        if line.strip():
                            try:
                                events.append(json.loads(line.strip()))
                                if len(events) >= 20:
                                    break
                            except Exception:
                                pass
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
        # Group tasks by worktree
        from collections import defaultdict
        worktree_groups = defaultdict(list)
        for t in p["tasks"]:
            wt = t.get("worktree") or "main"
            worktree_groups[wt].append(t)
            
        # Sort each group's tasks by date and id in descending order
        for wt in worktree_groups:
            worktree_groups[wt].sort(key=lambda t: (get_task_datetime(t), get_task_id_number(t)), reverse=True)
            
        # Get sorted worktree names based on the maximum task in each group
        sorted_worktrees = sorted(
            worktree_groups.keys(),
            key=lambda wt: max((get_task_datetime(t), get_task_id_number(t)) for t in worktree_groups[wt]),
            reverse=True
        )

        tasks_html += f"<details open class='project-tasks-group' data-project='{p['name']}'><summary><h2 style='color:#6366f1; cursor:pointer; padding:5px; background:#1a1d27; border-radius:4px;'>Projet : {p['name']}</h2></summary><div style='padding: 10px 0;'>\n"
        
        for wt in sorted_worktrees:
            tasks_html += f"<details open style='margin-left: 15px; margin-bottom: 10px; border-left: 2px solid #2d3148; padding-left: 12px;'><summary><h3 style='font-size:11px; color:#94a3b8; margin-bottom:8px;'>Worktree: {wt}</h3></summary>\n"
            for t in worktree_groups[wt]:
                p_name = p["name"]
                t_id = t.get("id", "")
                t_status = t.get("status", "")
                
                badge_class = "done" if t_status == "done" else ("active" if t_status == "active" else "todo")
                badge_text = t_status.upper()
                active_class = "active-task" if t_status == "active" else ""
                steps_str = f"{t.get('steps_done', 0)}/{t.get('steps_total', 1)} steps" if t.get("steps_total", 0) > 1 else ""
                
                # Badges de tokens et coûts pour la tâche
                task_tokens_str = ""
                task_cost_str = ""
                task_key = f"{p_name}_{t_id}"
                task_stats = None
                if token_metrics and "tasks" in token_metrics:
                    tasks_stats_dict = token_metrics["tasks"]
                    if task_key in tasks_stats_dict:
                        task_stats = tasks_stats_dict[task_key]
                    elif t_id in tasks_stats_dict:
                        task_stats = tasks_stats_dict[t_id]
                
                if task_stats:
                    try:
                        t_tokens = float(task_stats.get("tokens", 0))
                        if t_tokens > 1000000:
                            t_tokens_str = f"{round(t_tokens/1000000, 2)}M"
                        else:
                            t_tokens_str = f"{round(t_tokens/1000, 1)}K"
                        t_cost = float(task_stats.get("cost_usd", 0))
                        t_cost_formatted = f"{t_cost:.2f}"
                        task_tokens_str = f"<span class='badge' style='background:rgba(99, 102, 241, 0.12); border:1px solid rgba(99, 102, 241, 0.25); color:#cbd5e1; margin-left:6px; font-family:monospace; font-size:9px; font-weight:400; padding:1px 4px;' title='Tokens consommés par l\\'agent'>{t_tokens_str}</span>"
                        task_cost_str = f"<span class='badge' style='background:rgba(251, 191, 36, 0.12); border:1px solid rgba(251, 191, 36, 0.25); color:#fde68a; margin-left:4px; font-family:monospace; font-size:9px; font-weight:400; padding:1px 4px;' title='Coût estimé (USD)'>${t_cost_formatted}</span>"
                    except Exception:
                        pass

                # Gestion du bouton Détails
                details_button = ""
                if t.get("details"):
                    details_button = f"<button class='btn-action btn-details' onclick='showDetails(\"{p_name}\", \"{t_id}\", \"{t_status}\", this, event)' title='Voir les détails'>Détails</button>"

                # Gestion des étapes détaillées
                steps_detail_html = ""
                if t.get("steps"):
                    steps_detail_html = "<div class='steps-container'>"
                    for s in t.get("steps", []):
                        if isinstance(s, dict):
                            is_done = s.get("done", False)
                            s_title = s.get("title", "")
                        else:
                            is_done = False
                            s_title = str(s)
                        icon = "<b style='color:#22c55e'>[v]</b>" if is_done else "<span style='color:#475569'>[ ]</span>"
                        step_class = "step-done" if is_done else ""
                        steps_detail_html += f"<div class='step-item {step_class}'>{icon} {s_title}</div>"
                    steps_detail_html += "</div>"

                # Date de la tâche pour filtrage JS
                task_date_val = get_task_datetime(t)
                if task_date_val != datetime.min:
                    task_date = task_date_val.strftime("%Y-%m-%dT%H:%M:%S")
                else:
                    task_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

                # Formatage des dates pour l'affichage
                dates_html = ""
                date_items = []
                if t.get("committed_at"):
                    date_items.append(f"Commit: {t['committed_at']}")
                if t.get("started_at"):
                    date_items.append(f"Debut: {t['started_at']}")
                if t.get("completed_at"):
                    date_items.append(f"Fin: {t['completed_at']}")
                if date_items:
                    dates_html = f"<div style='font-size:9px;color:#475569;margin-top:2px;font-family:monospace'>{' | '.join(date_items)}</div>"

                # Boutons Clôturer / Supprimer
                done_button = ""
                if t_status != "done":
                    done_button = f"<button class='btn-action btn-done' title='Clôturer' onclick='completeTask(\"{p_name}\", \"{t_id}\")'>&#10004;</button>"
                delete_button = f"<button class='btn-action btn-delete' title='Supprimer' onclick='deleteTask(\"{p_name}\", \"{t_id}\")'>&#128465;</button>"#128465;</button>"

                tasks_html += f"""
            <div class="mission {active_class} {badge_class}" data-date="{task_date}">
              <div class="mission-header" style="display:flex; gap:10px; align-items:center; width:100%">
                <span class="badge {badge_class}">{badge_text}</span>
                <div style="flex:1; min-width: 0;">
                  <div class="mission-title" style="display:flex; justify-content:space-between; align-items:center; width:100%;">
                    <span style="text-overflow:ellipsis; overflow:hidden; white-space:nowrap;" title="{t.get('id')}: {t.get('title')}">{t.get('id')}: {t.get('title')}</span>
                    <div style="display:flex; flex-direction:column; align-items:flex-end; gap:4px; flex-shrink:0;">
                      <div style="display:flex; align-items:center; gap:2px;">{task_tokens_str}{task_cost_str}{details_button}</div>
                      <div style="display:flex; align-items:center; gap:2px;">{done_button}{delete_button}</div>
                    </div>
                  </div>
                  <div style="font-size:10px;color:#64748b;margin-top:2px">Mode: {t.get('mode', 'N/A')} - {steps_str}</div>
                  {dates_html}
                </div>
              </div>
              {steps_detail_html}
            </div>
            """
            tasks_html += "</details>\n"
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

    # Load token metrics and build the rich Rapport de Consommation & Activité Agent
    token_activity_html = ""
    if token_metrics:
        try:
            totals = token_metrics.get("totals", {})
            tot_tokens = float(totals.get("tokens", 0))
            tot_cache = float(totals.get("cache_hits", 0))
            tot_cost = float(totals.get("cost_usd", 0))
            tot_cost_formatted = f"{tot_cost:.2f}"
            
            if tot_tokens > 1000000:
                tot_tokens_str = f"{round(tot_tokens/1000000, 2)}M"
            else:
                tot_tokens_str = f"{round(tot_tokens/1000, 1)}K"
                
            tot_cache_pct = int(round((tot_cache / tot_tokens) * 100)) if tot_tokens > 0 else 0
            
            # Barre de répartition par Projet
            project_alloc_html = ""
            projects_data = token_metrics.get("projects", {})
            if projects_data:
                excluded_projects = ["scripts"]
                proj_list = [(k, v) for k, v in projects_data.items() if k not in excluded_projects]
                visible_token_total = sum(float(proj_val.get("tokens", 0)) for proj_name, proj_val in proj_list)
                project_token_total = visible_token_total if visible_token_total > 0 else tot_tokens
                
                colors = ["#6366f1", "#10b981", "#fbbf24", "#ec4899", "#8b5cf6"]
                
                # Render bar container
                project_alloc_html += '<div class="project-bar-container" style="display:flex; height:6px; border-radius:3px; overflow:hidden; background:#1e293b; margin:12px 0 8px;">'
                idx = 0
                for proj_name, proj_val in proj_list:
                    tokens_val = float(proj_val.get("tokens", 0))
                    pct = int(round((tokens_val / project_token_total) * 100))
                    if pct > 0:
                        col = colors[idx % len(colors)]
                        project_alloc_html += f"<div style='width:{pct}%; background:{col};' title='{proj_name}: {pct}% ({int(tokens_val/1000)}k tks)'></div>"
                        idx += 1
                project_alloc_html += '</div>'
                
                # Render legends
                project_alloc_html += '<div style="display:flex; flex-wrap:wrap; gap:10px; font-size:10px; color:#94a3b8; margin-bottom:16px;">'
                idx = 0
                for proj_name, proj_val in proj_list:
                    tokens_val = float(proj_val.get("tokens", 0))
                    pct = int(round((tokens_val / project_token_total) * 100))
                    if pct > 0:
                        col = colors[idx % len(colors)]
                        project_alloc_html += f"<span style='display:flex; align-items:center; gap:4px;'><span style='width:6px; height:6px; border-radius:50%; background:{col};'></span>{proj_name} ({pct}%)</span>"
                        idx += 1
                project_alloc_html += '</div>'
                
            # Cost by model
            model_cost_html = ""
            global_cost_by_model = None
            model_costs_data = token_metrics.get("model_costs", {})
            if model_costs_data and "global" in model_costs_data:
                global_cost_by_model = model_costs_data["global"]
            elif totals and "cost_by_model" in totals:
                global_cost_by_model = totals["cost_by_model"]
                
            if global_cost_by_model:
                fallback_model_names = []
                if model_costs_data and "unregistered" in model_costs_data:
                    fallback_model_names = [str(m) for m in model_costs_data["unregistered"]]
                elif totals and "unregistered_models" in totals:
                    fallback_model_names = [str(m) for m in totals["unregistered_models"]]
                    
                # Sort models by cost descending
                sorted_models = sorted(global_cost_by_model.items(), key=lambda x: float(x[1]), reverse=True)
                for model_name, model_cost_val in sorted_models[:12]:
                    model_cost_formatted = f"{float(model_cost_val):.2f}"
                    fallback_badge = ""
                    if model_name in fallback_model_names:
                        fallback_badge = "<span style='font-size:8px; color:#f59e0b; border:1px solid rgba(245,158,11,0.35); border-radius:3px; padding:1px 3px; flex-shrink:0;'>fallback</span>"
                    model_cost_html += f"<div class='model-cost-row' style='display:flex; justify-content:space-between; gap:10px; padding:5px 0; border-bottom:1px solid rgba(255,255,255,0.04); font-size:10px;'><span style='color:#cbd5e1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; display:flex; align-items:center; gap:5px;' title='{model_name}'><span style='overflow:hidden; text-overflow:ellipsis; white-space:nowrap;'>{model_name}</span>{fallback_badge}</span><span style='color:#fbbf24; font-family:monospace; flex-shrink:0;'>${model_cost_formatted}</span></div>"
                    
            if not model_cost_html:
                model_cost_html = "<div style='font-size:10px; color:#64748b; padding:6px 0;'>Aucun coût par modèle disponible.</div>"
                
            # Sessions
            sessions_html = ""
            sessions_data = token_metrics.get("sessions", [])
            excluded_projects = ["scripts"]
            recent_sess = [s for s in sessions_data if s.get("project") not in excluded_projects]
            if not recent_sess:
                sessions_html = '<div style="font-size: 11px; font-style: italic; color: #64748b; text-align: center; padding: 10px;">Aucune session active enregistrée.</div>'
            else:
                for s in recent_sess:
                    s_tokens = float(s.get("tokens", 0))
                    if s_tokens > 1000000:
                        s_tokens_str = f"{round(s_tokens/1000000, 2)}M"
                    else:
                        s_tokens_str = f"{round(s_tokens/1000, 1)}K"
                    s_cost = float(s.get("cost_usd", 0))
                    s_cost_formatted = f"{s_cost:.2f}"
                    s_cache_pct = int(round((float(s.get("cache_hits", 0)) / s_tokens) * 100)) if s_tokens > 0 else 0
                    tasks_joined = ", ".join(s.get("tasks", []))
                    
                    sessions_html += f"""
      <div class="session-row" data-project="{s.get('project')}" style="background: rgba(30, 41, 59, 0.2); border: 1px solid rgba(255,255,255,0.03); border-radius: 6px; padding: 8px 12px; display: flex; justify-content: space-between; align-items: center; transition: all 0.2s; font-size: 11px; margin-bottom: 6px;">
        <div style="flex: 1; min-width: 0; padding-right: 8px;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <span style="width: 6px; height: 6px; border-radius: 50%; background: #6366f1; box-shadow: 0 0 6px #6366f1;"></span>
            <span style="font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #cbd5e1; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;" title="{s.get('id')}">{s.get('id')[:8]}...</span>
            <span style="font-size: 9px; padding: 1px 4px; border-radius: 3px; background: rgba(99,102,241,0.2); border: 1px solid rgba(99,102,241,0.3); color: #cbd5e1;">{s.get('project')}</span>
          </div>
          <div style="font-size: 10px; color: #64748b; margin-top: 3px; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">
            {s.get('date')} | {s.get('start_time')} - {s.get('end_time')} ({s.get('duration')})
          </div>
          <div style="font-size: 10px; color: #64748b; margin-top: 2px; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">
            <span style="color:#6366f1">Tâches:</span> {tasks_joined}
          </div>
        </div>
        <div style="text-align: right; font-family: 'JetBrains Mono', monospace; min-width: 80px;">
          <div style="color: #cbd5e1; font-weight: 500;">{s_tokens_str} tks</div>
          <div style="font-size: 9px; color: #64748b; margin-top: 2px;">${s_cost_formatted} | {s_cache_pct}%</div>
        </div>
      </div>
"""
            
            token_activity_html += f"""
<details open style="margin-top: 24px; border: 1px solid #2d3148; border-radius: 8px; background: #111420; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.4);">
  <summary style="padding: 12px 16px; background: #1a1d27; border-bottom: 1px solid #2d3148; cursor: pointer; display: flex; justify-content: space-between; align-items: center; user-select: none;">
    <span style="font-size: 11px; font-weight: 600; text-transform: uppercase; color: #6366f1; letter-spacing: 0.05em; display: flex; align-items: center; gap: 8px;">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
      Rapport de Consommation & Activité Agent
    </span>
    <span id="token-report-header-cost" style="font-size: 11px; color: #cbd5e1; font-family: monospace;">Coût total : ${tot_cost_formatted} USD</span>
  </summary>
  <div style="padding: 16px;">
    <!-- Métriques globales -->
    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 16px;">
      <div style="background: rgba(30, 41, 59, 0.4); border: 1px solid #2d3148; border-radius: 6px; padding: 10px; text-align: center;">
         <div style="font-size: 9px; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em;">Tokens Totaux</div>
         <div id="token-report-total-tokens" style="font-size: 16px; font-weight: 600; color: #f8fafc; font-family: 'JetBrains Mono', monospace; margin-top: 2px;">{tot_tokens_str}</div>
      </div>
      <div style="background: rgba(30, 41, 59, 0.4); border: 1px solid #2d3148; border-radius: 6px; padding: 10px; text-align: center;">
         <div style="font-size: 9px; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em;">Cache Hits</div>
         <div id="token-report-cache-hits" style="font-size: 16px; font-weight: 600; color: #10b981; font-family: 'JetBrains Mono', monospace; margin-top: 2px;">{tot_cache_pct}%</div>
      </div>
      <div style="background: rgba(30, 41, 59, 0.4); border: 1px solid #2d3148; border-radius: 6px; padding: 10px; text-align: center;">
         <div style="font-size: 9px; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em;">Coût Global</div>
         <div id="token-report-total-cost" style="font-size: 16px; font-weight: 600; color: #fbbf24; font-family: 'JetBrains Mono', monospace; margin-top: 2px;">${tot_cost_formatted}</div>
      </div>
    </div>
    
    <div id="token-report-alloc-container">
      <h3 style="font-size: 10px; color: #94a3b8; text-transform: uppercase; margin: 12px 0 6px;">Répartition par Projet</h3>
      {project_alloc_html}
    </div>

    <h3 id="model-cost-title" style="font-size: 10px; color: #94a3b8; text-transform: uppercase; margin: 16px 0 8px;">Coût global par modèle</h3>
    <div id="token-report-model-costs" style="background: rgba(30, 41, 59, 0.25); border: 1px solid #2d3148; border-radius: 6px; padding: 8px 10px; max-height: 180px; overflow-y: auto;">
      {model_cost_html}
    </div>
    
    <h3 style="font-size: 10px; color: #94a3b8; text-transform: uppercase; margin: 16px 0 8px;">Détail des Sessions</h3>
    <div style="display: flex; flex-direction: column; max-height: 250px; overflow-y: auto; padding-right: 4px;">
      {sessions_html}
    </div>
  </div>
</details>
"""
        except Exception as e:
            token_activity_html = f"<div style='font-size:10px; color:#ef4444; padding:8px 0;'>Erreur de génération du rapport de consommation: {e}</div>"
    else:
        token_activity_html = "<div style='font-size:10px; color:#64748b; padding:8px 0;'>Aucun rapport de consommation disponible.</div>"

    # Append Headroom stats
    token_activity_html += "\n<div style='margin-top:20px;'><h2>Supervision des Jets de Jetons (Headroom)</h2>"
    stats_json_path = DATA_ROOT / "Metrics" / "headroom_stats.json"
    if stats_json_path.exists():
        try:
            stats_data = json.loads(stats_json_path.read_text(encoding="utf-8"))
            tasks_stats = stats_data.get("tasks", {})
            if tasks_stats:
                recent_task_ids = list(tasks_stats.keys())[-15:]
                tasks_stats = {k: tasks_stats[k] for k in recent_task_ids}
                
                token_activity_html += '<table style="width:100%; border-collapse:collapse; font-size:11px; margin-top:8px;">'
                token_activity_html += '<tr style="border-bottom:1px solid #334155; color:#94a3b8; text-align:left;"><th style="padding:4px;">Tâche</th><th style="padding:4px;">Mode</th><th style="padding:4px;">In</th><th style="padding:4px;">Out</th><th style="padding:4px;">Total</th><th style="padding:4px;">Statut</th></tr>'
                
                thresholds = {"coding": 500000, "reasoning": 2000000, "bulk": 1000000}
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
    token_activity_html += "</div>"

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

    # Build Event Bus HTML
    event_bus_html = "<h2>Activité Event Bus (Derniers évènements)</h2>"
    if events:
        event_bus_html += "<div style='display:flex; flex-direction:column; gap:4px; margin-top:8px;'>"
        for ev in events[:6]:
            ev_type = ev.get("event_type", ev.get("type", "EVENT"))
            ev_src = ev.get("source", "system")
            ev_ts = ev.get("timestamp", "")[:19].replace("T", " ")
            event_bus_html += f"""
            <div style="padding:6px 8px; background:#1e293b; border-left:3px solid #3b82f6; border-radius:4px; font-size:10px;">
              <div style="display:flex; justify-content:space-between; color:#94a3b8; font-family:monospace;">
                <span>[{ev_type}]</span>
                <span>{ev_ts}</span>
              </div>
              <div style="color:#e2e8f0; margin-top:2px; font-size:10.5px;">Source: {ev_src}</div>
            </div>
            """
        event_bus_html += "</div>"
    else:
        event_bus_html += "<div style='color:#64748b; font-size:11px;'>Aucun événement récent.</div>"

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
            "event_bus_recent": event_bus_html + "<div style='margin-top:12px;'></div>" + alerts_html + "<div style='margin-top:12px;'></div>" + protocol_html,
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
    payload_str = json.dumps(payload, indent=2, ensure_ascii=False)
    cache_path.write_text(payload_str, encoding="utf-8")

    # Save payload hash
    import hashlib
    hash_path = DATA_ROOT / "Dashboard" / "payload_hash.txt"
    payload_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
    try:
        hash_path.write_text(payload_hash, encoding="utf-8")
    except Exception:
        pass

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
            template = template.replace('{{EVENT_BUS_RECENT}}', event_bus_html + "<div style='margin-top:12px;'></div>" + alerts_html)
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
        print(payload_str)

if __name__ == "__main__":
    main()
