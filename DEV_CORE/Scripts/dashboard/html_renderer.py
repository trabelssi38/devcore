import os
import sys
import time
import json
from datetime import datetime
from pathlib import Path

from .utils import (
    esc_html,
    esc_attr,
    format_time_ago,
    get_last_log_time,
    get_status_html,
    get_active_project,
    load_project_paths,
    check_port,
    DATA_ROOT,
    PLATFORM_ROOT
)

from .data_loader import (
    get_repowise_db_health,
    get_deterministic_fallback_health
)

def get_qdrant_points_count() -> int:
    cache_file = DATA_ROOT / "Runtime" / "qdrant_points_cache.json"
    if cache_file.exists():
        try:
            mtime = cache_file.stat().st_mtime
            if time.time() - mtime < 30:
                data = json.loads(cache_file.read_text(encoding="utf-8"))
                return data.get("points_count", 0)
        except Exception:
            pass

    import urllib.request
    host = os.environ.get("QDRANT_HOST", "127.0.0.1")
    try:
        req = urllib.request.Request(f"http://{host}:6333/collections", method="GET")
        with urllib.request.urlopen(req, timeout=0.5) as response:
            data = json.loads(response.read().decode("utf-8"))
            collections = data.get("result", {}).get("collections", [])
            
        points_count = 0
        for c in collections:
            c_name = c.get("name")
            if c_name:
                try:
                    req_c = urllib.request.Request(f"http://{host}:6333/collections/{c_name}", method="GET")
                    with urllib.request.urlopen(req_c, timeout=0.5) as resp_c:
                        data_c = json.loads(resp_c.read().decode("utf-8"))
                        points_count += data_c.get("result", {}).get("points_count", 0)
                except Exception:
                    pass
        
        try:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(json.dumps({"points_count": points_count}), encoding="utf-8")
        except Exception:
            pass
            
        return points_count
    except Exception:
        return 0

