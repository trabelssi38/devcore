# dc.py -- DEV_CORE central CLI dispatcher
import argparse
import sys
import os
import json
import time
import socket
import sqlite3
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# Handle the individual API command before historical path discovery/imports.
if __name__ == "__main__" and sys.argv[1:2] == ["individual"]:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from devcore_engine.clients.individual_cli import main as individual_main
    raise SystemExit(individual_main(sys.argv[2:]))

# Setup paths to import devcore package
SCRIPT_DIR = Path(__file__).resolve().parent
DEV_CORE = SCRIPT_DIR.parent
TOOLS_DIR = DEV_CORE / "Tools"

if str(TOOLS_DIR) not in sys.path:
    sys.path.append(str(TOOLS_DIR))

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
    # Resolve each invocation from the nearest explicit local manifest.
    if str(DEV_CORE) not in sys.path:
        sys.path.insert(0, str(DEV_CORE))
    from devcore_engine.context import project_from_directory
    return project_from_directory()


def load_scoped_legacy_board(data_path, project):
    """Read a compatibility snapshot only when it names the selected project."""
    if not project:
        return None
    board_path = data_path / "Memory" / project / "tasks.json"
    if not board_path.is_file():
        return None
    board = json.loads(board_path.read_text(encoding="utf-8-sig"))
    if not isinstance(board, dict) or board.get("project") != project:
        raise ValueError("Task board project mismatch")
    return board

def get_data_root():
    return Path(os.environ.get("DEVCORE_DATA_ROOT", str(Path(__file__).resolve().parents[2] / "DEV_CORE_DATA")))

def get_local_root():
    env_local = os.environ.get("DEVCORE_LOCAL_ROOT")
    if env_local:
        return Path(env_local)
    if os.name == "nt" and os.getenv("LOCALAPPDATA"):
        return Path(os.getenv("LOCALAPPDATA")) / "DEV_CORE_LOCAL"
    return get_data_root().parent / "DEV_CORE_DATA_local"

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
    # Workflow mode is not permission to replace a native model/provider.
    profile = {
        "requested_mode": mode, "mode": "coding", "budget": "8k tokens",
        "profile": "implementation", "model": None, "gemini_model": None,
        "route": "native", "endpoint": "http://127.0.0.1:8787/v1",
        "preserve_requested_model": True, "codex_behavior": "implementation", "hint": "",
    }
    routing_json = DEV_CORE / "Config" / "routing_profiles.json"
    if not routing_json.exists():
        return profile
    config = json.loads(routing_json.read_text(encoding="utf-8-sig"))
    requested = str(mode or config.get("default_mode", "coding")).lower().strip()
    resolved = config.get("aliases", {}).get(requested, requested)
    item = config.get("profiles", {}).get(resolved)
    if item is None:
        raise ValueError(f"Unknown routing profile: {requested}")
    profile.update(item)
    if profile["route"] == "native":
        if profile["model"] is not None or profile["gemini_model"] is not None:
            raise ValueError("Native workflow profiles must preserve the application's model")
    elif profile["route"] == "auxiliary":
        try:
            from .router.policy import validate_auxiliary, MODEL_MAP
        except ImportError:
            from router.policy import validate_auxiliary, MODEL_MAP
        validate_auxiliary({"model": profile["model"]})
        if profile["gemini_model"] != MODEL_MAP[profile["model"]]:
            raise ValueError("Auxiliary profile disagrees with the router allowlist")
    else:
        raise ValueError("Unknown route")
    expected = "http://127.0.0.1:8787/v1" if profile["route"] == "native" else "http://127.0.0.1:8789/v1"
    if profile["endpoint"] != expected:
        raise ValueError("Profile endpoint disagrees with its route")
    return profile

