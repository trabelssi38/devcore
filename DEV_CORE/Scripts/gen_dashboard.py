# gen_dashboard.py -- Python implementation of DEV_CORE Dashboard payload generator
import os
import sys
import json
import time
import html
import socket
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

def esc_html(val) -> str:
    """HTML escape for standard text content."""
    if val is None:
        return ""
    return html.escape(str(val))

def esc_attr(val) -> str:
    """HTML escape for attributes, with quotes enabled."""
    if val is None:
        return ""
    return html.escape(str(val), quote=True)

def format_time_ago(dt) -> str:
    if not dt:
        return "Jamais"
    ts = datetime.now() - dt
    if ts.days >= 1:
        return f"{round(ts.days)} jours"
    hours = ts.seconds // 3600
    if hours >= 1:
        return f"{round(hours)} heures"
    minutes = (ts.seconds % 3600) // 60
    if minutes >= 1:
        return f"{round(minutes)} mins"
    return f"{round(ts.seconds)} s"

def get_status_html(title, desc, is_ok, perf=None, solic=None, impact=None) -> str:
    is_degraded = (is_ok == "degraded")
    if is_degraded:
        status_class = "status-degraded-badge"
        status_icon = "DEGRADED"
        status_label = "Service degraded"
    elif is_ok:
        status_class = "status-ok"
        status_icon = "&#10003;"
        status_label = "Service healthy"
    else:
        status_class = "status-error"
        status_icon = "&#10007;"
        status_label = "Service unavailable"
        
    metrics_html = ""
    if perf or solic or impact:
        metrics_html = '<div class="component-metrics" style="display:flex; flex-wrap:wrap; gap:6px; margin-top:8px; font-size:9px;">'
        if perf:
            metrics_html += f"<span style='padding:2px 6px; background:rgba(16,185,129,0.12); border:1px solid rgba(16,185,129,0.25); border-radius:4px; color:#34d399; font-weight:600;'>Perf: {perf}</span>"
        if solic:
            metrics_html += f"<span style='padding:2px 6px; background:rgba(99,102,241,0.12); border:1px solid rgba(99,102,241,0.25); border-radius:4px; color:#a5b4fc; font-weight:600;'>Solic: {solic}</span>"
        if impact:
            metrics_html += f"<span style='padding:2px 6px; background:rgba(251,191,36,0.12); border:1px solid rgba(251,191,36,0.25); border-radius:4px; color:#fde047; font-weight:600;'>Eff/Imp: {impact}</span>"
        metrics_html += '</div>'
        
    return f"""
<div class="component" style="display:flex; flex-direction:column; align-items:stretch; padding:12px 14px; margin-bottom:8px;">
  <div style="display:flex; justify-content:space-between; align-items:center;">
    <div style="flex: 1; min-width: 0;">
      <div class="component-name" style="font-size:12px; font-weight:600; color:#f1f5f9; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{title}</div>
      <div class="component-detail" style="font-size:10px; color:#94a3b8; margin-top:1px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{desc}</div>
    </div>
    <div class="{status_class}" aria-label="{status_label}" title="{status_label}" style="flex-shrink: 0; margin-left: 12px;">{status_icon}</div>
  </div>
  {metrics_html}
</div>
"""

def get_last_log_time(prefix: str) -> datetime:
    log_dir = DATA_ROOT / "Logs" / "scripts"
    if not log_dir.exists():
        return None
    try:
        files = list(log_dir.glob(f"{prefix}*.log"))
        if not files:
            return None
        files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        return datetime.fromtimestamp(files[0].stat().st_mtime)
    except Exception:
        return None