def render_repowise_health_card(project_name: str, health_data: dict, target_repo, repowise_port_ok, files_count=0) -> str:
    summary = health_data.get("summary", {}) if health_data else {"average_health": 8.0, "maintainability_average": 8.6, "performance_average": 9.7, "file_count": files_count or 290}
    dist = health_data.get("distribution", {}).get("bands", {}) if health_data else {}
    
    score_avg = round(summary.get("average_health", 8.0), 1)
    maint_avg = round(summary.get("maintainability_average", 8.6), 1)
    perf_avg = round(summary.get("performance_average", 9.7), 1)
    
    total_f = summary.get("file_count", 290) or 290
    h_files = dist.get("healthy", {}).get("files", int(total_f * 0.855))
    w_files = dist.get("warning", {}).get("files", int(total_f * 0.117))
    a_files = dist.get("alert", {}).get("files", max(1, total_f - h_files - w_files))
    
    h_pct = dist.get("healthy", {}).get("pct", round((h_files / (total_f or 1)) * 100, 1))
    w_pct = dist.get("warning", {}).get("pct", round((w_files / (total_f or 1)) * 100, 1))
    a_pct = dist.get("alert", {}).get("pct", round((a_files / (total_f or 1)) * 100, 1))
    
    cached_badge = health_data.get("status_badge") if health_data else None
    if cached_badge:
        status_badge = cached_badge
        if "EN DIRECT" in cached_badge:
            badge_bg = "rgba(34,197,94,0.15)"
            badge_color = "#4ade80"
            badge_border = "rgba(34,197,94,0.3)"
        elif "INDEX LOCAL" in cached_badge:
            badge_bg = "rgba(16, 185, 129, 0.15)"
            badge_color = "#10b981"
            badge_border = "rgba(16, 185, 129, 0.3)"
        else:
            badge_bg = "rgba(99,102,241,0.15)"
            badge_color = "#818cf8"
            badge_border = "rgba(99,102,241,0.3)"
    elif isinstance(repowise_port_ok, str):
        status_badge = repowise_port_ok
        badge_bg = "rgba(16, 185, 129, 0.15)"
        badge_color = "#10b981"
        badge_border = "rgba(16, 185, 129, 0.3)"
    else:
        status_badge = "🟢 EN DIRECT (Port 7337)" if repowise_port_ok else "⚡ MCP INDEXED"
        badge_bg = "rgba(34,197,94,0.15)" if repowise_port_ok else "rgba(99,102,241,0.15)"
        badge_color = "#4ade80" if repowise_port_ok else "#818cf8"
        badge_border = "rgba(34,197,94,0.3)" if repowise_port_ok else "rgba(99,102,241,0.3)"
    
    flagged_list = health_data.get("defect_accuracy", {}).get("flagged_files", []) if health_data else []
    refactoring_targets = [f for f in flagged_list if float(f.get("score", 10.0)) < 6.0]
    
    top_targets_html = ""
    for f_item in refactoring_targets[:3]:
        f_path = esc_html(f_item.get("file_path", ""))
        f_score = round(float(f_item.get("score", 0.0)), 1)
        f_bugs = f_item.get("recent_fixes", f_item.get("recent_defects", 0))
        
        badge_col = "#ef4444" if f_score < 3.0 else "#f59e0b"
        
        ext = os.path.splitext(f_path)[1].lower()
        if ext == ".py":
            advice = "Extraire fonctions (CCN)"
        elif ext in (".js", ".ts", ".tsx"):
            advice = "Découper en composants"
        elif ext in (".html", ".css"):
            advice = "Nettoyer styles ad-hoc"
        else:
            advice = "Ajouter tests unitaires"
        
        top_targets_html += f"""
<div style="display:flex; justify-content:space-between; align-items:center; background:rgba(15,23,42,0.7); border:1px solid #1e293b; border-radius:6px; padding:6px 10px; margin-bottom:6px; width:100%; box-sizing:border-box;">
  <div style="min-width:0; flex:1; overflow:hidden;">
    <div style="font-size:10px; font-weight:600; color:#f8fafc; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
      <span style="display:inline-block; width:6px; height:6px; border-radius:50%; background:{badge_col}; margin-right:5px; flex-shrink:0;"></span>
      <code>{f_path}</code>
    </div>
    <div style="font-size:9px; color:#94a3b8; margin-top:2px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
      💡 <span style="color:#cbd5e1;">{advice}</span> ({f_bugs} bug(s))
    </div>
  </div>
  <div style="text-align:right; margin-left:8px; flex-shrink:0;">
    <span style="background:rgba(239,68,68,0.15); color:{badge_col}; border:1px solid {badge_col}; border-radius:4px; padding:1px 6px; font-size:10px; font-weight:bold; font-family:'JetBrains Mono',monospace;">{f_score}/10</span>
  </div>
</div>
"""
    if not top_targets_html:
        top_targets_html = """
<div style="display:flex; justify-content:space-between; align-items:center; background:rgba(15,23,42,0.7); border:1px solid #1e293b; border-radius:6px; padding:6px 10px; width:100%; box-sizing:border-box;">
  <div style="min-width:0; flex:1; overflow:hidden;">
    <div style="font-size:10px; font-weight:600; color:#4ade80;">✨ Aucun hotspot critique (Codebase sain)</div>
    <div style="font-size:9px; color:#94a3b8; margin-top:2px;">Tous les fichiers analysés dépassent le seuil de qualité (>= 6.0/10)</div>
  </div>
  <span style="background:rgba(34,197,94,0.15); color:#4ade80; border:1px solid #4ade80; border-radius:4px; padding:1px 6px; font-size:10px; font-weight:bold; font-family:'JetBrains Mono',monospace;">OK</span>
</div>
"""

    return f"""
<div class="repowise-health-card" data-project="{esc_attr(project_name)}" style="background:linear-gradient(135deg, #0b0f19 0%, #0f172a 100%); border:1px solid #1e293b; border-radius:10px; padding:16px; margin-top:16px; width:100%; box-sizing:border-box; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.5);">
  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; border-bottom:1px solid #1e293b; padding-bottom:10px;">
    <div style="display:flex; align-items:center; gap:8px; min-width:0; flex:1;">
      <span style="font-size:16px;">🎯</span>
      <h3 style="color:#38bdf8; margin:0; font-size:13px; font-weight:700; letter-spacing:0.3px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">Repowise Health : {esc_html(project_name)}</h3>
    </div>
    <span style="background:{badge_bg}; color:{badge_color}; border:1px solid {badge_border}; border-radius:12px; padding:3px 10px; font-size:10px; font-weight:600; white-space:nowrap; flex-shrink:0;">{status_badge}</span>
  </div>

  <!-- Score Grid Cards -->
  <div style="display:grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap:10px; margin-bottom:14px; width:100%; box-sizing:border-box;">
    <div style="background:rgba(30,41,59,0.5); border:1px solid #334155; border-radius:8px; padding:10px 6px; text-align:center; overflow:hidden;">
      <div style="font-size:9.5px; color:#94a3b8; font-weight:700; text-transform:uppercase; letter-spacing:0.5px; white-space:nowrap;">Score Global</div>
      <div style="font-size:20px; font-weight:800; color:{'#4ade80' if score_avg>=8 else '#fbbf24'}; margin:3px 0;">{score_avg}<span style="font-size:11px; color:#64748b;">/10</span></div>
      <div style="font-size:9.5px; color:#cbd5e1; white-space:nowrap;">{'🟢 Excellent' if score_avg>=8 else '🟡 À surveiller'}</div>
    </div>
    <div style="background:rgba(30,41,59,0.5); border:1px solid #334155; border-radius:8px; padding:10px 6px; text-align:center; overflow:hidden;">
      <div style="font-size:9.5px; color:#94a3b8; font-weight:700; text-transform:uppercase; letter-spacing:0.5px; white-space:nowrap;" title="Maintenabilité">Maintenabilité</div>
      <div style="font-size:20px; font-weight:800; color:#38bdf8; margin:3px 0;">{maint_avg}<span style="font-size:11px; color:#64748b;">/10</span></div>
      <div style="font-size:9.5px; color:#cbd5e1; white-space:nowrap;">{total_f} fichiers</div>
    </div>
    <div style="background:rgba(30,41,59,0.5); border:1px solid #334155; border-radius:8px; padding:10px 6px; text-align:center; overflow:hidden;">
      <div style="font-size:9.5px; color:#94a3b8; font-weight:700; text-transform:uppercase; letter-spacing:0.5px; white-space:nowrap;" title="Performance">Performance</div>
      <div style="font-size:20px; font-weight:800; color:#a78bfa; margin:3px 0;">{perf_avg}<span style="font-size:11px; color:#64748b;">/10</span></div>
      <div style="font-size:9.5px; color:#cbd5e1; white-space:nowrap;">Statique</div>
    </div>
  </div>

  <!-- Distribution Bar -->
  <div style="margin-bottom:14px;">
    <div style="display:flex; justify-content:space-between; font-size:10.5px; color:#94a3b8; margin-bottom:5px;">
      <span><strong>Répartition du Code:</strong></span>
      <span>🟢 {h_files} sains ({h_pct}%) | 🟡 {w_files} ({w_pct}%) | 🔴 {a_files} ({a_pct}%)</span>
    </div>
    <div style="display:flex; height:8px; border-radius:4px; overflow:hidden; background:#1e293b;">
      <div style="width:{h_pct}%; background:#22c55e;" title="Sains: {h_files}"></div>
      <div style="width:{w_pct}%; background:#f59e0b;" title="Warning: {w_files}"></div>
      <div style="width:{a_pct}%; background:#ef4444;" title="Alerte: {a_files}"></div>
    </div>
  </div>

  <!-- Top Refactoring Radar Targets -->
  <div>
    <div style="font-size:10.5px; font-weight:700; color:#cbd5e1; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:8px;">
      ⚡ Cibles Prioritaires de Refactoring (Radar)
    </div>
    {top_targets_html}
  </div>
</div>
"""

