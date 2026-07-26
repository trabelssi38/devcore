# dc.py -- DEV_CORE central CLI dispatcher
import argparse
import sys
import os
import json
import time
import socket
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# Setup paths to import devcore package
SCRIPT_DIR = Path(__file__).resolve().parent
DEV_CORE = SCRIPT_DIR.parent
TOOLS_DIR = DEV_CORE / "Tools"

if str(TOOLS_DIR) not in sys.path:
    sys.path.append(str(TOOLS_DIR))

# Safe import of paths
try:
    from devcore.paths import get_paths
    DEV_CORE_PATHS = get_paths()
except ImportError:
    DEV_CORE_PATHS = None

# ANSI colors helper
def print_color(text, color="gray"):
    colors = {
        "cyan": "\033[96m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "red": "\033[91m",
        "magenta": "\033[95m",
        "white": "\033[97m",
        "gray": "\033[90m",
        "darkgray": "\033[90m",
        "reset": "\033[0m"
    }
    if os.name == 'nt':
        os.system('')
    sys.stdout.write(f"{colors.get(color, colors['gray'])}{text}{colors['reset']}\n")

def get_active_project():
    # Cache lookup
    current_pwd = os.getcwd()
    if os.environ.get("DEVCORE_ACTIVE_PROJECT_PWD") == current_pwd:
        cached_name = os.environ.get("DEVCORE_ACTIVE_PROJECT_NAME")
        if cached_name:
            return cached_name

    project_name = None
    try:
        # Get git root parent name
        git_dir = subprocess.check_output(
            ["git", "rev-parse", "--git-common-dir"],
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
        abs_git = os.path.abspath(git_dir)
        if abs_git.endswith(".git"):
            project_name = os.path.basename(os.path.dirname(abs_git))
        else:
            project_name = os.path.basename(abs_git)
    except Exception:
        pass

    if not project_name:
        project_name = os.path.basename(current_pwd)

    # Exclude system folders
    system_dirs = {"Documents", "Desktop", "Downloads", "OneDrive", "System32", "Users", "Windows", "Temp", "AppData", "Local"}
    if project_name in system_dirs:
        project_name = "devcore"

    # Replace bad characters
    project_name = "".join(c if c not in '\\/:*?"<>|' else '_' for c in project_name)

    # Set cache env vars
    os.environ["DEVCORE_ACTIVE_PROJECT_PWD"] = current_pwd
    os.environ["DEVCORE_ACTIVE_PROJECT_NAME"] = project_name
    return project_name

def get_data_root():
    return Path(os.environ.get("DEVCORE_DATA_ROOT", str(Path(__file__).resolve().parents[2] / "DEV_CORE_DATA")))

def get_platform_title():
    try:
        plat_json = DEV_CORE / "Config" / "platform.json"
        if plat_json.exists():
            data = json.loads(plat_json.read_text(encoding="utf-8-sig"))
            return f"{data.get('name', 'DEV_CORE')} v{data.get('version', '10.0')}"
    except Exception:
        pass
    return "DEV_CORE v10.0"

def resolve_routing_profile(mode):
    # Fallback default
    profile = {
        "requested_mode": mode,
        "mode": "coding",
        "budget": "8k tokens",
        "profile": "implementation",
        "model": "gemini-2.5-pro",
        "gemini_model": "gemini-2.5-pro",
        "codex_behavior": "implementation",
        "hint": "Skill dev-methodology. TDD. Commit [T-XX] apres chaque etape validee."
    }

    try:
        routing_json = DEV_CORE / "Config" / "routing_profiles.json"
        capability_json = DEV_CORE / "Config" / "ai_capability_registry.json"

        if routing_json.exists():
            r_data = json.loads(routing_json.read_text(encoding="utf-8-sig"))
            requested = mode.lower().strip() if mode else r_data.get("default_mode", "coding")
            
            # Resolve alias
            resolved = requested
            if "aliases" in r_data and requested in r_data["aliases"]:
                resolved = r_data["aliases"][requested]
            
            if "profiles" in r_data and resolved in r_data["profiles"]:
                p_data = r_data["profiles"][resolved]
                profile["mode"] = p_data.get("mode", "coding")
                profile["budget"] = p_data.get("budget", "8k tokens")
                profile["profile"] = p_data.get("profile", "implementation")
                profile["model"] = p_data.get("model", "gemini-2.5-pro")
                profile["gemini_model"] = p_data.get("gemini_model", "gemini-2.5-pro")
                profile["codex_behavior"] = p_data.get("codex_behavior", "implementation")
                profile["hint"] = p_data.get("hint", "")

        # Try capability registry override
        if capability_json.exists():
            c_data = json.loads(capability_json.read_text(encoding="utf-8-sig"))
            candidate_id = "devcore-coding"
            
            # Resolve candidate id
            req_model = profile["model"].lower().strip()
            if "aliases" in c_data and req_model in c_data["aliases"]:
                candidate_id = c_data["aliases"][req_model]
            elif "candidates" in c_data and req_model in c_data["candidates"]:
                candidate_id = req_model
            elif "mode_defaults" in c_data and profile["mode"] in c_data["mode_defaults"]:
                candidate_id = c_data["mode_defaults"][profile["mode"]]
            else:
                candidate_id = c_data.get("default_candidate", "devcore-coding")
            
            if "candidates" in c_data and candidate_id in c_data["candidates"]:
                candidate = c_data["candidates"][candidate_id]
                if candidate.get("enabled", True):
                    profile["gemini_model"] = candidate.get("backend_model", profile["gemini_model"])
    except Exception:
        pass

    return profile

def publish_event(event_type, task, payload=None):
    if payload is None:
        payload = {}
    event_bus = SCRIPT_DIR / "event_bus.ps1"
    if not event_bus.exists():
        return
    try:
        project = get_active_project()
        task_id = task.get("id", "")
        corr_id = f"{project}-{task_id}-{event_type}"
        
        event_payload = {
            "id": task_id,
            "title": task.get("title", ""),
            "mode": task.get("mode", "coding"),
            "status": task.get("status", ""),
            "steps_done": task.get("steps_done", 0),
            "steps_total": task.get("steps_total", 1)
        }
        event_payload.update(payload)
        payload_str = json.dumps(event_payload)
        
        # Publish using Powershell to reuse logic cleanly
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File",
             str(event_bus), "-Action", "Publish", "-Id", corr_id, "-Source", "task_service",
             "-Project", project, "-TaskId", task_id, "-EventType", event_type, "-CorrelationId", corr_id,
             "-PayloadJson", payload_str],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except Exception:
        pass

def cmd_next_task(args):
    project = get_active_project()
    data_root = get_data_root()
    proj_dir = data_root / "Memory" / project
    tasks_file = proj_dir / "tasks.json"

    if not tasks_file.exists():
        print_color("  Aucun tasks.json -- dc new task 'titre'", "yellow")
        sys.exit(0)

    try:
        board = json.loads(tasks_file.read_text(encoding="utf-8-sig"))
    except Exception as e:
        print_color(f"  Erreur lors de la lecture de tasks.json: {e}", "red")
        sys.exit(1)

    tasks = board.get("tasks", [])
    current = next((t for t in tasks if t.get("status") == "active"), None)

    # Transition from todo to active if none active
    if not current:
        done_ids = {t["id"] for t in tasks if t.get("status") == "done"}
        current = next((t for t in tasks if t.get("status") == "todo" and 
                        (not t.get("depends_on") or t["depends_on"] in done_ids)), None)
        if current:
            current["status"] = "active"
            current["started_at"] = datetime.now().isoformat()
            board["current_task"] = current["id"]
            
            # Save board
            tasks_file.write_text(json.dumps(board, indent=4), encoding="utf-8-sig")
            # Publish TaskStarted event
            publish_event("TaskStarted", current, {"started_at": current["started_at"]})

    if not current:
        done_count = sum(1 for t in tasks if t.get("status") == "done")
        total_count = len(tasks)
        if done_count == total_count and total_count > 0:
            print_color("  Toutes les taches accomplies !", "green")
        else:
            print_color("  Aucune tache disponible -- verifier les dependances (dc ts)", "yellow")

        # Write empty session context
        proj_dir.mkdir(parents=True, exist_ok=True)
        logs_dir = data_root / "Logs" / "scripts"
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        ctx_txt = f"[DEV_CORE] Aucune tache active\n[DEV_CORE] Toutes les taches accomplies : {done_count}/{total_count}\n[DEV_CORE] Commencer par: dc new task 'description' -mode reasoning|coding|bulk"
        (logs_dir / "session_context.txt").write_text(ctx_txt, encoding="utf-8-sig")
        (proj_dir / "session_context.txt").write_text(ctx_txt, encoding="utf-8-sig")

        ctx_toon = f"session:\n  active_task: null\n  status: no_active_task\n  done: {done_count}\n  total: {total_count}\n  project: {board.get('project', project)}"
        (logs_dir / "session_context.toon").write_text(ctx_toon, encoding="utf-8-sig")
        (proj_dir / "session_context.toon").write_text(ctx_toon, encoding="utf-8-sig")
        sys.exit(0)

    # Toonify task board to keep compat
    try:
        toonify_script = SCRIPT_DIR / "toonify.ps1"
        if toonify_script.exists():
            subprocess.run(["powershell", "-NoProfile", "-Command", f"& '{toonify_script}' -InputFile '{tasks_file}'"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

    # Resolve routing profile details
    routing = resolve_routing_profile(current.get("mode", "coding"))
    next_task = next((t for t in tasks if t.get("status") == "todo" and t.get("id") != current["id"]), None)

    # ASCII Display
    print("")
    print_color("  +------------------------------------------+", "cyan")
    print_color(f"  |  TASK {current['id'].ljust(35)}|", "cyan")
    print_color("  +------------------------------------------+", "cyan")
    print_color(f"  |  {current.get('title', '').ljust(40)}  |", "white")
    print_color("  +------------------------------------------+", "cyan")
    print_color(f"  |  Mode   : {current.get('mode', 'coding').ljust(31)}|", "gray")
    print_color(f"  |  Budget : {routing['budget'].ljust(31)}|", "gray")
    print_color(f"  |  Profile: {routing['profile'].ljust(31)}|", "gray")
    steps_str = f"{current.get('steps_done', 0)}/{current.get('steps_total', 1)}"
    print_color(f"  |  Steps  : {steps_str.ljust(31)}|", "gray")
    if next_task:
        next_str = f"{next_task['id']} [{next_task.get('mode', 'coding')}]"
        print_color(f"  |  Suivant: {next_str.ljust(31)}|", "darkgray")
    print_color("  +------------------------------------------+", "cyan")
    print("")
    if routing.get("hint"):
        print_color(f"  Hint : {routing['hint']}", "darkgray")
        print("")

    # Write session context files
    ctx_txt = (
        f"[DEV_CORE] Task active : {current['id']}\n"
        f"[DEV_CORE] Titre  : {current.get('title', '')}\n"
        f"[DEV_CORE] Mode   : {current.get('mode', 'coding')}\n"
        f"[DEV_CORE] Profile: {routing['profile']}\n"
        f"[DEV_CORE] Budget : {routing['budget']}\n"
        f"[DEV_CORE] Model  : {routing['model']}\n"
        f"[DEV_CORE] Gemini : {routing['gemini_model']}\n"
        f"[DEV_CORE] Codex  : {routing['codex_behavior']}\n"
        f"[DEV_CORE] Steps  : {steps_str}\n"
        f"[DEV_CORE] Tag git: [{current['id']}]"
    )
    logs_dir = data_root / "Logs" / "scripts"
    logs_dir.mkdir(parents=True, exist_ok=True)
    proj_dir.mkdir(parents=True, exist_ok=True)

    (logs_dir / "session_context.txt").write_text(ctx_txt, encoding="utf-8-sig")
    (proj_dir / "session_context.txt").write_text(ctx_txt, encoding="utf-8-sig")

    ctx_toon = (
        f"session:\n"
        f"  active_task: {current['id']}\n"
        f"  title: {current.get('title', '')}\n"
        f"  mode: {current.get('mode', 'coding')}\n"
        f"  resolved_mode: {routing['mode']}\n"
        f"  profile: {routing['profile']}\n"
        f"  budget: {routing['budget']}\n"
        f"  model: {routing['model']}\n"
        f"  gemini_model: {routing['gemini_model']}\n"
        f"  codex_behavior: {routing['codex_behavior']}\n"
        f"  steps_done: {current.get('steps_done', 0)}\n"
        f"  steps_total: {current.get('steps_total', 1)}\n"
        f"  git_tag: [{current['id']}]\n"
        f"  project: {board.get('project', project)}"
    )
    (logs_dir / "session_context.toon").write_text(ctx_toon, encoding="utf-8-sig")
    (proj_dir / "session_context.toon").write_text(ctx_toon, encoding="utf-8-sig")

    # Generate dashboard
    try:
        gen_db = SCRIPT_DIR / "gen_dashboard.ps1"
        if gen_db.exists():
            subprocess.run(["powershell", "-NoProfile", "-Command", f"& '{gen_db}'"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

def ping_tcp(host, port, timeout=1.0):
    try:
        socket.setdefaulttimeout(timeout)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False

def ping_http(url, timeout=2.0):
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={'User-Agent': 'DEV_CORE Doctor'})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status == 200
    except Exception:
        return False

def cmd_doctor(args):
    print("")
    print_color(f"  {get_platform_title()} -- Diagnostic autonomie (Python Native)", "cyan")
    print_color("  =======================================", "darkgray")
    print("")

    ok_count, warn_count, fail_count = 0, 0, 0

    def check(label, is_ok, fix_hint=""):
        nonlocal ok_count, warn_count, fail_count
        if is_ok == "OK":
            print_color(f"  [OK]   {label}", "green")
            ok_count += 1
        elif is_ok == "WARN":
            print_color(f"  [WARN] {label}", "yellow")
            if fix_hint:
                print_color(f"         Fix : {fix_hint}", "darkgray")
            warn_count += 1
        else:
            print_color(f"  [FAIL] {label}", "red")
            if fix_hint:
                print_color(f"         Fix : {fix_hint}", "darkgray")
            fail_count += 1

    # 1. Env Vars
    platform_root = os.environ.get("DEVCORE_PLATFORM_ROOT")
    check("DEVCORE_PLATFORM_ROOT defini", "OK" if platform_root else "WARN", "Relancer setup.ps1")
    data_root = os.environ.get("DEVCORE_DATA_ROOT")
    check("DEVCORE_DATA_ROOT defini", "OK" if data_root else "WARN", "Relancer setup.ps1")

    # 2. Critical Dirs
    data_path = get_data_root()
    dirs = {
        "Memory": data_path / "Memory",
        "Logs/scripts": data_path / "Logs" / "scripts",
        "Backups/auto": data_path / "Backups" / "auto",
        "Sessions": data_path / "Sessions"
    }
    for name, p in dirs.items():
        check(f"Dossier {name} present", "OK" if p.exists() else "WARN", f"mkdir {p}")

    # 3. DB & FTS5 Check
    db_file = data_path / "Memory" / "conversations.db"
    if db_file.exists():
        check("Base SQLite conversations.db trouvee", "OK")
        fts_ok = False
        try:
            conn = sqlite3.connect(str(db_file))
            c = conn.cursor()
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='conversations_fts';")
            if c.fetchone():
                fts_ok = True
            conn.close()
        except Exception:
            pass
        check("Table FTS5 SQLite conversations_fts OK", "OK" if fts_ok else "FAIL", "Relancer init_conversations_db.py")
    else:
        check("Base SQLite conversations.db absente", "FAIL", "python DEV_CORE/Scripts/init_conversations_db.py")

    # 4. Config & Embedding Mismatch
    emb_json = DEV_CORE / "Config" / "embedding.json"
    if emb_json.exists():
        try:
            cfg = json.loads(emb_json.read_text(encoding="utf-8-sig"))
            model = cfg.get("model")
            q_model = cfg.get("query_model")
            if model and q_model and model != q_model:
                check(f"Coherence embedding model: storage ({model}) != query ({q_model})", "WARN", "Modifier Config/embedding.json pour unifier les modeles")
            else:
                check("Coherence embedding model unifie OK", "OK")
        except Exception as e:
            check(f"Fichier embedding.json corrompu: {e}", "FAIL")
    else:
        check("Fichier Config/embedding.json absent", "WARN")

    # 5. Client hooks
    user_profile = os.environ.get("USERPROFILE", "")
    hook_checks = {
        ".claude": os.path.join(user_profile, ".claude", "settings.json"),
        ".gemini": os.path.join(user_profile, ".gemini", "settings.json")
    }
    for client, path in hook_checks.items():
        if os.path.exists(path):
            try:
                data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
                if "hooks" in data and any(h in str(data["hooks"]) for h in ["BeforeAgent", "UserPromptSubmit"]):
                    check(f"{client} hooks OK", "OK")
                else:
                    check(f"{client} hooks manquants", "FAIL", "install_universal_hooks.ps1")
            except Exception:
                check(f"{client} settings.json corrompu", "FAIL", "install_universal_hooks.ps1")
        else:
            check(f"{client} settings.json absent", "FAIL", "install_universal_hooks.ps1")

    # 6. Critical Scripts
    scripts = ["session_start.ps1", "session_end.ps1", "post_tool_hook.ps1", "task_next.ps1", "task_done.ps1", "task_step_done.ps1", "launch.ps1"]
    for s in scripts:
        check(f"Script {s} present", "OK" if (SCRIPT_DIR / s).exists() else "FAIL", "Restaurer DEV_CORE")

    # 7. Secrets scan
    sec_scan = SCRIPT_DIR / "secret_scan.ps1"
    if sec_scan.exists():
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File",
                 str(sec_scan), "-Path", os.getcwd(), "-Quiet"],
                capture_output=True
            )
            check("Secrets hardcodes absents des fichiers suivis", "OK" if res.returncode == 0 else "FAIL")
        except Exception:
            check("Echec de l'execution du secret scan", "WARN")
    else:
        check("Script secret_scan.ps1 absent", "FAIL")

    # 8. Tasks board integrity
    project = get_active_project()
    t_file = data_path / "Memory" / project / "tasks.json"
    if t_file.exists():
        try:
            board = json.loads(t_file.read_text(encoding="utf-8-sig"))
            active = next((t for t in board.get("tasks", []) if t.get("status") == "active"), None)
            if active:
                check(f"Task active: {active['id']} ({active.get('steps_done', 0)}/{active.get('steps_total', 1)})", "OK")
                
                # Check corruption
                corrupt = [t for t in board.get("tasks", []) if t.get("status") == "done" and t.get("steps_done", 0) < t.get("steps_total", 1)]
                if corrupt:
                    check(f"Corruption: {len(corrupt)} taches completed mais non validees", "WARN", "Lancer dc task status")
                else:
                    check("Integrite des taches completed OK", "OK")
            else:
                check("Aucune task active", "WARN", "dc next task")
        except Exception:
            check("tasks.json illisible", "FAIL")
    else:
        check("tasks.json absent", "WARN", "dc new task [nom]")

    # 9. Services & Ports check
    services = {
        "PostgreSQL (Port 5432)": ("127.0.0.1", 5432, "tcp"),
        "Qdrant (Port 6333)": ("http://localhost:6333/collections", 6333, "http"),
        "Gemini Router (Port 20130)": ("http://localhost:20130/v1/models", 20130, "http"),
        "FastAPI API (Port 20131)": ("http://localhost:20131/api/v1/health", 20131, "http"),
        "Repowise (Port 7337)": ("127.0.0.1", 7337, "tcp")
    }

    for name, (addr, port, p_type) in services.items():
        is_up = False
        if p_type == "http":
            is_up = ping_http(addr)
        else:
            is_up = ping_tcp(addr, port)
        
        check(f"Service {name} accessible", "OK" if is_up else "WARN", f"Verifier le conteneur ou demarrer le service")

    # Final summary
    print("")
    print_color("  =======================================", "darkgray")
    total_checks = ok_count + warn_count + fail_count
    summary_str = f"  OK: {ok_count}  |  WARN: {warn_count}  |  FAIL: {fail_count}"
    print_color(summary_str, "white")
    print("")
    if fail_count > 0:
        print_color("  FAIL a corriger -- dc check --fix pour auto-reparer", "red")
    elif warn_count > 0:
        print_color("  Quasi pret -- resoudre les avertissements", "yellow")
    else:
        print_color("  100% operationnel -- autonomie complete", "green")
    print("")

def cmd_benchmark(args):
    print("")
    print_color("  DEV_CORE Benchmark -- Operations de base", "cyan")
    print_color("  =======================================", "darkgray")
    print("")

    # Benchmark disk speed
    temp_file = Path("C:/devcore/DEV_CORE_DATA/temp_bench.dat")
    try:
        data_block = b"x" * 1024 * 1024  # 1MB
        t0 = time.perf_counter()
        temp_file.write_bytes(data_block)
        write_time = time.perf_counter() - t0
        
        t0 = time.perf_counter()
        _ = temp_file.read_bytes()
        read_time = time.perf_counter() - t0
        
        temp_file.unlink()
        print_color(f"  Vitesse Ecriture 1MB : {write_time * 1000:.2f} ms", "green")
        print_color(f"  Vitesse Lecture  1MB : {read_time * 1000:.2f} ms", "green")
    except Exception as e:
        print_color(f"  Erreur benchmark Disque : {e}", "red")

    # Benchmark SQLite query
    db_path = get_data_root() / "Memory" / "conversations.db"
    if db_path.exists():
        try:
            t0 = time.perf_counter()
            conn = sqlite3.connect(str(db_path))
            c = conn.cursor()
            c.execute("SELECT count(*) FROM conversations;")
            count = c.fetchone()[0]
            conn.close()
            query_time = time.perf_counter() - t0
            print_color(f"  Lecture SQLite (Conversations={count}) : {query_time * 1000:.2f} ms", "green")
        except Exception as e:
            print_color(f"  Erreur benchmark SQLite : {e}", "red")
    print("")

def cmd_profile(args):
    print("")
    print_color("  DEV_CORE Startup Profiler", "cyan")
    print_color("  =======================================", "darkgray")
    print("")
    
    t0 = time.perf_counter()
    import argparse
    import json
    import sqlite3
    import socket
    t_imports = time.perf_counter() - t0
    
    t0 = time.perf_counter()
    proj = get_active_project()
    t_proj = time.perf_counter() - t0
    
    t0 = time.perf_counter()
    paths = get_paths() if DEV_CORE_PATHS else None
    t_paths = time.perf_counter() - t0

    print_color(f"  Temps d'import des packages : {t_imports * 1000:.2f} ms", "green")
    print_color(f"  Resolution du projet actif  : {t_proj * 1000:.2f} ms ({proj})", "green")
    print_color(f"  Resolution des chemins      : {t_paths * 1000:.2f} ms", "green")
    print("")

def cmd_scheduler_status(args):
    data_root = get_data_root()
    jobs_file = data_root / "Scheduler" / "jobs.json"
    
    print("")
    print_color("  DEV_CORE Scheduler Status", "cyan")
    print_color("  =======================================", "darkgray")
    print("")
    
    if not jobs_file.exists():
        print_color("  jobs.json non trouve -- Le scheduler n'a pas encore demarre.", "yellow")
        print("")
        sys.exit(0)
        
    try:
        jobs = json.loads(jobs_file.read_text(encoding="utf-8-sig"))
    except Exception as e:
        print_color(f"  Erreur lors de la lecture de jobs.json: {e}", "red")
        sys.exit(1)
        
    header = f"  {'Job ID'.ljust(30)} {'Enabled'.ljust(10)} {'Kind'.ljust(10)} {'Schedule'.ljust(15)} {'Next Run'.ljust(26)} {'Status'.ljust(10)} {'Completed'}"
    print_color(header, "white")
    print_color("  " + "-" * len(header.strip()), "darkgray")
    
    for job in jobs:
        jid = job.get("id", "?")
        enabled = "Yes" if job.get("enabled", True) else "No"
        sch = job.get("schedule", {})
        kind = sch.get("kind", "?")
        expr = sch.get("expr", "?")
        
        state = job.get("state", {})
        next_run = state.get("next_run_at") or "None"
        if next_run != "None":
            try:
                dt = datetime.fromisoformat(next_run)
                next_run = dt.strftime("%Y-%m-%d %H:%M:%S%z")
            except Exception:
                pass
                
        status = state.get("last_status") or "None"
        completed = str(state.get("completed", 0))
        
        status_color = "gray"
        if status == "ok":
            status_color = "green"
        elif status == "error":
            status_color = "red"
        elif status == "running":
            status_color = "yellow"
            
        line = f"  {jid.ljust(30)} {enabled.ljust(10)} {kind.ljust(10)} {expr.ljust(15)} {next_run.ljust(26)} "
        sys.stdout.write(line)
        print_color(status.ljust(10), status_color)
        sys.stdout.write(f" {completed.rjust(9)}\n")
    print("")

def main():
    parser = argparse.ArgumentParser(description="DEV_CORE CLI")
    subparsers = parser.add_subparsers(dest="command")

    # subcommand next task
    parser_nt = subparsers.add_parser("next task", aliases=["nt"])
    
    # subcommand doctor
    parser_doc = subparsers.add_parser("doctor")
    
    # subcommand benchmark
    parser_bench = subparsers.add_parser("benchmark")
    
    # subcommand profile
    parser_prof = subparsers.add_parser("profile")

    # subcommand scheduler
    parser_sched = subparsers.add_parser("scheduler")
    parser_sched.add_argument("action", choices=["status"], nargs="?", default="status")

    # Custom parsing for multi-word subcommands (e.g., 'next task')
    sys_args = sys.argv[1:]
    if len(sys_args) >= 2 and sys_args[0] == "next" and sys_args[1] == "task":
        sys_args = ["next task"] + sys_args[2:]
    elif len(sys_args) >= 1 and sys_args[0] == "nt":
        sys_args = ["next task"] + sys_args[1:]
    elif len(sys_args) >= 2 and sys_args[0] == "scheduler" and sys_args[1] == "status":
        sys_args = ["scheduler", "status"] + sys_args[2:]

    args = parser.parse_args(sys_args)

    if args.command == "next task":
        cmd_next_task(args)
    elif args.command == "doctor":
        cmd_doctor(args)
    elif args.command == "benchmark":
        cmd_benchmark(args)
    elif args.command == "profile":
        cmd_profile(args)
    elif args.command == "scheduler":
        if args.action == "status":
            cmd_scheduler_status(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