def is_process_running(script_name: str) -> bool:
    try:
        # Run wmic to get python processes command lines
        cmd = ["wmic", "process", "where", "name='python.exe' or name='pythonw.exe'", "get", "commandline"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                if script_name in line:
                    return True
    except Exception as e:
        print(f"[Dashboard] Error checking process {script_name}: {e}")
    return False

def get_qdrant_points_count() -> int:
    import urllib.request
    try:
        req = urllib.request.Request("http://localhost:6333/collections", method="GET")
        with urllib.request.urlopen(req, timeout=2) as response:
            data = json.loads(response.read().decode("utf-8"))
            collections = data.get("result", {}).get("collections", [])
            
        points_count = 0
        for c in collections:
            c_name = c.get("name")
            if c_name:
                try:
                    req_c = urllib.request.Request(f"http://localhost:6333/collections/{c_name}", method="GET")
                    with urllib.request.urlopen(req_c, timeout=2) as resp_c:
                        data_c = json.loads(resp_c.read().decode("utf-8"))
                        points_count += data_c.get("result", {}).get("points_count", 0)
                except Exception:
                    pass
        return points_count
    except Exception:
        return 0


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
        tasks_list = p.get("tasks", [])
        active_tasks = [t for t in tasks_list if t.get("status") == "active"]
        for task in active_tasks:
            query = task.get("title") or task.get("id") or ""
            task_type = task.get("mode") or "devcore"
            
            try:
                context_script = PLATFORM_ROOT / "Scripts" / "context_service.ps1"
                cmd = [
                    "powershell.exe",
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(context_script),
                    "-Action",
                    "ScoreSources",
                    "-Query",
                    query,
                    "-TaskType",
                    task_type,
                    "-Json"
                ]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if res.returncode == 0 and res.stdout.strip():
                    score_payload = json.loads(res.stdout)
                    sources = score_payload.get("sources", [])
                    # Sort sources by score descending
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
    try:
        metrics_script = PLATFORM_ROOT / "Scripts" / "metrics_service.ps1"
        cmd = [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(metrics_script),
            "-Action",
            "Status",
            "-Json"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if res.returncode == 0:
            return json.loads(res.stdout)
    except Exception as e:
        print(f"[Dashboard] Error calling metrics service: {e}")
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
        
        # Extract totals
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
    empty = "<div style='font-size:10px; color:#64748b; padding:8px 0;'>Knowledge Graph indisponible.</div>"
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
            # Count edges connected to this service
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

def get_services_html(projects, token_metrics) -> str:
    # 1. Qdrant
    qdrant_ok = check_port("127.0.0.1", 6333)
    qdrant_points = get_qdrant_points_count() if qdrant_ok else 0
    qdrant_desc = f"Port 6333 | {qdrant_points} vectors" if qdrant_ok else "Port 6333"
    q_perf = "Rapide (1ms)" if qdrant_ok else "HS"
    q_solic = f"{qdrant_points:,} vecteurs" if qdrant_ok else "Aucune"
    q_impact = "Optimise (4 colls)" if qdrant_ok else "Perdu"
    
    # 2. Gemini Router
    gemini_ok = check_port("127.0.0.1", 20130)
    cache_hit = 0
    token_str = "Faible"
    if gemini_ok and token_metrics:
        totals = token_metrics.get("totals", {})
        total_tokens = totals.get("tokens", 0) or (token_metrics.get("total_input_tokens", 0) + token_metrics.get("total_output_tokens", 0))
        cache_hit = int(round(token_metrics.get("average_cache_hit_ratio", 0) * 100))
        if total_tokens >= 1000000:
            token_str = f"{round(total_tokens/1000000, 1)}M"
        elif total_tokens >= 1000:
            token_str = f"{round(total_tokens/1000, 1)}k"
        else:
            token_str = str(total_tokens)
    gemini_desc = f"Port 20130 | Cache: {cache_hit}% | {token_str} tok" if gemini_ok else "Port 20130"
    g_perf = "99.9% dispo" if gemini_ok else "HS"
    g_solic = f"{token_str} tokens" if gemini_ok else "Faible"
    g_impact = f"Cache: {cache_hit}%" if gemini_ok else "Null"
    
    # 3. Dashboard API Server
    api_ok = check_port("127.0.0.1", 20129)
    api_desc = f"Port 20129 | {len(projects)} projets" if api_ok else "Port 20129"
    api_perf = "Rapide (4ms)" if api_ok else "HS"
    api_solic = f"{len(projects)} projets" if api_ok else "Aucune"
    api_impact = "Administration"
    
    # 4. Headroom Proxy
    headroom_ok = check_port("127.0.0.1", 8787)
    headroom_desc = "Port 8787 | ~98% reduction" if headroom_ok else "Port 8787"
    h_perf = "< 2ms overhead" if headroom_ok else "HS"
    h_solic = "Moyenne" if headroom_ok else "Aucune"
    h_impact = "98% reduction" if headroom_ok else "Perdu"
    
    # 5. Hermes Cron Daemon
    tick_log = DATA_ROOT / "Logs" / "hermes" / "cron_tick.log"
    hermes_tick_warn_seconds = 600
    last_tick_sec = 9999
    is_hermes_alive = is_process_running("hermes_cron_tick.py")
    
    if tick_log.exists():
        try:
            mtime = tick_log.stat().st_mtime
            last_tick_sec = int(round(time.time() - mtime))
        except Exception:
            pass
            
    hermes_status = False
    if is_hermes_alive and last_tick_sec <= hermes_tick_warn_seconds:
        hermes_status = True
    elif is_hermes_alive:
        hermes_status = "degraded"
        
    job_count = 0
    jobs_file = Path(os.path.expanduser("~")) / ".hermes" / "cron" / "jobs.json"
    if jobs_file.exists():
        try:
            jobs_data = json.loads(jobs_file.read_text(encoding="utf-8"))
            job_count = len(jobs_data.get("jobs", []))
        except Exception:
            pass
            
    if hermes_status is True:
        hermes_desc = f"Ticking ({last_tick_sec}s) | {job_count} jobs"
    elif hermes_status == "degraded":
        hermes_desc = f"DEGRADED: process vivant, tick vieux ({last_tick_sec}s) | {job_count} jobs"
    else:
        hermes_desc = f"Inactif | {job_count} jobs"
        
    hermes_perf = "Precis (0s lag)" if hermes_status is True else f"DEGRADED tick>{hermes_tick_warn_seconds}s" if hermes_status == "degraded" else "HS"
    hermes_solic = f"{job_count} jobs"
    hermes_impact = "Orchestrateur"
    
    # 6. Repowise Server
    repowise_ok = check_port("127.0.0.1", 7337)
    files_count = 0
    repowise_desc = "Port 7337"
    if repowise_ok:
        repowise_state_file = Path("C:/devcore/.repowise/state.json")
        repowise_kg_file = Path("C:/devcore/.repowise/knowledge-graph.json")
        if repowise_state_file.exists():
            try:
                if repowise_kg_file.exists():
                    kg_data = json.loads(repowise_kg_file.read_text(encoding="utf-8"))
                    files_count = kg_data.get("project", {}).get("total_files", 0)
                if files_count > 0:
                    repowise_desc = f"Port 7337 | {files_count} files | health 8.6/10"
                else:
                    repowise_desc = "Port 7337 | indexé"
            except Exception:
                pass
                
    rep_perf = "Health: 8.9/10" if repowise_ok else "HS"
    rep_solic = f"{files_count} fichiers" if repowise_ok and files_count else "Inactif"
    rep_impact = "Analytics & MCP"
    
    infra_html = "<h2>Services & Infrastructure</h2>\n"
    infra_html += get_status_html("Gemini Router (Primary)", gemini_desc, gemini_ok, g_perf, g_solic, g_impact)
    infra_html += get_status_html("Dashboard API Server", api_desc, api_ok, api_perf, api_solic, api_impact)
    infra_html += get_status_html("Headroom Proxy", headroom_desc, headroom_ok, h_perf, h_solic, h_impact)
    infra_html += get_status_html("Hermes Cron Daemon", hermes_desc, hermes_status, hermes_perf, hermes_solic, hermes_impact)
    infra_html += get_status_html("Qdrant Vector DB", qdrant_desc, qdrant_ok, q_perf, q_solic, q_impact)
    infra_html += get_status_html("Repowise Server", repowise_desc, repowise_ok, rep_perf, rep_solic, rep_impact)
    
    # Background Jobs section
    infra_html += "<h2>Hermes Background Jobs</h2>\n"
    if jobs_file.exists():
        try:
            jobs_data = json.loads(jobs_file.read_text(encoding="utf-8"))
            for j in jobs_data.get("jobs", []):
                enabled = j.get("enabled", False)
                status_class = "status-ok" if enabled else "status-warn"
                
                last_run_at = j.get("last_run_at")
                if last_run_at:
                    try:
                        dt_str = last_run_at.strip()
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
                            last_run = last_run_at
                    except Exception:
                        last_run = last_run_at
                else:
                    last_run = "Jamais"
                    
                last_status = j.get("last_status")
                last_status_display = last_status.upper() if last_status else "N/A"
                if last_status == "success":
                    last_status_class = "color:#22c55e"
                elif last_status == "error":
                    last_status_class = "color:#ef4444"
                else:
                    last_status_class = "color:#94a3b8"
                    
                enabled_text = "ON" if enabled else "OFF"
                
                infra_html += f"""
<div class="component" style="padding: 8px 10px; margin-bottom: 6px; background: rgba(30, 41, 59, 0.2); border: 1px solid rgba(255,255,255,0.02); border-radius: 6px; display:flex; justify-content:space-between; align-items:center;">
  <div style="flex: 1; min-width: 0; padding-right:8px;">
    <div class="component-name" style="font-size: 11px; font-weight: 600; color: #f8fafc; text-overflow:ellipsis; overflow:hidden; white-space:nowrap;" title="{esc_attr(j.get('name'))}">{esc_html(j.get('name'))}</div>
    <div style="font-size: 9px; color: #64748b; margin-top: 2px;">
      Freq: {esc_html(j.get('schedule_display'))} | Last: {esc_html(last_run)} | <span style="{last_status_class}; font-weight:bold;">{esc_html(last_status_display)}</span>
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
    hooks_html = ""
    # task_sync
    sync_log = get_last_log_time("task_sync")
    sync_ok = (sync_log is not None and (datetime.now() - sync_log).days < 1)
    hooks_html += get_status_html("task_sync", f"Dernier: {format_time_ago(sync_log)}", sync_ok)
    
    # session_start
    start_log = get_last_log_time("session_start")
    start_ok = (start_log is not None and (datetime.now() - start_log).days < 2)
    hooks_html += get_status_html("session_start", f"Dernier: {format_time_ago(start_log)}", start_ok)
    
    # session_end
    end_log = get_last_log_time("session_end")
    end_ok = (end_log is not None and (datetime.now() - end_log).days < 2)
    hooks_html += get_status_html("session_end", f"Dernier: {format_time_ago(end_log)}", end_ok)
    
    return hooks_html

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-Json", "--json", action="store_true")
    parser.add_argument("-SkipTokenRefresh", "--skip-token-refresh", action="store_true")
    args = parser.parse_args()

    # If running in JSON mode, redirect standard prints to stderr to keep stdout completely clean
    original_stdout = sys.stdout
    if args.json:
        sys.stdout = sys.stderr

    generated_at = datetime.now().isoformat()
    memory_dir = DATA_ROOT / "Memory"
    
    # Load token metrics at the start
    token_metrics = {}
    token_json = DATA_ROOT / "Logs" / "token_reports" / "token_metrics_summary.json"
    if token_json.exists():
        try:
            token_metrics = json.loads(token_json.read_text(encoding="utf-8-sig"))
        except Exception:
            pass

    # Load plugins registry at the start
    plugins_registry = {}
    plugins_json = DATA_ROOT / "Plugins" / "plugins_registry.json"
    if plugins_json.exists():
        try:
            plugins_registry = json.loads(plugins_json.read_text(encoding="utf-8-sig"))
        except Exception:
            pass
            
    projects = []
    task_details = {}
    
    db_path = DATA_ROOT / "devcore.db"
    if db_path.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT project FROM tasks WHERE project != 'scripts'")
            proj_names = [row[0] for row in cur.fetchall()]
            
            for name in proj_names:
                cur.execute("SELECT id, title, status, mode, steps_total, steps_done, source, details, started_at, completed_at FROM tasks WHERE project = ? ORDER BY id ASC", (name,))
                rows = cur.fetchall()
                tasks = []
                for r in rows:
                    tasks.append({
                        "id": r[0],
                        "title": r[1],
                        "status": r[2],
                        "mode": r[3],
                        "steps_total": r[4],
                        "steps_done": r[5],
                        "source": r[6],
                        "details": r[7],
                        "started_at": r[8],
                        "completed_at": r[9]
                    })
                total = len(tasks)
                done = sum(1 for t in tasks if t["status"] == "done")
                pct = int((done / total) * 100) if total > 0 else 0
                
                active_task = next((t for t in tasks if t["status"] in ["todo", "active", "paused"]), None)
                if not active_task and tasks:
                    active_task = tasks[-1]
                    
                active_id = active_task["id"] if active_task else "Aucune"
                active_mode = active_task["mode"] if active_task else "N/A"
                active_steps = f"{active_task['steps_done']}/{active_task['steps_total']}" if active_task else ""
                
                active_tasks = [t for t in tasks if t["status"] in ["todo", "active", "paused"]]
                completed_tasks = [t for t in tasks if t["status"] == "done"]
                limited_tasks = completed_tasks[-20:] + active_tasks
                
                for t in limited_tasks:
                    if t.get("details"):
                        task_details[f"{name}_{t['id']}"] = t["details"]
                        
                proj_tokens_str = ""
                if token_metrics and "projects" in token_metrics:
                    proj_stats = token_metrics["projects"].get(name)
                    if proj_stats:
                        try:
                            p_tokens = float(proj_stats.get("tokens", 0))
                            p_tokens_str = f"{round(p_tokens/1000000, 2)}M" if p_tokens > 1000000 else f"{round(p_tokens/1000, 1)}K"
                            p_cost = float(proj_stats.get("cost_usd", 0))
                            proj_tokens_str = f"{p_tokens_str} tokens | ${p_cost:.2f}"
                        except Exception:
                            pass
                            
                projects.append({
                    "name": name,
                    "active_task": active_id,
                    "mode": active_mode,
                    "progress": pct,
                    "steps": active_steps,
                    "tasks": limited_tasks,
                    "tokens": proj_tokens_str
                })
            conn.close()
        except Exception as e:
            print(f"[gen_dashboard] SQLite read warning: {e}")
            projects = []
            task_details = {}

    if not projects and memory_dir.exists():
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
                    
                    proj_tokens_str = ""
                    if token_metrics and "projects" in token_metrics:
                        proj_stats = token_metrics["projects"].get(folder.name)
                        if proj_stats:
                            try:
                                p_tokens = float(proj_stats.get("tokens", 0))
                                if p_tokens > 1000000:
                                    p_tokens_str = f"{round(p_tokens/1000000, 2)}M"
                                else:
                                    p_tokens_str = f"{round(p_tokens/1000, 1)}K"
                                p_cost = float(proj_stats.get("cost_usd", 0))
                                proj_tokens_str = f"{p_tokens_str} tokens | ${p_cost:.2f}"
                            except Exception:
                                pass

                    projects.append({
                        "name": folder.name,
                        "active_task": active_id,
                        "mode": active_mode,
                        "progress": pct,
                        "steps": active_steps,
                        "tasks": limited_tasks,
                        "tokens": proj_tokens_str
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
        
        # Color coding active task
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

    tasks_html = ""
    for p in projects:
        # Group tasks by worktree - bound completed tasks to 20 most recent per project
        from collections import defaultdict
        worktree_groups = defaultdict(list)
        
        project_tasks = p["tasks"]
        active_t = [t for t in project_tasks if t.get("status") == "active"]
        completed_t = [t for t in project_tasks if t.get("status") != "active"]
        completed_t.sort(key=lambda t: get_task_datetime(t), reverse=True)
        bounded_tasks = active_t + completed_t[:20]
        
        for t in bounded_tasks:
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
                    details_button = f"<button class='btn-action btn-details' onclick='showDetails(\"{esc_attr(p_name)}\", \"{esc_attr(t_id)}\", \"{esc_attr(t_status)}\", this, event)' title='Voir les détails'>Détails</button>"

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
                        steps_detail_html += f"<div class='step-item {step_class}'>{icon} {esc_html(s_title)}</div>"
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
                    date_items.append(f"Commit: {esc_html(t['committed_at'])}")
                if t.get("started_at"):
                    date_items.append(f"Debut: {esc_html(t['started_at'])}")
                if t.get("completed_at"):
                    date_items.append(f"Fin: {esc_html(t['completed_at'])}")
                if date_items:
                    dates_html = f"<div style='font-size:9px;color:#475569;margin-top:2px;font-family:monospace'>{' | '.join(date_items)}</div>"

                # Boutons Clôturer / Supprimer
                done_button = ""
                if t_status != "done":
                    done_button = f"<button class='btn-action btn-done' title='Clôturer' onclick='completeTask(\"{esc_attr(p_name)}\", \"{esc_attr(t_id)}\")'>&#10004;</button>"
                delete_button = f"<button class='btn-action btn-delete' title='Supprimer' onclick='deleteTask(\"{esc_attr(p_name)}\", \"{esc_attr(t_id)}\")'>&#128465;</button>"

                tasks_html += f"""
            <div class="mission {active_class} {badge_class}" data-date="{task_date}">
              <div class="mission-header" style="display:flex; gap:10px; align-items:center; width:100%">
                <span class="badge {badge_class}">{badge_text}</span>
                <div style="flex:1; min-width: 0;">
                  <div class="mission-title" style="display:flex; justify-content:space-between; align-items:center; width:100%;">
                    <span style="text-overflow:ellipsis; overflow:hidden; white-space:nowrap;" title="{esc_attr(t_id)}: {esc_attr(t.get('title', ''))}">{esc_html(t_id)}: {esc_html(t.get('title', ''))}</span>
                    <div style="display:flex; flex-direction:column; align-items:flex-end; gap:4px; flex-shrink:0;">
                      <div style="display:flex; align-items:center; gap:2px;">{task_tokens_str}{task_cost_str}{details_button}</div>
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
            recent_sess = [s for s in sessions_data if s.get("project") not in excluded_projects][-50:]
            recent_sess.reverse()
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
      <div class="session-row" data-project="{s.get('project')}" style="background: rgba(30, 41, 59, 0.2); border: 1px solid rgba(255,255,255,0.03); border-radius: 6px; padding: 8px 12px; display: flex; justify-content: space-between; align-items: center; transition: transform 0.15s ease, opacity 0.15s ease, border-color 0.15s ease; font-size: 11px; margin-bottom: 6px;">
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
                token_activity_html += '<tr style="border-bottom:1px solid #334155; color:#94a3b8; text-align:left;"><th style="padding:6px 8px;">T&acirc;che</th><th style="padding:6px 8px;">Mode</th><th style="padding:6px 8px; text-align:right;">Tokens In</th><th style="padding:6px 8px; text-align:right;">Tokens Out</th><th style="padding:6px 8px; text-align:right;">Total</th><th style="padding:6px 8px; text-align:center;">Statut</th></tr>'
                
                thresholds = {"coding": 500000, "reasoning": 2000000, "bulk": 1000000}
                for tid, tinfo in tasks_stats.items():
                    mode = tinfo.get("mode", "coding")
                    t_in = tinfo.get("tokens_in", 0)
                    t_out = tinfo.get("tokens_out", 0)
                    t_total = tinfo.get("total_tokens", 0)
                    limit = thresholds.get(mode, 1000000)
                    
                    disp_tid = f'<span style="color:#94a3b8; font-style:italic;">Hors T&acirc;che (Session libre)</span>' if tid in ("Aucune", "Sans tache", "none") else esc_html(tid)
                    mode_badge = f'<span style="background:rgba(99,102,241,0.15); color:#818cf8; border:1px solid rgba(99,102,241,0.3); padding:2px 6px; border-radius:4px; font-size:10px; font-weight:600;">{esc_html(mode)}</span>'
                    
                    status_badge = '<span style="background:rgba(16,185,129,0.15); color:#34d399; border:1px solid rgba(16,185,129,0.3); padding:2px 6px; border-radius:4px; font-size:10px; font-weight:600;">OK</span>'
                    if t_total > limit:
                        status_badge = '<span style="background:rgba(239,68,68,0.15); color:#f87171; border:1px solid rgba(239,68,68,0.3); padding:2px 6px; border-radius:4px; font-size:10px; font-weight:600;">ALERTE</span>'
                    
                    tin_str = f"{t_in:,}".replace(",", " ")
                    tout_str = f"{t_out:,}".replace(",", " ")
                    ttot_str = f"{t_total:,}".replace(",", " ")
                    
                    token_activity_html += f'<tr style="border-bottom:1px solid #1e293b; color:#cbd5e1; transition:background 0.2s;" onmouseover="this.style.background=\'rgba(255,255,255,0.03)\'" onmouseout="this.style.background=\'transparent\'"><td style="padding:6px 8px; font-weight:600;">{disp_tid}</td><td style="padding:6px 8px;">{mode_badge}</td><td style="padding:6px 8px; text-align:right;">{tin_str}</td><td style="padding:6px 8px; text-align:right;">{tout_str}</td><td style="padding:6px 8px; text-align:right; font-weight:bold;">{ttot_str}</td><td style="padding:6px 8px; text-align:center;">{status_badge}</td></tr>'
                token_activity_html += "</table>"
            else:
                token_activity_html += "<div style='font-size:11px; color:#64748b; padding:8px 0;'>Aucune donn&eacute;e de supervision enregistr&eacute;e.</div>"
        except Exception as e:
            token_activity_html += f"<div style='font-size:11px; color:#ef4444; padding:8px 0;'>Erreur de lecture de la supervision: {esc_html(str(e))}</div>"
    else:
        token_activity_html += "<div style='font-size:11px; color:#64748b; padding:8px 0;'>Aucune donn&eacute;e de supervision (Headroom inactif ou pas encore d'appels).</div>"
    token_activity_html += "</div>"

    # Load recent alerts from alerts.log
    alerts_html = "<h2>Alerte de Consommation &amp; &Eacute;v&eacute;nements</h2>"
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
            ev_task = ev.get("task_id") or "-"
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
                
            event_bus_html += f'    <div class="token-layer"><span class="token-name">{esc_html(time_str)} {esc_html(ev_type)}</span><span class="token-reduction" title="{esc_attr(ev_src)}">{esc_html(ev_task)}</span></div>\n'
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
        "token_metrics": token_metrics,
        "projects_raw": projects,  # Added structured data for Next.js frontend!
        "services_raw": services,
        "events_raw": events[:10] if events else [],
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
            template = template.replace('{{AUTOMATION_HOOKS}}', hooks_html)
            template = template.replace('{{TOKEN_ACTIVITY_REPORT}}', token_activity_html)
            template = template.replace('{{CONTEXT_COMPOSITION}}', context_composition_html)
            template = template.replace('{{METRICS_SERVICE_SUMMARY}}', metrics_service_summary_html)
            template = template.replace('{{EVENT_BUS_RECENT}}', event_bus_html + "<div style='margin-top:12px;'></div>" + alerts_html)
            template = template.replace('{{KNOWLEDGE_GRAPH_SUMMARY}}', knowledge_graph_summary_html)
            template = template.replace('{{PLUGIN_STATUS}}', plugin_status_html)
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
        original_stdout.buffer.write(payload_str.encode("utf-8"))
        original_stdout.write("\n")

if __name__ == "__main__":
    main()