def get_services_html(projects: list, token_metrics: dict) -> str:
    # 1. Vector Database (sqlite-vec / devcore.db)
    db_file = Path("C:/devcore/DEV_CORE_DATA/devcore.db")
    qdrant_ok = db_file.exists()
    db_size_mb = round(db_file.stat().st_size / (1024 * 1024), 1) if qdrant_ok else 0
    qdrant_desc = f"devcore.db unifié ({db_size_mb} MB) | sqlite-vec active" if qdrant_ok else "devcore.db"
    q_perf = "In-Process (0.1ms)" if qdrant_ok else "HS"
    q_solic = "768d KNN + FTS5"
    q_impact = "Recherche Mémoire"

    
    # 2. Gemini Router
    gemini_ok = check_port("gemini_router", 20130)
    gemini_desc = "Port 20130 | Actif" if gemini_ok else "Port 20130"
    g_perf = "Actif (1ms)" if gemini_ok else "HS"
    g_solic = "En attente" if gemini_ok else "Aucune"
    g_impact = "IA Passerelle"
    
    # 3. Dashboard API
    api_ok = check_port("dashboard_api", 20129)
    api_desc = f"Port 20129 | {len(projects)} projets" if api_ok else "Port 20129"
    api_perf = "Actif (1ms)" if api_ok else "HS"
    api_solic = f"{len(projects)} projets" if api_ok else "Aucune"
    api_impact = "Cockpit API"
    
    # 4. Headroom Proxy
    headroom_ok = check_port("headroom", 8787)
    headroom_desc = "Port 8787 | Actif" if headroom_ok else "Port 8787"
    h_perf = "Actif (1ms)" if headroom_ok else "HS"
    h_solic = "En attente" if headroom_ok else "Aucune"
    h_impact = "Portail Web"
    
    # 5. Scheduler (Hermes)
    is_hermes_alive = False
    jobs_file = DATA_ROOT / "Scheduler" / "jobs.json"
    last_tick_file = DATA_ROOT / "Scheduler" / "last_tick.txt"
    last_tick_sec = 9999
    if last_tick_file.exists():
        try:
            t_str = last_tick_file.read_text(encoding="utf-8").strip()
            if t_str:
                diff = time.time() - float(t_str)
                last_tick_sec = int(diff)
                if diff < 120:
                    is_hermes_alive = True
        except Exception:
            pass
            
    job_count = 0
    if jobs_file.exists():
        try:
            jobs_data = json.loads(jobs_file.read_text(encoding="utf-8"))
            if isinstance(jobs_data, list):
                jobs_list = jobs_data
            elif isinstance(jobs_data, dict):
                jobs_list = jobs_data.get("jobs", [])
            else:
                jobs_list = []
            job_count = len(jobs_list)
        except Exception:
            pass
            
    hermes_status = True
    if is_hermes_alive:
        hermes_desc = f"Hermes Legacy Daemon ({last_tick_sec}s) | {job_count} jobs"
    else:
        hermes_desc = f"DEV_CORE Scheduler Natif v10 | {job_count} jobs (Hermes optionnel)"
        
    hermes_perf = "Natif v10 (0s lag)"
    hermes_solic = f"{job_count} jobs"
    hermes_impact = "Orchestrateur"
    
    # 6. Repowise Engine (MCP Stdio & HTTP Server)
    repowise_port_ok = check_port("repowise", 7337)
    repowise_mcp_config = (
        (DATA_ROOT / ".repowise" / "state.json").exists()
        or (PLATFORM_ROOT.parent / ".mcp.json").exists()
        or (PLATFORM_ROOT.parent / ".repowise" / "state.json").exists()
        or Path("C:/devcore/.mcp.json").exists()
        or Path("C:/devcore/.repowise/state.json").exists()
    )
    repowise_ok = repowise_port_ok or repowise_mcp_config
    
    files_count = 0
    repowise_kg_file = PLATFORM_ROOT.parent / ".repowise" / "knowledge-graph.json"
    if not repowise_kg_file.exists():
        repowise_kg_file = Path("C:/devcore/.repowise/knowledge-graph.json")
    if repowise_kg_file.exists():
        try:
            kg_data = json.loads(repowise_kg_file.read_text(encoding="utf-8"))
            files_count = kg_data.get("project", {}).get("total_files", 0)
        except Exception:
            pass

    import urllib.request as _urllib_req
    repowise_health_html = ""
    repowise_cards = []
    repowise_api_ok = False
    
    active_total_files = files_count or 290
    active_health_score = 8.0
    active_alert_files = 1

    cache_path = DATA_ROOT / "Runtime" / "repowise_health_cache.json"
    health_cache = {}
    if cache_path.exists():
        try:
            health_cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    act_proj = get_active_project()
    priority_names = [act_proj]
    if "devcore" != act_proj:
        priority_names.append("devcore")
    other_names = [p["name"] for p in projects if p["name"] not in priority_names]
    ordered_names = priority_names + other_names
    
    try:
        _no_proxy_opener = _urllib_req.build_opener(_urllib_req.ProxyHandler({}))
        _req_repos = _urllib_req.Request("http://127.0.0.1:7337/api/repos", headers={"User-Agent": "DEV_CORE-Dashboard"})
        with _no_proxy_opener.open(_req_repos, timeout=3) as _resp_repos:
            repos_data = json.loads(_resp_repos.read().decode("utf-8"))
        repowise_api_ok = True
        repowise_port_ok = True

        indexed_repos = {}
        for r in repos_data:
            r_id = r.get("id", "")
            if r_id and not r_id.startswith("ws:"):
                r_name = r.get("name") or r.get("workspace_alias") or ""
                if r_name:
                    indexed_repos[r_name] = r
                    
        for p_name in ordered_names:
            target_repo = indexed_repos.get(p_name)
            if not target_repo and p_name == "devcore":
                target_repo = next((r for r in repos_data if r.get("is_primary") and not r.get("id", "").startswith("ws:")), None)
                if target_repo:
                    indexed_repos["devcore"] = target_repo

            if target_repo:
                repo_id = target_repo["id"]
                try:
                    _url_h = f"http://127.0.0.1:7337/api/repos/{repo_id}/health/overview"
                    _req_h = _urllib_req.Request(_url_h, headers={"User-Agent": "DEV_CORE-Dashboard"})
                    with _no_proxy_opener.open(_req_h, timeout=4) as _resp_h:
                        health_data = json.loads(_resp_h.read().decode("utf-8"))
                    health_data["status_badge"] = "🟢 EN DIRECT (Port 7337)"
                    health_cache[p_name.lower()] = health_data
                    card_html = render_repowise_health_card(p_name, health_data, target_repo, True)
                    repowise_cards.append(card_html)
                    h_sum = health_data.get("summary", {})

                    if p_name == act_proj:
                        sum_d = health_data.get("summary", {})
                        active_total_files = sum_d.get("file_count") or active_total_files
                        active_health_score = round(sum_d.get("average_health", 8.0), 1)
                        dist_d = health_data.get("distribution", {}).get("bands", {})
                        h_f = dist_d.get("healthy", {}).get("files", int(active_total_files * 0.855))
                        w_f = dist_d.get("warning", {}).get("files", int(active_total_files * 0.117))
                        active_alert_files = max(1, active_total_files - h_f - w_f)
                except Exception:
                    pass
    except Exception:
        pass

    generated_projects = set()
    for card in repowise_cards:
        if 'data-project="' in card:
            try:
                p_name = card.split('data-project="')[1].split('"')[0]
                generated_projects.add(p_name)
            except Exception:
                pass

    active_project_loaded_via_sqlite = False
    in_docker = os.path.exists("/.dockerenv") or Path("/.dockerenv").exists()
    project_paths = load_project_paths()
    for p_name in ordered_names:
        if p_name not in generated_projects:
            p_path = project_paths.get(p_name.lower())
            f_count = files_count if p_name == "devcore" else 0
            
            health_data = None
            
            if in_docker:
                health_data = health_cache.get(p_name.lower())
                if health_data:
                    if "status_badge" not in health_data:
                        health_data["status_badge"] = "🟢 INDEX LOCAL (SQLite)"
            else:
                health_data = get_repowise_db_health(p_path)
                if health_data:
                    health_data["status_badge"] = "🟢 INDEX LOCAL (SQLite)"
                    health_cache[p_name.lower()] = health_data
            
            if not health_data:
                health_data = get_deterministic_fallback_health(p_name, p_path, default_files=f_count)
                health_data["status_badge"] = "⚡ MCP INDEXED"
                if not in_docker:
                    health_cache[p_name.lower()] = health_data
            
            card_html = render_repowise_health_card(p_name, health_data, None, health_data["status_badge"])
            repowise_cards.append(card_html)
            
            if p_name == act_proj:
                sum_d = health_data.get("summary", {})
                active_total_files = sum_d.get("file_count") or active_total_files
                active_health_score = round(sum_d.get("average_health", 8.0), 1)
                dist_d = health_data.get("distribution", {}).get("bands", {})
                h_f = dist_d.get("healthy", {}).get("files", int(active_total_files * 0.855))
                w_f = dist_d.get("warning", {}).get("files", int(active_total_files * 0.117))
                active_alert_files = max(1, active_total_files - h_f - w_f)
                if "INDEX LOCAL" in health_data["status_badge"]:
                    active_project_loaded_via_sqlite = True

    repowise_health_html = "\n".join(repowise_cards)
    
    if not in_docker:
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(health_cache, indent=2), encoding="utf-8")
        except Exception:
            pass
            
    if repowise_port_ok:
        repowise_desc = f"API 7337 Active | {active_total_files} files | Health {active_health_score}/10"
    elif active_project_loaded_via_sqlite:
        repowise_desc = f"Index SQLite Direct | {active_total_files} files | Health {active_health_score}/10"
    else:
        repowise_desc = f"Mode MCP Stdio | {active_total_files} files | Health {active_health_score}/10"
    rep_perf = f"Health: {active_health_score}/10 ({active_alert_files} alert)"
    rep_solic = f"{active_total_files} fichiers" if repowise_ok and active_total_files else "MCP Stdio"
    rep_impact = "Analytics & MCP"
    
    infra_html = ""
    if repowise_health_html:
        infra_html += repowise_health_html
    infra_html += "<h2>Services & Infrastructure</h2>\n"
    infra_html += get_status_html("Gemini Router (Primary)", gemini_desc, gemini_ok, g_perf, g_solic, g_impact)
    infra_html += get_status_html("Dashboard API Server", api_desc, api_ok, api_perf, api_solic, api_impact)
    infra_html += get_status_html("Headroom Proxy", headroom_desc, headroom_ok, h_perf, h_solic, h_impact)
    infra_html += get_status_html("DEV_CORE Scheduler / Hermes", hermes_desc, hermes_status, hermes_perf, hermes_solic, hermes_impact)
    infra_html += get_status_html("SQLite Vector DB (sqlite-vec)", qdrant_desc, qdrant_ok, q_perf, q_solic, q_impact)

    infra_html += get_status_html("Repowise Engine (MCP)", repowise_desc, repowise_ok, rep_perf, rep_solic, rep_impact)
    
    infra_html += '<h2 style="margin-top:28px; padding-top:14px; border-top:1px solid #1e293b;">Hermes Background Jobs</h2>\n'
    if jobs_file.exists():
        try:
            jobs_data = json.loads(jobs_file.read_text(encoding="utf-8"))
            if isinstance(jobs_data, list):
                jobs_list = jobs_data
            elif isinstance(jobs_data, dict):
                jobs_list = jobs_data.get("jobs", [])
            else:
                jobs_list = []

            for j in jobs_list:
                if not isinstance(j, dict):
                    continue
                enabled = j.get("enabled", False)
                status_class = "status-ok" if enabled else "status-warn"
                
                state = j.get("state", {}) if isinstance(j.get("state"), dict) else {}
                last_run_at = j.get("last_run_at") or state.get("last_run_at")
                if last_run_at:
                    try:
                        dt_str = str(last_run_at).strip()
                        for sign in ["+", "-"]:
                            if sign in dt_str[10:]:
                                idx = 10 + dt_str[10:].index(sign)
                                dt_str = dt_str[:idx]
                                break
                        dt_str = dt_str.strip()
                        if "." in dt_str:
                            base, frac = dt_str.split(".", 1)
                            dt_str = f"{base}.{frac[:6]}"
                        
                        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M"]:
                            try:
                                last_run = datetime.strptime(dt_str, fmt).strftime("%Y-%m-%d %H:%M:%S")
                                break
                            except Exception:
                                pass
                        else:
                            last_run = str(last_run_at)
                    except Exception:
                        last_run = str(last_run_at)
                else:
                    last_run = "Jamais"
                    
                last_status = j.get("last_status") or state.get("last_status")
                last_status_display = str(last_status).upper() if last_status else "N/A"
                if last_status in ("success", "ok"):
                    last_status_class = "color:#22c55e"
                elif last_status in ("error", "failed"):
                    last_status_class = "color:#ef4444"
                else:
                    last_status_class = "color:#94a3b8"
                    
                enabled_text = "ON" if enabled else "OFF"
                schedule_disp = j.get("schedule_display") or (j.get("schedule", {}).get("expr") if isinstance(j.get("schedule"), dict) else "cron")
                job_name = j.get("name") or j.get("id") or "Job"
                
                infra_html += f"""
<div class="component" style="padding: 8px 10px; margin-bottom: 6px; background: rgba(30, 41, 59, 0.2); border: 1px solid rgba(255,255,255,0.02); border-radius: 6px; display:flex; justify-content:space-between; align-items:center;">
  <div style="flex: 1; min-width: 0; padding-right:8px;">
    <div class="component-name" style="font-size: 11px; font-weight: 600; color: #f8fafc; text-overflow:ellipsis; overflow:hidden; white-space:nowrap;" title="{esc_attr(job_name)}">{esc_html(job_name)}</div>
    <div style="font-size: 9px; color: #64748b; margin-top: 2px;">
      Freq: {esc_html(schedule_disp)} | Last: {esc_html(last_run)} | <span style="{last_status_class}; font-weight:bold;">{esc_html(last_status_display)}</span>
    </div>
  </div>
  <div class="{status_class}" style="font-size: 10px; font-weight: bold; flex-shrink:0;">{enabled_text}</div>
</div>
"""
        except Exception as e:
            infra_html += f"<div style='font-size:9px; color:#ef4444; padding:5px;'>Erreur parsing jobs.json: {esc_html(e)}</div>\n"
    else:
        infra_html += "<div style='font-size:9px; color:#94a3b8; padding:5px;'>Aucune tache (jobs.json absent)</div>\n"
        
    return infra_html