def publish_event(event_type, task, payload=None):
    if payload is None:
        payload = {}
    event_bus = SCRIPT_DIR / "event_bus.ps1"
    if not event_bus.exists():
        return
    try:
        project = get_active_project()
        if not project:
            return
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
    """Select the next task in local SQL without writing a shared JSON board."""
    if str(DEV_CORE) not in sys.path:
        sys.path.insert(0, str(DEV_CORE))
    from devcore_engine.context import project_from_directory, validate_project_id
    from devcore_engine.services.tasks import TaskService

    project = args.project or project_from_directory()
    if not project:
        print("Project required: --project or .devcore/project.json", file=sys.stderr)
        raise SystemExit(2)
    try:
        project = validate_project_id(project)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc

    api_url = os.environ.get("DEVCORE_API_URL")
    if os.environ.get("DEVCORE_CLIENT_MODE") == "1" and not api_url:
        print("Direct database access is forbidden in client mode; configure DEVCORE_API_URL", file=sys.stderr)
        raise SystemExit(2)

    if api_url:
        import urllib.request
        import urllib.error
        req = urllib.request.Request(
            f"{api_url.rstrip('/')}/api/v1/tasks/next",
            data=json.dumps({"project": project}).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                task = data.get("task")
                if task:
                    print(f"Active task: [{task['id']}] {task['title']}")
                else:
                    print("No pending tasks available.")
                return
        except urllib.error.HTTPError as exc:
            print(f"API error: {exc.code}", file=sys.stderr)
            raise SystemExit(1)
        except Exception as exc:
            print(f"API connection failed: {exc}", file=sys.stderr)
            raise SystemExit(1)

    service = TaskService()
    try:
        task = service.next_task(project)
    finally:
        service.conn.close()
    if task:
        print(f"Active task: [{task['id']}] {task['title']}")
    else:
        print("No pending tasks available.")

def ping_tcp(host, port, timeout=1.0):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            pass
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
    local_path = get_local_root()
    dirs = {
        "Memory": data_path / "Memory",
        "Logs/scripts": local_path / "Logs" / "scripts",
        "Backups/auto": local_path / "Backups" / "auto",
        "Sessions": local_path / "Sessions"
    }
    for name, p in dirs.items():
        check(f"Dossier {name} present", "OK" if p.exists() else "WARN", f"mkdir {p}")

    # 3. The historical shared conversation store is not a project health gate.
    check(
        "Base conversations globale non evaluee",
        "WARN",
        "Verifier une sauvegarde et la sante de l'instance active",
    )

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
    t_file = data_path / "Memory" / project / "tasks.json" if project else None
    if t_file and t_file.is_file():
        try:
            board = load_scoped_legacy_board(data_path, project)
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
    elif project:
        check("tasks.json absent", "WARN", "dc new task [nom]")
    else:
        check("Projet local introuvable", "WARN", "Ajouter .devcore/project.json")

    # 9. Services & Ports check
    services = {
        "PostgreSQL (Port 5432)": ("127.0.0.1", 5432, "tcp"),
        "Gemini Router (Port 20130)": ("http://localhost:20130/v1/models", 20130, "http"),
        "FastAPI API (Port 20131)": ("http://localhost:20131/api/v1/health", 20131, "http"),
        "Repowise (Port 7337)": ("127.0.0.1", 7337, "tcp")
    }

    # File existence and an unauthenticated HTTP probe do not establish vector readiness.
    db_file = get_local_root() / "devcore.db"
    check("Base SQLite locale presente", "OK" if db_file.is_file() else "WARN")
    qdrant_up = ping_http("http://127.0.0.1:6333/collections")
    check("Qdrant HTTP accessible", "OK" if qdrant_up else "WARN")
    check("Memoire vectorielle non evaluee", "WARN", "Verifier collections et extensions sur l'instance")

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
    return 1 if fail_count else 0

def cmd_benchmark(args):
    print("")
    print_color("  DEV_CORE Benchmark -- Operations de base", "cyan")
    print_color("  =======================================", "darkgray")
    print("")

    # Benchmark an isolated disposable directory, never an active data root.
    try:
        with tempfile.TemporaryDirectory(prefix="devcore-benchmark-") as scratch:
            temp_file = Path(scratch) / "block.dat"
            data_block = b"x" * 1024 * 1024  # 1MB
            t0 = time.perf_counter()
            temp_file.write_bytes(data_block)
            write_time = time.perf_counter() - t0
            t0 = time.perf_counter()
            _ = temp_file.read_bytes()
            read_time = time.perf_counter() - t0
        print_color(f"  Vitesse Ecriture 1MB : {write_time * 1000:.2f} ms", "green")
        print_color(f"  Vitesse Lecture  1MB : {read_time * 1000:.2f} ms", "green")
    except Exception as e:
        print_color(f"  Erreur benchmark Disque : {e}", "red")

    print_color("  SQLite : utiliser benchmark_sqlite_snapshot.py sur une sauvegarde verifiee", "yellow")
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
    _ = (get_data_root(), get_local_root(), DEV_CORE)
    t_paths = time.perf_counter() - t0

    print_color(f"  Temps d'import des packages : {t_imports * 1000:.2f} ms", "green")
    print_color(f"  Resolution du projet actif  : {t_proj * 1000:.2f} ms ({proj})", "green")
    print_color(f"  Resolution des chemins      : {t_paths * 1000:.2f} ms", "green")
    print("")

def cmd_scheduler_status(args):
    local_root = get_local_root()
    jobs_file = local_root / "Scheduler" / "jobs.json"
    
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
    subparsers.add_parser("individual", help="Explicit individual API context/tasks/done/delete")

    # subcommand next task
    parser_nt = subparsers.add_parser("next task", aliases=["nt"])
    parser_nt.add_argument("--project", help="Project ID; defaults to the local manifest")
    
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
        raise SystemExit(cmd_doctor(args))
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
