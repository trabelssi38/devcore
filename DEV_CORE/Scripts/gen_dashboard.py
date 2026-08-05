# gen_dashboard.py -- Python implementation of DEV_CORE Dashboard payload generator
import os
import sys
import json
import sqlite3
import time

import argparse
import subprocess
import hashlib
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# File-based lock: sérialise les appels concurrents à gen_dashboard.py
# (post-commit hook, task_sync.ps1, repowise_update.py, dashboard_api.py...)
# Utilise O_CREAT | O_EXCL pour une création atomique cross-platform (Windows + Linux)
# ---------------------------------------------------------------------------
class DashboardLock:
    """Context manager qui acquiert un lock fichier exclusif avant génération."""
    LOCK_FILENAME = "gen_dashboard.lock"
    WAIT_TIMEOUT  = 30   # secondes max pour attendre la libération du lock
    STALE_TIMEOUT = 120  # secondes après lesquelles un lock est considéré périmé

    def __init__(self):
        lock_dir = Path(os.environ.get("DEVCORE_DATA_ROOT",
                        str(Path(__file__).resolve().parents[2] / "DEV_CORE_DATA"))) / "Runtime"
        lock_dir.mkdir(parents=True, exist_ok=True)
        self.lock_path = lock_dir / self.LOCK_FILENAME

    def __enter__(self):
        deadline = time.monotonic() + self.WAIT_TIMEOUT
        while True:
            try:
                # Création exclusive atomique : échoue si le fichier existe déjà
                fd = os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode())
                os.close(fd)
                return self
            except FileExistsError:
                # Vérifie si le lock est périmé (processus mort)
                try:
                    mtime = self.lock_path.stat().st_mtime
                    if time.time() - mtime > self.STALE_TIMEOUT:
                        self.lock_path.unlink(missing_ok=True)
                        continue
                except OSError:
                    pass
                if time.monotonic() >= deadline:
                    print("[gen_dashboard.py] Lock timeout (autre processus toujours actif). Skip.",
                          file=sys.stderr)
                    raise SystemExit(0)
                time.sleep(0.5)

    def __exit__(self, *_):
        try:
            self.lock_path.unlink(missing_ok=True)
        except OSError:
            pass

# Add parent directory to path so we can import from dashboard package
sys.path.append(str(Path(__file__).resolve().parent))

from dashboard.utils import (
    esc_html,
    esc_attr,
    get_task_datetime,
    get_task_id_number,
    get_active_project,
    load_project_paths,
    check_port,
    DATA_ROOT,
    PLATFORM_ROOT
)

from dashboard.data_loader import (
    load_token_metrics,
    load_plugins_registry,
    load_projects_and_tasks
)

from dashboard.html_renderer import (
    get_services_html,
    get_hooks_html,
    get_context_composition_html,
    get_metrics_service_summary_html,
    get_knowledge_graph_summary_html,
    get_plugin_status_html
)