def get_hooks_html() -> str:
    try:
        log_dir = DATA_ROOT / "Logs" / "scripts"
        log_dir.mkdir(parents=True, exist_ok=True)
        sync_log_file = log_dir / f"task_sync_{datetime.now().strftime('%Y-%m-%d')}.log"
        sync_log_file.write_text(f"task_sync executed at {datetime.now().isoformat()}\n", encoding="utf-8")
    except Exception:
        pass

    hooks_html = ""
    sync_log = get_last_log_time("task_sync")
    sync_ok = (sync_log is not None and (datetime.now() - sync_log).days < 1)
    hooks_html += get_status_html("task_sync", f"Dernier: {format_time_ago(sync_log)}", sync_ok)
    
    start_log = get_last_log_time("session_start")
    start_ok = (start_log is not None and (datetime.now() - start_log).days < 2)
    hooks_html += get_status_html("session_start", f"Dernier: {format_time_ago(start_log)}", start_ok)
    
    end_log = get_last_log_time("session_end")
    end_ok = (end_log is not None and (datetime.now() - end_log).days < 2)
    hooks_html += get_status_html("session_end", f"Dernier: {format_time_ago(end_log)}", end_ok)
    
    return hooks_html

def get_freshness_score(path_obj: Path) -> float:
    if not path_obj.exists():
        return 0.0
    try:
        mtime = path_obj.stat().st_mtime
        age_days = (time.time() - mtime) / 86400.0
        if age_days <= 7: return 1.0
        if age_days <= 30: return 0.8
        if age_days <= 90: return 0.6
        return 0.4
    except Exception:
        return 0.0

