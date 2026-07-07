import os
import sys
import json
import re
import argparse
from datetime import datetime, timedelta

def format_duration(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    if h > 0:
        return f"{h}h {m}m"
    return f"{m}m"

def clean_task_id(text):
    match = re.search(r'\bT-(\d+)\b', text, re.IGNORECASE)
    if match:
        return f"T-{int(match.group(1)):02d}"
    return None

def parse_created_at(created_at_str):
    if not created_at_str:
        return None
    s = created_at_str.replace("Z", "")
    if "+" in s:
        s = s.split("+")[0]
    if "-" in s[10:]:
        s = s[:10] + s[10:].split("-")[0]
    
    if "." in s:
        parts = s.split(".")
        main_part = parts[0]
        frac_part = parts[1][:6].ljust(6, '0')
        s = f"{main_part}.{frac_part}"
        try:
            return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
            pass
            
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        try:
            return datetime.strptime(s.split("T")[0], "%Y-%m-%d")
        except ValueError:
            return None

def main():
    parser = argparse.ArgumentParser(description="Génère un rapport de tokens DEV_CORE ultra-premium avec répartition par projet, session et tâche.")
    parser.add_argument("--date", type=str, help="Date au format YYYY-MM-DD (par défaut aujourd'hui)")
    args = parser.parse_args()

    if args.date:
        tdate = args.date
    else:
        tdate = datetime.now().strftime("%Y-%m-%d")

    brain_dir = r"C:\Users\trb_m\.gemini\antigravity\brain"
    reports_dir = r"C:\devcore\DEV_CORE_DATA\Logs\token_reports"

    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir)

    # Détection dynamique des projets valides dans Memory
    memory_path = r"C:\devcore\DEV_CORE_DATA\Memory"
    valid_projects = ["devcore", "cea_dashboard", "job_tracker", "default"]
    task_to_project = {}
    if os.path.exists(memory_path):
        try:
            for d in os.listdir(memory_path):
                proj_dir = os.path.join(memory_path, d)
                if os.path.isdir(proj_dir):
                    d_lower = d.lower()
                    if d_lower not in ["archive", "patterns", "scores", "default"] and d_lower not in valid_projects:
                        valid_projects.append(d_lower)
                    
                    tasks_file = os.path.join(proj_dir, "tasks.json")
                    if os.path.exists(tasks_file):
                        try:
                            with open(tasks_file, "r", encoding="utf-8") as tf:
                                board = json.load(tf)
                                for t in board.get("tasks", []):
                                    tid = t.get("id")
                                    if tid:
                                        task_to_project[tid.upper()] = d_lower
                        except Exception:
                            pass
        except Exception:
            pass

    # 1. Global Aggregation Metrics
    totals = {
        "tokens": 0,
        "cache_hits": 0,
        "output_tokens": 0,
        "duration_seconds": 0,
        "sessions_count": 0,
        "cost_usd": 0.0
    }
    
    projects_data = {}
    tasks_data = {}
    sessions_data = []

    if os.path.exists(brain_dir):
        for folder_name in os.listdir(brain_dir):
            folder_path = os.path.join(brain_dir, folder_name)
            if not os.path.isdir(folder_path) or folder_name == "tempmediaStorage":
                continue
            log_path = None
            overview_path = os.path.join(folder_path, ".system_generated", "logs", "overview.txt")
            transcript_path = os.path.join(folder_path, ".system_generated", "logs", "transcript.jsonl")
            
            if os.path.exists(overview_path):
                log_path = overview_path
            elif os.path.exists(transcript_path):
                log_path = transcript_path

            if log_path:
                timestamps = []
                user_turns = 0
                model_turns = 0
                model_chars = 0
                
                session_tasks = set()
                detected_project = "devcore" # Default fallback
                
                current_task = "Sans tâche"
                session_task_tokens = {}
                
                try:
                    with open(log_path, "r", encoding="utf-8") as f:
                        for line in f:
                            if not line.strip():
                                continue
                            try:
                                data = json.loads(line)
                                created_at_str = data.get("created_at")
                                if not created_at_str:
                                    continue
                                
                                dt_utc = parse_created_at(created_at_str)
                                if not dt_utc:
                                    continue
                                dt_local = dt_utc + timedelta(hours=1)
                                timestamps.append(dt_local)
                                
                                content = data.get("content", "")
                                source = data.get("source")
                                type_ = data.get("type")
                                tool_calls = data.get("tool_calls", [])
                                
                                is_user = (source == "USER_EXPLICIT" or type_ == "USER_INPUT")
                                is_model = (source == "MODEL" and type_ == "PLANNER_RESPONSE")
                                
                                # A. Project identification
                                for tc in tool_calls:
                                    tc_args = tc.get("args", {})
                                    if isinstance(tc_args, str):
                                        args_str = tc_args.lower()
                                    else:
                                        args_str = json.dumps(tc_args).lower()
                                        
                                    normalized_args = args_str.replace("\\\\", "/").replace("\\", "/")
                                    best_project = None
                                    max_idx = -1
                                    for proj in valid_projects:
                                        proj_lower = proj.lower()
                                        if f"/{proj_lower}/" in normalized_args or normalized_args.endswith(f"/{proj_lower}") or f"/{proj_lower}\\" in normalized_args or proj_lower in normalized_args:
                                            idx = normalized_args.rfind(proj_lower)
                                            if idx > max_idx:
                                                max_idx = idx
                                                best_project = proj_lower
                                                
                                    if best_project:
                                        detected_project = best_project
                                
                                # B. Task identification & project extraction
                                task_matches = re.findall(r'\bT-\d+\b', content, re.IGNORECASE)
                                if task_matches:
                                    for tm in task_matches:
                                        tid = clean_task_id(tm)
                                        if tid:
                                            current_task = tid
                                            session_tasks.add(tid)
                                            # Fallback project association based on task ID mapping
                                            tid_upper = tid.upper()
                                            if tid_upper in task_to_project:
                                                detected_project = task_to_project[tid_upper]
                                
                                if is_user:
                                    user_turns += 1
                                elif is_model:
                                    model_turns += 1
                                    model_chars += len(content)
                                    
                                    turn_in = 15000
                                    turn_cache = int(15000 * 0.85)
                                    turn_out = len(content) // 4
                                    
                                    if current_task not in session_task_tokens:
                                        session_task_tokens[current_task] = {
                                            "tokens": 0,
                                            "cache_hits": 0,
                                            "output_tokens": 0,
                                            "turns": 0
                                        }
                                    session_task_tokens[current_task]["tokens"] += turn_in
                                    session_task_tokens[current_task]["cache_hits"] += turn_cache
                                    session_task_tokens[current_task]["output_tokens"] += turn_out
                                    session_task_tokens[current_task]["turns"] += 1
                            except Exception:
                                continue
                except Exception as e:
                    pass

                if not timestamps:
                    continue

                min_dt = min(timestamps)
                max_dt = max(timestamps)
                duration_sec = (max_dt - min_dt).total_seconds()
                if duration_sec < 60:
                    duration_sec = 60

                session_in = model_turns * 15000
                session_cache = int(session_in * 0.85)
                session_out = model_chars // 4
                
                # Input normal: $3/M, Input cached: $0.45/M, Output: $15/M
                normal_in = session_in - session_cache
                session_cost = (normal_in * 0.000003) + (session_cache * 0.00000045) + (session_out * 0.000015)

                if not session_task_tokens and session_tasks:
                    share_in = session_in // len(session_tasks)
                    share_cache = session_cache // len(session_tasks)
                    share_out = session_out // len(session_tasks)
                    for t in session_tasks:
                        session_task_tokens[t] = {
                            "tokens": share_in,
                            "cache_hits": share_cache,
                            "output_tokens": share_out,
                            "turns": model_turns // len(session_tasks) or 1
                        }
                elif not session_task_tokens:
                    session_task_tokens["Sans tâche"] = {
                        "tokens": session_in,
                        "cache_hits": session_cache,
                        "output_tokens": session_out,
                        "turns": model_turns
                    }

                session_info = {
                    "id": folder_name,
                    "project": detected_project,
                    "tasks": sorted(list(session_tasks)) if session_tasks else ["Sans tâche"],
                    "date": min_dt.strftime("%Y-%m-%d"),
                    "start_time": min_dt.strftime("%H:%M:%S"),
                    "end_time": max_dt.strftime("%H:%M:%S"),
                    "duration": format_duration(duration_sec),
                    "tokens": session_in,
                    "cache_hits": session_cache,
                    "output_tokens": session_out,
                    "turns": model_turns + user_turns,
                    "cost_usd": round(session_cost, 4)
                }
                
                sessions_data.append(session_info)

                totals["tokens"] += session_in
                totals["cache_hits"] += session_cache
                totals["output_tokens"] += session_out
                totals["duration_seconds"] += duration_sec
                totals["sessions_count"] += 1
                totals["cost_usd"] += session_cost

                # Project statistics
                if detected_project not in projects_data:
                    projects_data[detected_project] = {
                        "tokens": 0,
                        "cache_hits": 0,
                        "output_tokens": 0,
                        "sessions": 0,
                        "cost_usd": 0.0
                    }
                projects_data[detected_project]["tokens"] += session_in
                projects_data[detected_project]["cache_hits"] += session_cache
                projects_data[detected_project]["output_tokens"] += session_out
                projects_data[detected_project]["sessions"] += 1
                projects_data[detected_project]["cost_usd"] += session_cost

                # Task statistics
                for tid, tdata in session_task_tokens.items():
                    task_key = f"{detected_project}_{tid}"
                    if task_key not in tasks_data:
                        tasks_data[task_key] = {
                            "project": detected_project,
                            "tokens": 0,
                            "cache_hits": 0,
                            "output_tokens": 0,
                            "turns": 0,
                            "cost_usd": 0.0
                        }
                    t_cost = ((tdata["tokens"] - tdata["cache_hits"]) * 0.000003) + (tdata["cache_hits"] * 0.00000045) + (tdata["output_tokens"] * 0.000015)
                    tasks_data[task_key]["tokens"] += tdata["tokens"]
                    tasks_data[task_key]["cache_hits"] += tdata["cache_hits"]
                    tasks_data[task_key]["output_tokens"] += tdata["output_tokens"]
                    tasks_data[task_key]["turns"] += tdata["turns"]
                    tasks_data[task_key]["cost_usd"] += t_cost

    totals["duration_minutes"] = int(totals["duration_seconds"] // 60)
    totals["cost_usd"] = round(totals["cost_usd"], 4)
    del totals["duration_seconds"]

    for p, pdata in projects_data.items():
        pdata["cost_usd"] = round(pdata["cost_usd"], 4)
    for t, tdata in tasks_data.items():
        tdata["cost_usd"] = round(tdata["cost_usd"], 4)

    # Compile the final structured JSON
    result_summary = {
        "totals": totals,
        "projects": projects_data,
        "tasks": tasks_data,
        "sessions": sorted(sessions_data, key=lambda x: x["date"] + " " + x["start_time"], reverse=True)
    }

    # Write unified JSON summary
    summary_path = os.path.join(reports_dir, "token_metrics_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(result_summary, f, indent=2, ensure_ascii=False)
    print(f"[SUCCESS] Résumé consolidé écrit dans {summary_path}")

    # 2. Extract stats for target date to write standalone HTML report
    day_sessions = [s for s in sessions_data if s["date"] == tdate]
    day_tokens = sum(s["tokens"] for s in day_sessions)
    day_cache = sum(s["cache_hits"] for s in day_sessions)
    day_cost = sum(s["cost_usd"] for s in day_sessions)
    day_sessions_count = len(day_sessions)

    # Format numbers nicely
    if day_tokens > 1000000:
        total_tokens_str = f"{day_tokens/1000000:.2f} M"
        cache_hits_str = f"{day_cache/1000000:.2f} M"
    elif day_tokens > 0:
        total_tokens_str = f"{day_tokens/1000:.1f} K"
        cache_hits_str = f"{day_cache/1000:.1f} K"
    else:
        total_tokens_str = "0"
        cache_hits_str = "0"
        
    sessions_list_html = ""
    if day_sessions_count == 0:
        sessions_list_html = '<div class="no-sessions">Aucune session active enregistrée pour cette journée.</div>'
    else:
        for s in day_sessions:
            total_steps = s["turns"]
            tasks_list = ", ".join(s["tasks"])
            cost_str = f"${s['cost_usd']:.2f}"
            cache_pct = int((s["cache_hits"] / s["tokens"] * 100)) if s["tokens"] > 0 else 0
            
            sessions_list_html += f"""
            <div class="session-item">
                <div class="session-info">
                    <div class="session-icon"></div>
                    <div>
                        <div class="session-id">{s['id']}</div>
                        <div class="session-meta">Activité : {s['start_time']} - {s['end_time']} ({s['duration']}) | {total_steps} tours | Tâches : {tasks_list}</div>
                    </div>
                </div>
                <div class="session-metrics">
                    <div>{s['tokens']:,} tokens</div>
                    <div style="font-size: 11px; color: var(--text-secondary); margin-top: 2px;">Coût : {cost_str} | Cache : {cache_pct}%</div>
                </div>
            </div>
            """

    # HTML Template (Premium Aesthetics with USD costs)
    html_template = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rapport de Tokens DEV_CORE — {date}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-gradient: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
            --panel-bg: rgba(30, 41, 59, 0.7);
            --border-glow: rgba(99, 102, 241, 0.2);
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --accent-primary: #6366f1;
            --accent-secondary: #4f46e5;
            --success: #10b981;
        }}

        body {{
            font-family: 'Outfit', sans-serif;
            background: var(--bg-gradient);
            color: var(--text-primary);
            min-height: 100vh;
            margin: 0;
            padding: 40px 20px;
            display: flex;
            justify-content: center;
            align-items: center;
        }}

        .container {{
            max-width: 800px;
            width: 100%;
            background: var(--panel-bg);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 24px;
            padding: 40px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5),
                        0 0 40px 0 var(--border-glow);
            position: relative;
            overflow: hidden;
        }}

        .container::before {{
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(99, 102, 241, 0.05) 0%, transparent 70%);
            pointer-events: none;
            z-index: 0;
        }}

        header {{
            position: relative;
            z-index: 1;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            padding-bottom: 24px;
            margin-bottom: 32px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .logo-section h1 {{
            font-size: 28px;
            font-weight: 700;
            margin: 0;
            background: linear-gradient(to right, #a5b4fc, #6366f1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.5px;
        }}

        .logo-section p {{
            font-size: 14px;
            color: var(--text-secondary);
            margin: 4px 0 0 0;
        }}

        .date-badge {{
            background: rgba(99, 102, 241, 0.15);
            border: 1px solid rgba(99, 102, 241, 0.3);
            border-radius: 12px;
            padding: 8px 16px;
            font-size: 14px;
            font-weight: 600;
            color: #c7d2fe;
            font-family: 'JetBrains Mono', monospace;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 20px;
            margin-bottom: 32px;
            position: relative;
            z-index: 1;
        }}

        .stat-card {{
            background: rgba(15, 23, 42, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.04);
            border-radius: 18px;
            padding: 24px;
            text-align: center;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
        }}

        .stat-card:hover {{
            transform: translateY(-5px);
            border-color: rgba(99, 102, 241, 0.4);
            box-shadow: 0 10px 20px -10px rgba(99, 102, 241, 0.3);
            background: rgba(15, 23, 42, 0.6);
        }}

        .stat-value {{
            font-size: 32px;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 6px;
            letter-spacing: -1px;
        }}

        .stat-card:nth-child(1) .stat-value {{
            background: linear-gradient(to bottom, #ffffff, #818cf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .stat-card:nth-child(2) .stat-value {{
            background: linear-gradient(to bottom, #ffffff, #34d399);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .stat-card:nth-child(3) .stat-value {{
            background: linear-gradient(to bottom, #ffffff, #fbbf24);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .stat-card:nth-child(4) .stat-value {{
            background: linear-gradient(to bottom, #ffffff, #cbd5e1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .stat-label {{
            font-size: 11px;
            font-weight: 600;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        .sessions-section {{
            position: relative;
            z-index: 1;
            background: rgba(15, 23, 42, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.04);
            border-radius: 18px;
            padding: 24px;
        }}

        .sessions-section h2 {{
            font-size: 16px;
            font-weight: 600;
            margin: 0 0 16px 0;
            color: #e2e8f0;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .sessions-list {{
            display: flex;
            flex-direction: column;
            gap: 12px;
        }}

        .session-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 14px 18px;
            background: rgba(30, 41, 59, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.03);
            border-radius: 14px;
            transition: all 0.2s ease;
        }}

        .session-item:hover {{
            background: rgba(30, 41, 59, 0.6);
            border-color: rgba(255, 255, 255, 0.08);
        }}

        .session-info {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .session-icon {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--accent-primary);
            box-shadow: 0 0 8px var(--accent-primary);
        }}

        .session-id {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 13px;
            color: #cbd5e1;
        }}

        .session-meta {{
            font-size: 12px;
            color: var(--text-secondary);
            margin-top: 2px;
        }}

        .session-metrics {{
            font-size: 13px;
            font-weight: 500;
            color: #cbd5e1;
            background: rgba(255, 255, 255, 0.05);
            padding: 6px 12px;
            border-radius: 8px;
            font-family: 'JetBrains Mono', monospace;
            text-align: right;
        }}

        .no-sessions {{
            text-align: center;
            color: var(--text-secondary);
            padding: 30px 0;
            font-style: italic;
        }}

        footer {{
            margin-top: 32px;
            border-top: 1px solid rgba(255, 255, 255, 0.08);
            padding-top: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 12px;
            color: var(--text-secondary);
            position: relative;
            z-index: 1;
        }}

        .footer-tag {{
            background: rgba(255, 255, 255, 0.05);
            padding: 4px 8px;
            border-radius: 6px;
            font-family: 'JetBrains Mono', monospace;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo-section">
                <h1>DEV_CORE</h1>
                <p>Rapport d'activité & consommation tokens</p>
            </div>
            <div class="date-badge">{date}</div>
        </header>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{total_tokens}</div>
                <div class="stat-label">Tokens Totaux</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{cache_hits}</div>
                <div class="stat-label">Cache Hits</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${cost_usd:.2f}</div>
                <div class="stat-label">Coût Estimé (USD)</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{num_sessions}</div>
                <div class="stat-label">Sessions Actives</div>
            </div>
        </div>

        <div class="sessions-section">
            <h2>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="color:var(--accent-primary)"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>
                Détail des Sessions du jour
            </h2>
            <div class="sessions-list">
                {sessions_list_html}
            </div>
        </div>

        <footer>
            <span>Auto-généré par <code>endday.ps1</code> & <code>token_report.py</code></span>
            <span class="footer-tag">DEV_CORE v9.0</span>
        </footer>
    </div>
</body>
</html>"""

    report_html = html_template.format(
        date=tdate,
        total_tokens=total_tokens_str,
        cache_hits=cache_hits_str,
        cost_usd=day_cost,
        num_sessions=day_sessions_count,
        sessions_list_html=sessions_list_html
    )

    report_path = os.path.join(reports_dir, f"{tdate}-report.html")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_html)

    print(f"[SUCCESS] Rapport de tokens HTML généré pour {tdate} -> {report_path}")

if __name__ == "__main__":
    main()