def get_platform_version(platform_root):
    try:
        toml_path = platform_root / "pyproject.toml"
        if toml_path.exists():
            with open(toml_path, "r", encoding="utf-8") as f:
                content = f.read()
            for line in content.splitlines():
                if line.strip().startswith("version"):
                    parts = line.split("=")
                    if len(parts) == 2:
                        return parts[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return "10.2.0"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-Json", "--json", action="store_true")
    parser.add_argument("-SkipTokenRefresh", "--skip-token-refresh", action="store_true")
    args = parser.parse_args()

    # Sérialiser les appels concurrents via lock fichier
    # (en mode --json le lock est ignoré pour ne pas bloquer l'API)
    if not args.json:
        lock = DashboardLock()
        lock.__enter__()
        import atexit
        atexit.register(lock.__exit__, None, None, None)

    # If running in JSON mode, redirect standard prints to stderr to keep stdout completely clean
    original_stdout = sys.stdout
    if args.json:
        sys.stdout = sys.stderr

    generated_at = datetime.now().isoformat()
    memory_dir = DATA_ROOT / "Memory"
    
    # Refresh token metrics unless explicitly skipped
    if not getattr(args, "skip_token_refresh", False):
        try:
            script_dir = Path(__file__).resolve().parent
            token_script = script_dir / "Auto" / "token_report.py"
            if token_script.exists():
                res = subprocess.run([sys.executable, str(token_script)], capture_output=True, text=True, timeout=60)
                if res.returncode != 0:
                    print(f"[WARNING] token_report.py returned code {res.returncode}: {res.stderr}")
        except Exception as err:
            print(f"[WARNING] Error running token_report.py: {err}")

    # Load token metrics, plugins registry, and project tasks
    token_metrics = load_token_metrics(DATA_ROOT)
    plugins_registry = load_plugins_registry(DATA_ROOT)
    projects, task_details = load_projects_and_tasks(DATA_ROOT, PLATFORM_ROOT, token_metrics)

    # Service statuses
    services = {
        "qdrant": check_port("qdrant", 6333),
        "gemini_router": check_port("gemini_router", 20130),
        "dashboard_api": check_port("dashboard_api", 20129),
        "headroom": check_port("headroom", 8787),
        "api": check_port("api", 20131),
        "repowise": check_port("repowise", 7337)
    }

    # Gather recent events from SQLite bus_events table or fallback JSONL files
    events = []
    db_path = DATA_ROOT / "devcore.db"
    if db_path.exists():
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("""
                SELECT id, source, event_type, project, task_id, correlation_id, payload, created_at
                FROM bus_events
                ORDER BY REPLACE(created_at, 'T', ' ') DESC, rowid DESC
                LIMIT 20;
            """)
            rows = cur.fetchall()
            for r in rows:
                try:
                    payload = json.loads(r[6]) if isinstance(r[6], str) else r[6]
                except Exception:
                    payload = r[6]
                events.append({
                    "id": r[0],
                    "source": r[1],
                    "event_type": r[2],
                    "project": r[3],
                    "task_id": r[4],
                    "correlation_id": r[5],
                    "payload": payload,
                    "timestamp": r[7]
                })
            conn.close()
        except Exception as e:
            print(f"[gen_dashboard] Warning reading bus_events from SQLite: {e}", file=sys.stderr)

    events_dir = DATA_ROOT / "Bus" / "events"
    events_jsonl = DATA_ROOT / "Bus" / "events.jsonl"

    if not events and events_jsonl.exists():

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

    # Build backward-compatible HTML blocks for template.html
    # 1. Project Cards
    cards_html = ""
    for p in projects:
        status_cls = "status-ok" if p["progress"] == 100 else ("status-warn" if p["progress"] > 0 else "status-todo")
        if p["active_task"] == "Aucune":
            active_task_html = '<span style="color:#64748b">Aucune</span>'
        else:
            active_task_html = f"<span style='color:#a5b4fc; font-weight:600;'>{esc_html(p['active_task'])}</span> <span style='font-size:9px; color:#64748b;'>({esc_html(p['mode'])})</span>"
            
        tokens_block = ""
        if p.get("tokens"):
            tokens_block = f"<div style='font-size:9px; color:#475569; padding-left:16px; margin-top:2px; font-family:\\'JetBrains Mono\\',monospace;'>{esc_html(p['tokens'])}</div>"
            
        cards_html += f"""
  <div class="project-row" data-project="{esc_attr(p['name'])}" onclick="toggleProjectFilter(this, '{esc_attr(p['name'])}')" title="Cliquer pour filtrer les taches du projet : {esc_attr(p['name'])} | progression : {p['progress']}%">
    <div style="display:flex; flex-direction:column; gap:4px; flex:1; min-width:0; padding-right:12px;">
      <div style="display:flex; align-items:center; gap:8px;">
        <span class="project-dot {status_cls}"></span>
        <span style="font-size:11px; font-weight:600; color:#f8fafc;">{esc_html(p['name'])}</span>
      </div>
      <div style="font-size:9.5px; font-family:'JetBrains Mono',monospace; color:#64748b; padding-left:16px; text-overflow:ellipsis; overflow:hidden; white-space:nowrap;">
        {active_task_html}
      </div>
      {tokens_block}
    </div>
    <div style="display:flex; flex-direction:column; align-items:flex-end; gap:4px; flex-shrink:0;">
      <div style="font-size:11px; font-weight:600; color:#cbd5e1; display:flex; align-items:center; gap:6px;">
        {p['progress']}%
      </div>
      <div style="width:45px; height:3px; background:#1e293b; border-radius:1.5px; overflow:hidden;">
        <div style="width:{p['progress']}%; height:100%; background:linear-gradient(90deg, #6366f1, #a5b4fc); border-radius:1.5px;"></div>
      </div>
    </div>
  </div>
"""

    # Build task_interactions_map
    events_by_task = {}
    commit_msgs_by_task = {}
    sqlite_db_path = DATA_ROOT / "devcore.db"
    if sqlite_db_path.exists():
        try:
            conn = sqlite3.connect(sqlite_db_path)
            cur = conn.cursor()
            rows = cur.execute("SELECT id, event_type, project, task_id, payload, created_at FROM bus_events ORDER BY rowid DESC LIMIT 300").fetchall()
            for r in rows:
                evt_type, proj, t_id, payload_raw, ts = r[1], r[2], r[3], r[4], r[5]
                p_data = {}
                if payload_raw:
                    try:
                        p_data = json.loads(payload_raw) if isinstance(payload_raw, str) else payload_raw
                    except Exception:
                        pass
                if not t_id and isinstance(p_data, dict):
                    t_id = p_data.get("task_id")
                if t_id:
                    t_key = t_id.upper()
                    if t_key not in events_by_task:
                        events_by_task[t_key] = []
                    details_str = (p_data.get("commit_msg") or p_data.get("title") or evt_type) if isinstance(p_data, dict) else str(p_data)
                    events_by_task[t_key].append({
                        "event_type": evt_type,
                        "created_at": ts,
                        "details": details_str
                    })
                    if isinstance(p_data, dict):
                        if p_data.get("commit_msg"):
                            commit_msgs_by_task[p_data["commit_msg"].strip().lower()] = t_key
                        if p_data.get("title"):
                            commit_msgs_by_task[p_data["title"].strip().lower()] = t_key
            conn.close()
        except Exception as e:
            print(f"[gen_dashboard] Warning fetching bus_events for interactions: {e}", file=sys.stderr)

    task_titles_map = {}
    for p in projects:
        for t_item in p.get("tasks", []):
            if t_item.get("title") and t_item.get("id"):
                task_titles_map[t_item["title"].strip().lower()] = t_item["id"].upper()

    git_files_by_task = {}
    try:
        git_out = subprocess.check_output(['git', 'log', '-n', '100', '--name-only', '--oneline'], text=True, cwd=str(PLATFORM_ROOT.parent))
        cur_t = None
        for line in git_out.splitlines():
            line = line.strip()
            if not line: continue
            if re.match(r'^[0-9a-f]{7,40}\s', line):
                parts = line.split(' ', 1)
                subj = parts[1] if len(parts) > 1 else ''
                m = re.search(r'\[?(T-\d+)\]?', subj, re.IGNORECASE)
                if m:
                    cur_t = m.group(1).upper()
                else:
                    cur_t = commit_msgs_by_task.get(subj.strip().lower()) or task_titles_map.get(subj.strip().lower())
            elif cur_t:
                if cur_t not in git_files_by_task: git_files_by_task[cur_t] = []
                if line not in git_files_by_task[cur_t]: git_files_by_task[cur_t].append(line)
    except Exception:
        pass

    task_interactions_map = {}

    # 2. Tasks Pipeline
    tasks_html = ""
    for p in projects:
        from collections import defaultdict
        worktree_groups = defaultdict(list)
        
        project_tasks = p["tasks"]
        active_t = [t for t in project_tasks if t.get("status") in ["active", "in_progress", "todo", "paused"]]
        completed_t = [t for t in project_tasks if t.get("status") not in ["active", "in_progress", "todo", "paused"]]
        completed_t.sort(key=lambda t: (get_task_datetime(t), get_task_id_number(t)), reverse=True)
        bounded_tasks = active_t + completed_t[:20]
        
        for t in bounded_tasks:
            wt = t.get("worktree") or "main"
            worktree_groups[wt].append(t)
            
        for wt in worktree_groups:
            worktree_groups[wt].sort(key=lambda t: (get_task_datetime(t), get_task_id_number(t)), reverse=True)
            
        sorted_worktrees = sorted(
            worktree_groups.keys(),
            key=lambda wt: max((get_task_datetime(t), get_task_id_number(t)) for t in worktree_groups[wt]),
            reverse=True
        )


        tasks_html += f"<details open class='project-tasks-group' data-project='{esc_attr(p['name'])}'><summary><h2 style='color:#6366f1; cursor:pointer; padding:5px; background:#1a1d27; border-radius:4px;'>Projet : {esc_html(p['name'])}</h2></summary><div style='padding: 10px 0;'>\n"
        
        for wt in sorted_worktrees:
            tasks_html += f"<details open style='margin-left: 15px; margin-bottom: 10px; border-left: 2px solid #2d3148; padding-left: 12px;'><summary><h3 style='font-size:11px; color:#94a3b8; margin-bottom:8px;'>Worktree: {esc_html(wt)}</h3></summary>\n"
            for t in worktree_groups[wt]:
                p_name = p["name"]
                t_id = t.get("id", "")
                t_status = t.get("status", "")
                
                badge_class = "done" if t_status == "done" else ("active" if t_status == "active" else "todo")
                badge_text = t_status.upper()
                active_class = "active-task" if t_status == "active" else ""
                steps_str = f"{t.get('steps_done', 0)}/{t.get('steps_total', 1)} steps" if t.get("steps_total", 0) > 1 else ""
                
                # Task tokens and costs
                task_tokens_str = ""
                task_cost_str = ""
                task_key = f"{p_name}_{t_id}"
                task_stats = None
                if token_metrics and "tasks" in token_metrics:
                    tasks_stats_dict = token_metrics["tasks"]
                    lower_dict = {k.lower(): v for k, v in tasks_stats_dict.items()}
                    
                    if task_key in tasks_stats_dict:
                        task_stats = tasks_stats_dict[task_key]
                    elif task_key.lower() in lower_dict:
                        task_stats = lower_dict[task_key.lower()]
                    elif t_id in tasks_stats_dict:
                        task_stats = tasks_stats_dict[t_id]
                    elif t_id.lower() in lower_dict:
                        task_stats = lower_dict[t_id.lower()]
                    else:
                        if t_id.upper().startswith("T-"):
                            try:
                                num = int(t_id[2:])
                                alt_ids = [f"T-{num}", f"T-{num:02d}"]
                                for alt_id in alt_ids:
                                    alt_key = f"{p_name}_{alt_id}".lower()
                                    if alt_key in lower_dict:
                                        task_stats = lower_dict[alt_key]
                                        break
                                    elif alt_id.lower() in lower_dict:
                                        task_stats = lower_dict[alt_id.lower()]
                                        break
                            except ValueError:
                                pass
                
                if task_stats:
                    try:
                        t_tokens = float(task_stats.get("tokens", 0))
                        t_tokens_str = f"{round(t_tokens/1000000, 2)}M" if t_tokens > 1000000 else f"{round(t_tokens/100, 1) if t_tokens > 0 else 0}K"
                        # Make it use correct rounding
                        if t_tokens > 1000000:
                            t_tokens_str = f"{round(t_tokens/1000000, 2)}M"
                        else:
                            t_tokens_str = f"{round(t_tokens/1000, 1)}K"
                        t_cost = float(task_stats.get("cost_usd", 0))
                        task_tokens_str = f"<span class='badge' style='background:rgba(99, 102, 241, 0.12); border:1px solid rgba(99, 102, 241, 0.25); color:#cbd5e1; margin-left:6px; font-family:monospace; font-size:9px; font-weight:400; padding:1px 4px;' title='Tokens consommés par l\\'agent'>{t_tokens_str}</span>"
                        task_cost_str = f"<span class='badge' style='background:rgba(251, 191, 36, 0.12); border:1px solid rgba(251, 191, 36, 0.25); color:#fde68a; margin-left:4px; font-family:monospace; font-size:9px; font-weight:400; padding:1px 4px;' title='Coût estimé (USD)'>${t_cost:.2f}</span>"
                    except Exception:
                        pass

                details_button = ""
                if t.get("details"):
                    details_button = f"<button class='btn-action btn-details' onclick='showDetails(\"{esc_attr(p_name)}\", \"{esc_attr(t_id)}\", \"{esc_attr(t_status)}\", this, event)' title='Voir les détails'>Détails</button>"

                interactions_button = f"<button class='btn-action btn-interactions' onclick='showInteractions(\"{esc_attr(p_name)}\", \"{esc_attr(t_id)}\", this, event)' style='background:rgba(56,189,248,0.12); color:#38bdf8; border:1px solid rgba(56,189,248,0.3); padding:2px 8px; border-radius:4px; font-size:10px; font-weight:600; cursor:pointer; margin-left:4px;' title='Voir les interactions et modules touchés par l\\'IDE/Agent'>Inter.</button>"

                # Populate task_interactions_map
                t_tok = float(task_stats.get("tokens", 0)) if task_stats else 0
                t_hit = float(task_stats.get("cache_hits", 0)) if task_stats else 0
                t_out = float(task_stats.get("output_tokens", 0)) if task_stats else 0
                t_cst = float(task_stats.get("cost_usd", 0)) if task_stats else 0
                c_pct = round((t_hit / max(1.0, t_tok)) * 100, 1)

                files_list = git_files_by_task.get(t_id.upper(), [])
                
                # Deduce system modules & subsystems interacted with
                modules_set = set()
                for f in files_list:
                    f_lower = f.lower()
                    if "dashboard" in f_lower or "template" in f_lower or "cockpit" in f_lower:
                        modules_set.add("🎛️ Cockpit & UI Engine")
                    if "runner" in f_lower or "hermes" in f_lower or "process" in f_lower:
                        modules_set.add("⚡ AgentRunner Abstraction")
                    if "memory" in f_lower or "qdrant" in f_lower or "dashboard_api" in f_lower:
                        modules_set.add("🧠 AsyncIO Memory & Qdrant Search")
                    if "repowise" in f_lower or "health" in f_lower:
                        modules_set.add("🔍 Repowise Code Health Radar")
                    if "docs" in f_lower or "readme" in f_lower or "changelog" in f_lower or "guide" in f_lower:
                        modules_set.add("📚 Technical Documentation Subsystem")
                    if "hooks" in f_lower or "commit" in f_lower or "session" in f_lower:
                        modules_set.add("⚓ Git Hooks & Session Manager")
                    if "test" in f_lower or "pytest" in f_lower:
                        modules_set.add("🧪 Native Test Suite")

                if not modules_set:
                    modules_set.add("🧠 Context & Memory Subsystem")
                    modules_set.add("🔒 Vault & Configuration System")

                if t_hit > 0:
                    modules_set.add("🛡️ Headroom LLM Proxy & Prompt Cache")

                task_interactions_map[task_key] = {
                    "task_id": t_id,
                    "project": p_name,
                    "title": t.get("title", ""),
                    "status": t.get("status", ""),
                    "mode": t.get("mode", "coding"),
                    "files": files_list,
                    "modules": sorted(list(modules_set)),
                    "metrics": {
                        "tokens": int(t_tok),
                        "cache_hits": int(t_hit),
                        "output_tokens": int(t_out),
                        "cost_usd": round(t_cst, 4),
                        "cache_hit_pct": c_pct
                    },
                    "events": events_by_task.get(t_id.upper(), [])
                }

                steps_detail_html = ""
                # Desactiver l'affichage inline des etapes dans la carte de tâche
                # if t.get("steps"):
                #     steps_detail_html = "<div class='steps-container'>"
                #     for s in t.get("steps", []):
                #         if isinstance(s, dict):
                #             is_done = s.get("done", False)
                #             s_title = s.get("title", "")
                #         else:
                #             is_done = False
                #             s_title = str(s)
                #         icon = "<b style='color:#22c55e'>[v]</b>" if is_done else "<span style='color:#475569'>[ ]</span>"
                #         step_class = "step-done" if is_done else ""
                #         steps_detail_html += f"<div class='step-item {step_class}'>{icon} {esc_html(s_title)}</div>"
                #     steps_detail_html += "</div>"

                task_date_val = get_task_datetime(t)
                if task_date_val != datetime.min:
                    task_date = task_date_val.strftime("%Y-%m-%dT%H:%M:%S")
                else:
                    task_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

                dates_html = ""
                date_items = []
                if t.get("committed_at"):
                    date_items.append(f"Commit: {esc_html(t['committed_at'])}")
                if t.get("started_at"):
                    date_items.append(f"Debut: {esc_html(t['started_at'])}")
                if t.get("completed_at"):
                    date_items.append(f"Fin: {esc_html(t['completed_at'])}")
                if date_items:
                    dates_html = f"<div style='font-size:9px;color:#475569;margin-top:2px;font-family:monospace'>{' | '.join(date_items)}</div>"

                done_button = ""
                if t_status != "done":
                    done_button = f"<button class='btn-action btn-done' title='Clôturer' onclick='completeTask(\"{esc_attr(p_name)}\", \"{esc_attr(t_id)}\", event)'>&#10004;</button>"
                delete_button = f"<button class='btn-action btn-delete' title='Supprimer' onclick='deleteTask(\"{esc_attr(p_name)}\", \"{esc_attr(t_id)}\", event)'>&#128465;</button>"

                if t_id.startswith("T-GIT-"):
                    short_hash = t_id.replace("T-GIT-", "").lower()
                    title_html = f"<span class='badge' style='background:rgba(99,102,241,0.15); border:1px solid rgba(99,102,241,0.3); color:#a5b4fc; font-family:monospace; font-size:9.5px; font-weight:600; margin-right:4px;' title='Commit Git {short_hash}'>git:{short_hash}</span> {esc_html(t.get('title', ''))}"
                else:
                    title_html = f"{esc_html(t_id)}: {esc_html(t.get('title', ''))}"

                tasks_html += f"""
            <div class="mission {active_class} {badge_class}" data-date="{task_date}">
              <div class="mission-header" style="display:flex; gap:10px; align-items:center; width:100%">
                <span class="badge {badge_class}">{badge_text}</span>
                <div style="flex:1; min-width: 0;">
                  <div class="mission-title" style="display:flex; justify-content:space-between; align-items:center; width:100%;">
                    <span style="text-overflow:ellipsis; overflow:hidden; white-space:nowrap;" title="{esc_attr(t_id)}: {esc_attr(t.get('title', ''))}">{title_html}</span>
                    <div style="display:flex; flex-direction:column; align-items:flex-end; gap:4px; flex-shrink:0;">
                      <div style="display:flex; align-items:center; gap:2px;">{task_tokens_str}{task_cost_str}{details_button}{interactions_button}</div>
                      <div style="display:flex; align-items:center; gap:2px;">{done_button}{delete_button}</div>
                    </div>
                  </div>
                  <div style="font-size:10px;color:#64748b;margin-top:2px">Mode: {esc_html(t.get('mode', 'N/A'))} - {steps_str}</div>
                  {dates_html}
                </div>
              </div>
              {steps_detail_html}
            </div>
            """
            tasks_html += "</details>\n"
        tasks_html += "</div></details>"

    services_html = get_services_html(projects, token_metrics)
    hooks_html = get_hooks_html()
    metrics_service_summary_html = get_metrics_service_summary_html()
    knowledge_graph_summary_html = get_knowledge_graph_summary_html()
    plugin_status_html = get_plugin_status_html()
    context_composition_html = get_context_composition_html(projects)

    # Load token metrics and build the rich Rapport de Consommation & Activité Agent
    token_activity_html = ""
    if token_metrics:
        try:
            totals = token_metrics.get("totals", {})
            tot_tokens = float(totals.get("tokens", 0))
            tot_cache = float(totals.get("cache_hits", 0))
            tot_cost = float(totals.get("cost_usd", 0))
            
            if tot_tokens > 1000000:
                tot_tokens_str = f"{round(tot_tokens/1000000, 2)}M"
            else:
                tot_tokens_str = f"{round(tot_tokens/1000, 1)}K"
                
            tot_cache_pct = int(round((tot_cache / tot_tokens) * 100)) if tot_tokens > 0 else 0
            
            # Project allocation bar
            project_alloc_html = ""
            projects_data = token_metrics.get("projects", {})
            if projects_data:
                excluded_projects = ["scripts"]
                proj_list = [(k, v) for k, v in projects_data.items() if k not in excluded_projects]
                visible_token_total = sum(float(proj_val.get("tokens", 0)) for proj_name, proj_val in proj_list)
                project_token_total = visible_token_total if visible_token_total > 0 else tot_tokens
                
                colors = ["#6366f1", "#10b981", "#fbbf24", "#ec4899", "#8b5cf6"]
                
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
            recent_sess = [s for s in sessions_data if s.get("project") not in excluded_projects][-50:]
            recent_sess.reverse()
            if not recent_sess:
                sessions_html = '<div style="font-size: 11px; font-style: italic; color: #64748b; text-align: center; padding: 10px;">Aucune session active enregistrée.</div>'
            else:
                for s in recent_sess:
                    s_tokens = float(s.get("tokens", 0))
                    s_tokens_str = f"{round(s_tokens/1000000, 2)}M" if s_tokens > 1000000 else f"{round(s_tokens/1000, 1)}K"
                    s_cost = float(s.get("cost_usd", 0))
                    s_cache_pct = int(round((float(s.get("cache_hits", 0)) / s_tokens) * 100)) if s_tokens > 0 else 0
                    tasks = s.get("tasks", [])
                    tasks_joined = ", ".join(tasks) if tasks else "Sans tâche (Session Libre)"
                    is_free_session = not tasks or tasks_joined == "Sans tâche" or "Sans tâche" in tasks_joined
                    
                    if is_free_session and (s_tokens > 500000 or s_cost > 0.50):
                        status_badge = '<span style="background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); font-size: 9px; padding: 1px 6px; border-radius: 4px; font-weight: 700; margin-left: 6px;">ALERTE (Hors Tâche)</span>'
                    elif is_free_session:
                        status_badge = '<span style="background: rgba(234, 179, 8, 0.15); color: #facc15; border: 1px solid rgba(234, 179, 8, 0.3); font-size: 9px; padding: 1px 6px; border-radius: 4px; font-weight: 600; margin-left: 6px;">OK (Session Libre)</span>'
                    else:
                        status_badge = '<span style="background: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3); font-size: 9px; padding: 1px 6px; border-radius: 4px; font-weight: 600; margin-left: 6px;">OK</span>'
                    
                    sessions_html += f"""
      <div class="session-row" data-project="{s.get('project')}" style="background: rgba(30, 41, 59, 0.2); border: 1px solid rgba(255,255,255,0.03); border-radius: 6px; padding: 8px 12px; display: flex; justify-content: space-between; align-items: center; transition: transform 0.15s ease, opacity 0.15s ease, border-color 0.15s ease; font-size: 11px; margin-bottom: 6px;">
        <div style="flex: 1; min-width: 0; padding-right: 8px;">
          <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
            <span style="font-weight: 700; color: #f8fafc;">Session {esc_html(s.get('id', ''))}</span>
            <span style="background: rgba(99, 102, 241, 0.15); color: #818cf8; font-size: 9px; padding: 1px 6px; border-radius: 10px; font-weight: 600;">{esc_html(s.get('project', ''))}</span>
            {status_badge}
          </div>
          <div style="font-size: 10px; color: #64748b; margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
            Tâches: {esc_html(tasks_joined)}
          </div>
          <div style="font-size: 9px; color: #475569; margin-top: 3px; font-family: 'JetBrains Mono', monospace;">
            Modèle: {esc_html(s.get('model', ''))}
          </div>
        </div>
        <div style="text-align: right; flex-shrink: 0; font-family: 'JetBrains Mono', monospace;">
          <div style="font-weight: 700; color: #fbbf24;">${s_cost:.2f}</div>
          <div style="font-size: 10px; color: #94a3b8; margin-top: 2px;">{s_tokens_str} ({s_cache_pct}% cache)</div>
        </div>
      </div>
"""

            token_activity_html = f"""
<details open style="border: 1px solid #2d3148; border-radius: 8px; background: #111420; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.4); margin-bottom: 10px;">
<summary style="cursor: pointer; padding: 10px 14px; background: #1a1d27; border-bottom: 1px solid #2d3148; display: flex; justify-content: space-between; align-items: center; user-select: none; font-size: 12px;">
  <span style="font-weight: 700; color: #f8fafc; font-size: 12px;">Supervision Headroom &middot; Rapport de Consommation &amp; Activit&eacute; Agent</span>
  <span id="token-report-header-cost" style="font-size: 10px; color: #fbbf24; font-family: monospace; font-weight:600;">Coût total : ${tot_cost:.2f} USD</span>
  <span class="headroom-toggle-text" style="font-size: 10px; color: #64748b;"></span>
</summary>
<div id="token-activity-inner" style="padding: 12px 14px;">
  <div style="display:grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap:10px; margin-bottom:14px; text-align:center;">
    <div style="background:rgba(30,41,59,0.5); border:1px solid #334155; border-radius:8px; padding:10px 6px;">
      <div style="font-size:9.5px; color:#94a3b8; font-weight:700; text-transform:uppercase; letter-spacing:0.5px;">Tokens</div>
      <div id="token-report-total-tokens" style="font-size:20px; font-weight:800; color:#cbd5e1; margin:3px 0;">{tot_tokens_str}</div>
      <div id="token-report-cache-hits" style="font-size:9.5px; color:#64748b;">{tot_cache_pct}% cache hit</div>
    </div>
    <div style="background:rgba(30,41,59,0.5); border:1px solid #334155; border-radius:8px; padding:10px 6px;">
      <div style="font-size:9.5px; color:#94a3b8; font-weight:700; text-transform:uppercase; letter-spacing:0.5px;">Co&ucirc;t Estim&eacute;</div>
      <div id="token-report-total-cost" style="font-size:20px; font-weight:800; color:#fbbf24; margin:3px 0;">${tot_cost:.2f}</div>
      <div style="font-size:9.5px; color:#64748b;">USD</div>
    </div>
    <div style="background:rgba(30,41,59,0.5); border:1px solid #334155; border-radius:8px; padding:10px 6px;">
      <div style="font-size:9.5px; color:#94a3b8; font-weight:700; text-transform:uppercase; letter-spacing:0.5px;">Limites</div>
      <div style="font-size:11px; color:#e2e8f0; font-weight:bold; margin-top:8px;">Reasoning: 5M tks</div>
      <div style="font-size:9px; color:#64748b;">Bulk: 15M tks</div>
    </div>
  </div>
  
  <div id="token-report-alloc-container">
    {project_alloc_html}
  </div>
  
  <h3 id="model-cost-title" style="font-size:11px; color:#94a3b8; margin: 12px 0 8px;">R&eacute;partition des Co&ucirc;ts par Mod&egrave;le</h3>
  <div id="token-report-model-costs" style="margin-bottom:16px;">{model_cost_html}</div>
  
  <h3 style="font-size:11px; color:#94a3b8; margin: 12px 0 8px;">Sessions R&eacute;centes</h3>
  <div style="max-height:280px; overflow-y:auto; padding-right:4px;">
    {sessions_html}
  </div>
</div>
</details>
"""
        except Exception as e:
            token_activity_html = f"<div style='font-size:11px; color:#ef4444; padding:8px 0;'>Erreur de lecture de la supervision: {esc_html(str(e))}</div>"
    else:
        token_activity_html = "<div style='font-size:11px; color:#64748b; padding:8px 0;'>Aucune donn&eacute;e de supervision (Headroom inactif ou pas encore d'appels).</div>"

    # Load recent alerts from alerts.log
    alerts_html = "<h2>Alerte de Consommation &amp; &Eacute;v&eacute;nements</h2>"
    alerts_path = DATA_ROOT / "Logs" / "scripts" / "alerts.log"
    alerts_list = []
    if alerts_path.exists():
        try:
            with open(alerts_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                alerts_list = [l.strip() for l in lines if l.strip()][-5:]
                alerts_list.reverse()
        except Exception:
            pass
            
    if alerts_list:
        for alert in alerts_list:
            alerts_html += f"""
            <div style="padding:6px; margin-bottom:4px; background-color:rgba(239,68,68,0.1); border-left:3px solid #ef4444; border-radius:3px; font-size:10.5px; color:#fca5a5;">
              {esc_html(alert)}
            </div>
            """
    else:
        alerts_html += "<div style='color:#64748b; font-size:11px;'>Aucune alerte de budget d&eacute;clench&eacute;e. Tous les agents respectent les quotas.</div>"

    # Protocol Compliance section
    protocol_html = "<h2>Conformit&eacute; Protocole Agent</h2>"
    ephemeral_path = DATA_ROOT / "Runtime" / "ephemeral_session.json"
    violations_path = DATA_ROOT / "Logs" / "scripts" / "protocol_violations.log"
    
    status_color = "#22c55e"
    status_label = "🟢 CONFORME"
    ephemeral_text = "Aucune session &eacute;ph&eacute;m&egrave;re active."
    
    if ephemeral_path.exists():
        try:
            eph_data = json.loads(ephemeral_path.read_text(encoding="utf-8"))
            sid = eph_data.get("session_id", "EPH-?")
            vcount = eph_data.get("violation_count", 0)
            status_color = "#eab308"
            status_label = "🟡 SESSION &Eacute;PH&Eacute;M&Egrave;RE ACTIVE"
            ephemeral_text = f"Session {sid} en cours avec {vcount} requ&ecirc;tes sans t&acirc;che active."
        except Exception:
            pass
            
    v_count_24h = 0
    if violations_path.exists():
        try:
            v_lines = violations_path.read_text(encoding="utf-8").strip().splitlines()
            v_count_24h = len(v_lines)
            if v_count_24h > 10 and not ephemeral_path.exists():
                status_color = "#ef4444"
                status_label = "🔴 VIOLATIONS R&Eacute;P&Eacute;T&Eacute;ES"
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
    event_bus_html = """
<div id="event-bus-inner">
  <h2>Event Bus</h2>
  <div style="display:flex; flex-direction:column; gap:4px; margin-bottom:8px;">
"""
    if events:
        for ev in events[:8]:
            ev_type = ev.get("event_type", ev.get("type", "EVENT"))
            ev_src = ev.get("source", "system")
            task_id_val = ev.get("task_id")
            proj_val = ev.get("project")
            
            if task_id_val:
                badge_html = f'<span class="token-reduction" style="color:#38bdf8; font-weight:600;" title="{esc_attr(ev_src)}">{esc_html(str(task_id_val))}</span>'
            elif proj_val and proj_val != "devcore":
                badge_html = f'<span class="token-reduction" style="color:#a78bfa;" title="{esc_attr(ev_src)}">{esc_html(str(proj_val))}</span>'
            else:
                badge_html = f'<span class="token-reduction" style="color:#64748b; font-size:10px; font-weight:normal;" title="{esc_attr(ev_src)}">system</span>'

            ev_ts = ev.get("timestamp", "")
            time_str = ""
            if ev_ts:
                try:
                    if "T" in ev_ts:
                        time_part = ev_ts.split("T")[1]
                        time_str = time_part[:8]
                    else:
                        time_str = ev_ts[:19]
                except Exception:
                    time_str = ev_ts
            else:
                time_str = "-"
                
            event_bus_html += f'    <div class="token-layer"><span class="token-name">{esc_html(time_str)} {esc_html(ev_type)}</span>{badge_html}</div>\n'
    else:
        event_bus_html += "    <div style='font-size:10px; color:#64748b; padding:8px 0;'>Aucun evenement recent.</div>\n"
    event_bus_html += "  </div>\n</div>"

    # Consolidate payload
    payload = {
        "schema_version": 1,
        "generated_at": generated_at,
        "sections": {
            "project_cards": cards_html,
            "tasks_pipeline": tasks_html,
            "services_monitoring": services_html,
            "automation_hooks": hooks_html,
            "token_activity_report": token_activity_html,
            "context_composition": context_composition_html,
            "metrics_service_summary": metrics_service_summary_html,
            "event_bus_recent": event_bus_html + "<div style='margin-top:12px;'></div>" + alerts_html + "<div style='margin-top:12px;'></div>" + protocol_html,
            "knowledge_graph_summary": knowledge_graph_summary_html,
            "plugin_status": plugin_status_html
        },
        "task_details": task_details,
        "task_interactions": task_interactions_map,
        "token_metrics": token_metrics,
        "projects_raw": projects,
        "services_raw": services,
        "events_raw": events[:10] if events else [],
        "plugins_raw": plugins_registry
    }

    # Save JSON payload cache
    cache_path = DATA_ROOT / "Dashboard" / "dashboard_payload.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload_str = json.dumps(payload, indent=2, ensure_ascii=False)
    try:
        cache_path.write_text(payload_str, encoding="utf-8")
    except Exception as e_cache:
        import time as _time
        _written = False
        for _ in range(3):
            _time.sleep(0.1)
            try:
                cache_path.write_text(payload_str, encoding="utf-8")
                _written = True
                break
            except Exception:
                pass
        if not _written:
            print(f"[gen_dashboard.py] Cache payload write warning: {e_cache}")

    # Save payload hash
    hash_path = DATA_ROOT / "Dashboard" / "payload_hash.txt"
    payload_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
    try:
        hash_path.write_text(payload_hash, encoding="utf-8")
    except Exception:
        pass

    # Render template.html -> index.html
    template_file = PLATFORM_ROOT / "Dashboard" / "template.html"
    output_file = PLATFORM_ROOT / "Dashboard" / "index.html"
    version = get_platform_version(PLATFORM_ROOT)
    if template_file.exists():
        try:
            template = template_file.read_text(encoding="utf-8")
            template = template.replace('{{PROJECT_CARDS}}', cards_html)
            template = template.replace('{{TASKS_PIPELINE}}', tasks_html)
            template = template.replace('{{SERVICES_MONITORING}}', services_html)
            template = template.replace('{{ACTIVE_PROJECT_NAME}}', get_active_project())
            template = template.replace('{{AUTOMATION_HOOKS}}', hooks_html)
            template = template.replace('{{TOKEN_ACTIVITY_REPORT}}', token_activity_html)
            template = template.replace('{{CONTEXT_COMPOSITION}}', context_composition_html)
            template = template.replace('{{METRICS_SERVICE_SUMMARY}}', metrics_service_summary_html)
            template = template.replace('{{EVENT_BUS_RECENT}}', event_bus_html + "<div style='margin-top:12px;'></div>" + alerts_html)
            template = template.replace('{{KNOWLEDGE_GRAPH_SUMMARY}}', knowledge_graph_summary_html)
            template = template.replace('{{PLUGIN_STATUS}}', plugin_status_html)
            template = template.replace('{{TASK_DETAILS_MAP}}', json.dumps(task_details))
            template = template.replace('{{TASK_INTERACTIONS_MAP}}', json.dumps(task_interactions_map))
            template = template.replace('{{TOKEN_METRICS_JSON}}', json.dumps(token_metrics))
            template = template.replace('{{VERSION}}', version)
            legacy_v9 = "DEV_CORE " + "v9.0"
            template = template.replace(legacy_v9 + ' Cockpit', f'DEV_CORE v{version} — Cockpit')
            template = template.replace(legacy_v9 + ' —', f'DEV_CORE v{version} —')

            
            output_file.write_text(template, encoding="utf-8")
            print("[gen_dashboard.py] Dashboard index.html generated successfully.")
        except Exception as e:
            print(f"[gen_dashboard.py] Error generating dashboard: {e}")

    # Render template_terminal.html -> index_terminal.html
    term_template_file = PLATFORM_ROOT / "Dashboard" / "template_terminal.html"
    term_output_file = PLATFORM_ROOT / "Dashboard" / "index_terminal.html"
    if term_template_file.exists():
        try:
            tterm = term_template_file.read_text(encoding="utf-8")
            tterm = tterm.replace('{{PROJECT_CARDS}}', cards_html)
            tterm = tterm.replace('{{TASKS_PIPELINE}}', tasks_html)
            tterm = tterm.replace('{{SERVICES_MONITORING}}', services_html)
            tterm = tterm.replace('{{ACTIVE_PROJECT_NAME}}', get_active_project())
            tterm = tterm.replace('{{AUTOMATION_HOOKS}}', hooks_html)
            tterm = tterm.replace('{{TOKEN_ACTIVITY_REPORT}}', token_activity_html)
            tterm = tterm.replace('{{CONTEXT_COMPOSITION}}', context_composition_html)
            tterm = tterm.replace('{{METRICS_SERVICE_SUMMARY}}', metrics_service_summary_html)
            tterm = tterm.replace('{{EVENT_BUS_RECENT}}', event_bus_html + "<div style='margin-top:12px;'></div>" + alerts_html)
            tterm = tterm.replace('{{KNOWLEDGE_GRAPH_SUMMARY}}', knowledge_graph_summary_html)
            tterm = tterm.replace('{{PLUGIN_STATUS}}', plugin_status_html)
            tterm = tterm.replace('{{TASK_DETAILS_MAP}}', json.dumps(task_details))
            tterm = tterm.replace('{{TASK_INTERACTIONS_MAP}}', json.dumps(task_interactions_map))
            tterm = tterm.replace('{{TOKEN_METRICS_JSON}}', json.dumps(token_metrics))
            tterm = tterm.replace('{{VERSION}}', version)
            term_output_file.write_text(tterm, encoding="utf-8")
            print("[gen_dashboard.py] Terminal index_terminal.html generated successfully.")
        except Exception as e:
            print(f"[gen_dashboard.py] Error generating terminal dashboard: {e}")

    if args.json:
        original_stdout.buffer.write(payload_str.encode("utf-8"))
        original_stdout.write("\n")

if __name__ == "__main__":
    main()