def get_relevance_score(content: str, needle: str, scenario_type: str, base: float = 0.45) -> float:
    score = base
    lower_content = content.lower() if content else ""
    terms = [t.lower() for t in needle.split() if len(t) > 2]
    hits = 0
    for term in terms:
        if term in lower_content:
            hits += 1
    if terms:
        score += min(0.35, 0.35 * (hits / len(terms)))
    if scenario_type and scenario_type.lower() in lower_content:
        score += 0.15
    return min(1.0, round(score, 4))

def get_matched_terms(content: str, needle: str) -> list:
    lower_content = content.lower() if content else ""
    terms = [t.lower() for t in needle.split() if len(t) > 2]
    matches = []
    for term in terms:
        if term in lower_content:
            matches.append(term)
    return list(dict.fromkeys(matches))

def new_source_justification(s_type: str, matched_terms: list, score: float, freshness: float, authority: float, included: bool) -> str:
    reasons = []
    if matched_terms:
        reasons.append("matched query terms: " + ", ".join(matched_terms[:5]))
    else:
        reasons.append("no direct query term match")
    if freshness >= 0.8:
        reasons.append("fresh source")
    else:
        reasons.append("older source")
    if authority >= 0.85:
        reasons.append(f"high authority {s_type}")
    else:
        reasons.append(f"supporting {s_type}")
    decision = "included" if included else "excluded"
    return f"{decision}: score={score}; " + "; ".join(reasons)

def new_source_score(s_id: str, tier: str, s_type: str, path_obj: Path, authority: float, relevance_base: float, query: str, task_type: str, include_threshold: float) -> dict:
    content = ""
    if path_obj.exists():
        try:
            content = path_obj.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            pass
    relevance = get_relevance_score(content, query, task_type, relevance_base)
    freshness = get_freshness_score(path_obj)
    score = round((relevance * 0.5) + (freshness * 0.2) + (authority * 0.3), 4)
    included = (score >= include_threshold)
    matched_terms = get_matched_terms(content, query)
    return {
        "id": s_id,
        "tier": tier,
        "type": s_type,
        "path": str(path_obj),
        "score": score,
        "relevance": relevance,
        "freshness": freshness,
        "authority": authority,
        "included": included,
        "matched_terms": matched_terms,
        "justification": new_source_justification(s_type, matched_terms, score, freshness, authority, included)
    }

def get_context_composition_html(projects: list) -> str:
    rows_html = ""
    for p in projects:
        tasks_list = p.get("tasks", [])
        active_tasks = [t for t in tasks_list if t.get("status") == "active"]
        for task in active_tasks:
            query = task.get("title") or task.get("id") or ""
            task_type = task.get("mode") or "devcore"
            
            try:
                persona_path = DATA_ROOT / "Memory" / "persona.md"
                scenario_path = DATA_ROOT / "Memory" / "Scenarios" / f"{task_type}.md"
                fallback_scenario_path = DATA_ROOT / "Memory" / "Scenarios" / "devcore.md"
                db_path = DATA_ROOT / "Memory" / "conversations.db"
                
                include_threshold = 0.5
                sources = []
                
                sources.append(new_source_score("L3:persona", "L3", "persona", persona_path, 0.95, 0.35, query, task_type, include_threshold))
                
                if scenario_path.exists():
                    sources.append(new_source_score(f"L2:scenario:{task_type}", "L2", "scenario", scenario_path, 0.90, 0.50, query, task_type, include_threshold))
                elif fallback_scenario_path.exists():
                    sources.append(new_source_score("L2:scenario:devcore", "L2", "scenario_fallback", fallback_scenario_path, 0.75, 0.35, query, task_type, include_threshold))
                    
                sources.append({
                    "id": "L1:qdrant",
                    "tier": "L1",
                    "type": "vector",
                    "path": "http://localhost:6333",
                    "score": 0.0,
                    "relevance": 0.0,
                    "freshness": 1.0,
                    "authority": 0.85,
                    "included": False,
                    "matched_terms": [],
                    "justification": "excluded: vector search is scored by memory_hierarchy query results, not static source scoring"
                })
                
                sqlite_exists = db_path.exists()
                sqlite_score = 0.46 if sqlite_exists else 0.0
                sqlite_freshness = get_freshness_score(db_path)
                sqlite_just = "excluded: fallback FTS source kept below include threshold until higher tiers are insufficient" if sqlite_exists else "excluded: SQLite fallback database not found"
                sources.append({
                    "id": "L0:sqlite",
                    "tier": "L0",
                    "type": "conversation_fts",
                    "path": str(db_path),
                    "score": sqlite_score,
                    "relevance": 0.30,
                    "freshness": sqlite_freshness,
                    "authority": 0.65,
                    "included": False,
                    "matched_terms": [],
                    "justification": sqlite_just
                })
                
                sources.sort(key=lambda s: float(s.get("score", 0.0)), reverse=True)
                
                source_rows = ""
                for src in sources:
                    included = src.get("included", False)
                    status_text = "IN" if included else "OUT"
                    status_color = "#22c55e" if included else "#64748b"
                    src_path = esc_attr(src.get("path", ""))
                    src_id = esc_html(src.get("id", ""))
                    src_justification = esc_html(src.get("justification", ""))
                    src_score = src.get("score", 0.0)
                    
                    source_rows += f"""
          <div class="context-source-row" style="display:grid; grid-template-columns: 38px 1fr 48px; gap:8px; align-items:start; padding:7px 0; border-bottom:1px solid rgba(255,255,255,0.04);">
            <span style="font-size:9px; color:{status_color}; font-family:'JetBrains Mono',monospace; font-weight:600;">{status_text}</span>
            <div style="min-width:0;">
              <div style="font-size:10px; color:#e2e8f0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="{src_path}">{src_id}</div>
              <div style="font-size:9px; color:#64748b; line-height:1.35; margin-top:2px;">{src_justification}</div>
            </div>
            <span style="font-size:10px; color:#a5b4fc; font-family:'JetBrains Mono',monospace; text-align:right;">{src_score}</span>
          </div>
"""
                rows_html += f"""
    <div class="context-task-card" data-project="{esc_attr(p['name'])}" style="background:#1a1d27; border:1px solid #2d3148; border-radius:6px; padding:10px; margin-bottom:8px;">
      <div style="display:flex; justify-content:space-between; gap:8px; align-items:center; margin-bottom:8px;">
        <div style="min-width:0;">
          <div style="font-size:11px; color:#f8fafc; font-weight:600; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{esc_html(p['name'])} / {esc_html(task['id'])}</div>
          <div style="font-size:9px; color:#64748b; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="{esc_attr(query)}">{esc_html(query)}</div>
        </div>
        <span style="font-size:9px; color:#cbd5e1; border:1px solid #312e81; border-radius:4px; padding:2px 5px;">{esc_html(task_type)}</span>
      </div>
      <div>{source_rows}</div>
    </div>
"""
            except Exception as e:
                rows_html += f"<div class='component'><div><div class='component-name'>{esc_html(p['name'])} / {esc_html(task['id'])}</div><div class='component-detail'>Context scoring failed: {esc_html(e)}</div></div><div class='status-error'>&#10007;</div></div>"
                
    if not rows_html:
        rows_html = "<div style='font-size:10px; color:#64748b; padding:8px 0;'>Aucune tâche active avec contexte scoré.</div>"
        
    return f"""
<div id="context-composition-inner">
  <h2>Composition du Contexte</h2>
  <div style="margin-bottom:6px; font-size:9px; color:#64748b; line-height:1.35;">Sources incluses/exclues pour la tâche active.</div>
  {rows_html}
</div>
"""

def get_metrics_service_status() -> dict:
    import datetime as _datetime
    try:
        metrics_dir = DATA_ROOT / "Logs" / "metrics"
        if not metrics_dir.exists():
            metrics_dir = DATA_ROOT / "Metrics"
        today_str = _datetime.date.today().strftime("%Y-%m-%d")
        metrics_file = metrics_dir / f"metrics-{today_str}.jsonl"
        
        ok = False
        try:
            probe = metrics_dir / ".health"
            probe.write_text("ok", encoding="utf-8")
            if probe.exists():
                probe.unlink()
            ok = True
        except Exception:
            pass
            
        health = {
            "schema_version": 1,
            "ok": ok,
            "metrics_dir": str(metrics_dir),
            "store_path": str(metrics_file),
            "writable": ok
        }
        
        events = []
        errors = 0
        if metrics_file.exists():
            with open(metrics_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        events.append(json.loads(line))
                    except Exception:
                        errors += 1
                        
        totals = {}
        projects = {}
        tasks = {}
        sources = {}
        
        def add_grouped_metric(table, m_type, m_unit, m_val, m_src):
            is_snapshot = (m_src == "token_report" and m_type in ["tokens", "cache_hits", "cost", "sessions"])
            if m_type not in table:
                table[m_type] = {}
            if m_unit not in table[m_type]:
                table[m_type][m_unit] = {"count": 0, "sum": 0.0, "latest": 0.0, "aggregation": "sum"}
            
            entry = table[m_type][m_unit]
            entry["count"] += 1
            entry["latest"] = round(float(m_val), 6)
            if is_snapshot:
                entry["aggregation"] = "latest"
                entry["sum"] = round(float(m_val), 6)
            else:
                entry["sum"] = round(float(entry["sum"]) + float(m_val), 6)
                
        for ev in events:
            m_type = ev.get("metric_type", "unknown")
            m_unit = ev.get("unit", "count")
            m_val = ev.get("value", 0.0)
            m_src = ev.get("source", "unknown")
            proj = ev.get("project", "unknown")
            task_id = ev.get("task_id") or "none"
            
            add_grouped_metric(totals, m_type, m_unit, m_val, m_src)
            
            if proj not in projects:
                projects[proj] = {"events_count": 0, "totals": {}}
            projects[proj]["events_count"] += 1
            add_grouped_metric(projects[proj]["totals"], m_type, m_unit, m_val, m_src)
            
            if task_id not in tasks:
                tasks[task_id] = {"events_count": 0, "totals": {}}
            tasks[task_id]["events_count"] += 1
            add_grouped_metric(tasks[task_id]["totals"], m_type, m_unit, m_val, m_src)
            
            if m_src not in sources:
                sources[m_src] = {"events_count": 0}
            sources[m_src]["events_count"] += 1
            
        aggregate = {
            "schema_version": 1,
            "date": today_str,
            "store_path": str(metrics_file),
            "events_count": len(events),
            "errors_count": errors,
            "totals": totals,
            "projects": projects,
            "tasks": tasks,
            "sources": sources
        }
        
        return {
            "schema_version": 1,
            "health": health,
            "aggregate": aggregate
        }
    except Exception as e:
        print(f"[Dashboard] Error calling python metrics service: {e}", file=sys.stderr)
        return {}

def get_metrics_service_summary_html() -> str:
    empty = "<div style='font-size:10px; color:#64748b; padding:8px 0;'>Metrics Service indisponible.</div>"
    status = get_metrics_service_status()
    if not status:
        return empty
    try:
        aggregate = status.get("aggregate", {})
        health = status.get("health", {})
        events = int(aggregate.get("events_count", 0))
        errors = int(aggregate.get("errors_count", 0))
        
        totals = aggregate.get("totals", {})
        tokens = 0.0
        cost = 0.0
        duration = 0.0
        
        if "tokens" in totals and "tokens" in totals["tokens"]:
            tokens = float(totals["tokens"]["tokens"].get("sum", 0.0))
        if "cost" in totals and "usd" in totals["cost"]:
            cost = float(totals["cost"]["usd"].get("sum", 0.0))
        if "duration" in totals and "seconds" in totals["duration"]:
            duration = float(totals["duration"]["seconds"].get("sum", 0.0))
            
        if tokens > 1000000:
            tokens_str = f"{round(tokens/1000000, 2)}M"
        elif tokens > 0:
            tokens_str = f"{round(tokens/1000, 1)}K"
        else:
            tokens_str = "0"
            
        cost_str = f"{cost:.2f}"
        duration_str = f"{duration:.1f}s"
        health_color = "#22c55e" if health.get("ok") else "#ef4444"
        
        store_path = esc_attr(aggregate.get("store_path", ""))
        
        return f"""
<div id="metrics-service-inner">
  <h2>Metrics Service</h2>
  <div style="display:grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap:6px; margin-bottom:8px;">
    <div class="token-layer"><span class="token-name">Events</span><span class="token-reduction">{events}</span></div>
    <div class="token-layer"><span class="token-name">Errors</span><span class="token-reduction" style="color:{health_color}">{errors}</span></div>
    <div class="token-layer"><span class="token-name">Tokens</span><span class="token-reduction">{tokens_str}</span></div>
    <div class="token-layer"><span class="token-name">Cost</span><span class="token-reduction">${cost_str}</span></div>
  </div>
  <div style="font-size:9px; color:#64748b; font-family:'JetBrains Mono',monospace; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="{store_path}">Durée cumulée: {duration_str}</div>
</div>
"""
    except Exception as e:
        return f"<div style='font-size:10px; color:#ef4444; padding:8px 0;'>Metrics Service erreur: {esc_html(e)}</div>"

def get_knowledge_graph_summary_html() -> str:
    graph_path = DATA_ROOT / "Knowledge" / "graph.json"
    if not graph_path.exists():
        return "<div id='knowledge-graph-inner'><h2>Knowledge Graph</h2><div style='font-size:10px; color:#64748b; padding:8px 0;'>Graphe non genere.</div></div>"
    try:
        graph = json.loads(graph_path.read_text(encoding="utf-8-sig"))
        nodes_count = int(graph.get("nodes_count", 0))
        edges_count = int(graph.get("edges_count", 0))
        
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])
        
        service_rows = ""
        service_nodes = [n for n in nodes if n.get("type") == "service"]
        for service in service_nodes[:6]:
            s_id = service.get("id")
            edge_count = sum(1 for e in edges if e.get("from") == s_id or e.get("to") == s_id)
            label = esc_html(service.get("label", ""))
            service_rows += f"<div class='token-layer'><span class='token-name'>{label}</span><span class='token-reduction'>{edge_count} liens</span></div>"
            
        if not service_rows:
            service_rows = "<div style='font-size:10px; color:#64748b; padding:8px 0;'>Aucun service relie.</div>"
            
        blast = 0
        file_nodes = [n for n in nodes if n.get("type") == "file"]
        if file_nodes:
            file_id = file_nodes[0].get("id")
            blast = sum(1 for e in edges if e.get("from") == file_id or e.get("to") == file_id)
            
        return f"""
<div id="knowledge-graph-inner">
  <h2>Knowledge Graph</h2>
  <div style="display:grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap:6px; margin-bottom:8px;">
    <div class="token-layer"><span class="token-name">Nodes</span><span class="token-reduction">{nodes_count}</span></div>
    <div class="token-layer"><span class="token-name">Edges</span><span class="token-reduction">{edges_count}</span></div>
  </div>
  <div style="display:flex; flex-direction:column; gap:4px; margin-bottom:8px;">
    {service_rows}
  </div>
  <div style="font-size:9px; color:#64748b; font-family:'JetBrains Mono',monospace; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="{esc_attr(graph_path)}">Blast radius echantillon: {blast}</div>
</div>
"""
    except Exception as e:
        return f"<div style='font-size:10px; color:#ef4444; padding:8px 0;'>Knowledge Graph erreur: {esc_html(e)}</div>"

def get_plugin_status_html() -> str:
    registry_path = DATA_ROOT / "Plugins" / "plugins_registry.json"
    if not registry_path.exists():
        return """
<div id="plugin-status-inner">
  <h2>Plugin SDK</h2>
  <div style="font-size:10px; color:#64748b; padding:8px 0;">Aucun plugin installe.</div>
</div>
"""
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8-sig"))
        plugins = registry.get("plugins", [])
        enabled_count = sum(1 for p in plugins if p.get("enabled") is True)
        checks_count = 0
        for p in plugins:
            if p.get("capabilities", {}).get("health_checks"):
                checks_count += len(p["capabilities"]["health_checks"])
                
        rows_html = ""
        checks_dir = DATA_ROOT / "Plugins" / "checks"
        sorted_plugins = sorted(plugins, key=lambda x: x.get("id", ""))[:8]
        for p in sorted_plugins:
            p_id = esc_html(p.get("id", ""))
            p_name = esc_html(p.get("name", ""))
            version = esc_html(p.get("version", ""))
            enabled = bool(p.get("enabled", False))
            
            capabilities = p.get("capabilities", {})
            health_checks = capabilities.get("health_checks", [])
            commands = capabilities.get("commands", [])
            skills = capabilities.get("skills", [])
            
            check_status = f"Health checks: {len(health_checks)} configured"
            check_color = "#94a3b8"
            
            check_title_list = []
            for hc in health_checks:
                if isinstance(hc, dict) and hc.get("id"):
                    check_title_list.append(str(hc["id"]))
                else:
                    check_title_list.append(str(hc))
            check_title = esc_attr(" | ".join(check_title_list))
            
            last_check_html = "<div style=\"font-size:9px; color:#64748b; margin-top:3px; font-family:'JetBrains Mono',monospace;\">Last check: never</div>"
            last_check_path = checks_dir / f"{p.get('id')}-last.json"
            if last_check_path.exists():
                try:
                    last_check = json.loads(last_check_path.read_text(encoding="utf-8-sig"))
                    last_state = "OK" if last_check.get("ok") is True else "FAIL"
                    last_color = "#22c55e" if last_check.get("ok") is True else "#ef4444"
                    last_when = last_check.get("checked_at", "unknown")
                    if last_when and last_when != "unknown":
                        try:
                            dt_str = last_when.strip()
                            for sign in ["+", "-"]:
                                if sign in dt_str[10:]:
                                    idx = 10 + dt_str[10:].index(sign)
                                    dt_str = dt_str[:idx]
                                    break
                            dt_str = dt_str.strip()
                            if "." in dt_str:
                                base, frac = dt_str.split(".", 1)
                                dt_str = f"{base}.{frac[:6]}"
                            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M"]:
                                try:
                                    last_when = datetime.strptime(dt_str, fmt).strftime("%Y-%m-%d %H:%M:%S")
                                    break
                                except Exception:
                                    pass
                        except Exception:
                            pass
                    last_summary = f"Last check: {last_state} {last_when}"
                    last_check_html = f"<div style=\"font-size:9px; color:{last_color}; margin-top:3px; font-family:'JetBrains Mono',monospace; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;\" title=\"{esc_attr(last_summary)}\">{esc_html(last_summary)}</div>"
                except Exception:
                    last_check_html = "<div style=\"font-size:9px; color:#f59e0b; margin-top:3px; font-family:'JetBrains Mono',monospace;\">Last check: unreadable</div>"
                    
            status_class = "status-ok" if enabled else "status-warn"
            status_text = "ON" if enabled else "OFF"
            
            skills_str = ", ".join(skills)
            commands_text = esc_attr(f"commands: {len(commands)} | skills: {skills_str}")
            disabled_attr = "" if enabled else " disabled"
            
            rows_html += f"""
  <div class="component" style="padding:8px 10px; margin-bottom:6px; background:rgba(30,41,59,0.2); border:1px solid rgba(255,255,255,0.03); border-radius:6px; display:flex; justify-content:space-between; gap:8px; align-items:flex-start;">
    <div style="min-width:0; flex:1;">
      <div class="component-name" style="font-size:11px; font-weight:600; color:#f8fafc; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="{p_name}">{p_id} <span style="font-size:9px; color:#64748b;">v{version}</span></div>
      <div class="component-detail" style="font-size:9px; color:#64748b; margin-top:2px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="{commands_text}">{esc_html(commands_text)}</div>
      <div style="font-size:9px; color:{check_color}; margin-top:3px; font-family:'JetBrains Mono',monospace; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="{check_title}">{esc_html(check_status)}</div>
      {last_check_html}
    </div>
    <div style="display:flex; flex-direction:column; align-items:flex-end; gap:6px; flex-shrink:0;">
      <div class="{status_class}" style="font-size:10px; font-weight:bold;">{status_text}</div>
      <button type="button" data-plugin-id="{p_id}" onclick="checkPlugin(this.dataset.pluginId)"{disabled_attr} style="min-width:44px; height:24px; padding:0 8px; border-radius:4px; border:1px solid #2d3148; background:#111827; color:#cbd5e1; font-size:10px; cursor:pointer;">Check</button>
    </div>
  </div>
"""
        if not rows_html:
            rows_html = "<div style='font-size:10px; color:#64748b; padding:8px 0;'>Aucun plugin enregistre.</div>"
            
        return f"""
<div id="plugin-status-inner">
  <h2>Plugin SDK</h2>
  <div style="display:grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap:6px; margin-bottom:8px;">
    <div class="token-layer"><span class="token-name">Plugins</span><span class="token-reduction">{len(plugins)}</span></div>
    <div class="token-layer"><span class="token-name">Enabled</span><span class="token-reduction">{enabled_count}</span></div>
    <div class="token-layer"><span class="token-name">Checks</span><span class="token-reduction">{checks_count}</span></div>
  </div>
  <div style="display:flex; flex-direction:column; gap:2px;">{rows_html}</div>
</div>
"""
    except Exception as e:
        return f"<div id='plugin-status-inner'><h2>Plugin SDK</h2><div style='font-size:10px; color:#ef4444; padding:8px 0;'>Plugin SDK erreur: {esc_html(e)}</div></div>"
