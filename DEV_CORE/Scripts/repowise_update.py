#!/usr/bin/env python3
"""repowise_update.py -- project-scoped RepoWise indexing.
Requires an explicit registered project, then triggers an index-only refresh.
"""
import argparse
import os
import sys
import json
import shutil
import subprocess
from pathlib import Path

# Paths
PLATFORM_ROOT = Path(os.environ.get("DEVCORE_PLATFORM_ROOT", str(Path(__file__).resolve().parents[2] / "DEV_CORE")))
PROJECTS_JSON = Path(os.environ.get("DEVCORE_CONFIG_ROOT", str(PLATFORM_ROOT / "Config"))) / "projects.json"
TEMPLATE_IGNORE = Path(__file__).resolve().parents[2] / ".repowiseignore"

def resolve_repowise_exe():
    user_home = Path(os.path.expanduser("~"))
    candidates = [
        user_home / "AppData" / "Roaming" / "Python" / "Python313" / "Scripts" / "repowise.exe",
        user_home / "AppData" / "Roaming" / "Python" / "Python312" / "Scripts" / "repowise.exe",
    ]
    for cand in candidates:
        if cand.exists():
            return str(cand)
    
    # Try system PATH
    system_path = shutil.which("repowise")
    if system_path:
        return system_path
        
    return "repowise"

def get_project_path(project_name):
    if PROJECTS_JSON.exists():
        try:
            config = json.loads(PROJECTS_JSON.read_text(encoding="utf-8"))
            for proj in config.get("projects", []):
                if proj.get("name") == project_name:
                    proj_path = proj.get("path")
                    if proj_path and Path(proj_path).is_absolute() and Path(proj_path).is_dir():
                        resolved = Path(proj_path).resolve()
                        manifest = resolved / ".devcore" / "project.json"
                        if manifest.is_file():
                            metadata = json.loads(manifest.read_text(encoding="utf-8-sig"))
                            if metadata.get("name") != project_name:
                                return None
                        return resolved
        except Exception as e:
            print(f"[RepowiseUpdate] Error reading projects.json: {e}")
            
    return None

def ensure_repowise_ignore(proj_path):
    ignore_file = proj_path / ".repowiseignore"
    if not ignore_file.exists():
        print(f"[RepowiseUpdate] Creating .repowiseignore in {proj_path}")
        if TEMPLATE_IGNORE.exists():
            try:
                shutil.copy2(TEMPLATE_IGNORE, ignore_file)
            except Exception as e:
                print(f"[RepowiseUpdate] Error copying ignore template: {e}")
        else:
            # Inline fallback
            content = "node_modules/\n.git/objects/\nDEV_CORE_DATA/Logs/\nDEV_CORE_DATA/Backups/\nDEV_CORE_DATA/qdrant_storage/\nDEV_CORE_DATA/Dashboard/\n__pycache__/\n*.log\n*.pyc\nhermes/.venv/\n"
            try:
                ignore_file.write_text(content, encoding="utf-8")
            except Exception as e:
                print(f"[RepowiseUpdate] Error writing ignore file: {e}")

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="Registered project ID to index")
    parser.add_argument("--refresh-dashboard", action="store_true", help="Also regenerate the shared legacy Dashboard")
    args = parser.parse_args(argv)
    project_name = args.project.strip()
    if not project_name or any(part in project_name for part in ("/", "\\", ":", "..")):
        parser.error("invalid project ID")
    proj_path = get_project_path(project_name)
    if not proj_path:
        parser.error(f"project '{project_name}' has no registered directory")

    print(f"[RepowiseUpdate] Project: {project_name} -> {proj_path}")
    ensure_repowise_ignore(proj_path)
    
    repowise_exe = resolve_repowise_exe()
    cmd = [
        repowise_exe,
        "update",
        "--index-only",
        "--no-docs",
        "--no-workspace"
    ]
    
    print(f"[RepowiseUpdate] Running: {' '.join(cmd)}")
    
    env = os.environ.copy()
    env["REPOWISE_EMBEDDER"] = "mock"
    env["REPOWISE_TELEMETRY_DISABLED"] = "1"
    
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if os.name == "nt" else 0
    try:
        # Run with a 120s timeout to prevent locking up
        result = subprocess.run(
            cmd,
            cwd=str(proj_path),
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
            creationflags=creationflags
        )
        print(result.stdout)
        if result.returncode != 0:
            print(f"[RepowiseUpdate] ERROR (exit code {result.returncode}):", file=sys.stderr)
            print(result.stderr, file=sys.stderr)
            sys.exit(result.returncode)
        else:
            print("[RepowiseUpdate] Repowise index updated successfully.")
    except subprocess.TimeoutExpired:
        print("[RepowiseUpdate] ERROR: Repowise update timed out after 120s", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[RepowiseUpdate] ERROR running repowise: {e}", file=sys.stderr)
        sys.exit(1)

    # Régénérer le dashboard APRÈS le scan Repowise pour avoir des données fraîches.
    # Le lock dans gen_dashboard.py sérialise automatiquement les appels concurrents
    # (task_sync.ps1 peut déjà avoir lancé une génération — elle se terminera d'abord).
    if args.refresh_dashboard and os.environ.get("DEVCORE_SKIP_DASHBOARD") != "1":
        gen_dash = Path(__file__).resolve().parent / "gen_dashboard.py"
        if gen_dash.exists():
            print("[RepowiseUpdate] Triggering dashboard regeneration after Repowise scan...")
            try:
                subprocess.run(
                    [sys.executable, str(gen_dash), "--skip-token-refresh"],
                    cwd=str(proj_path),
                    timeout=60,
                    creationflags=creationflags
                )
                print("[RepowiseUpdate] Dashboard regenerated successfully.")
            except subprocess.TimeoutExpired:
                print("[RepowiseUpdate] WARNING: Dashboard regeneration timed out.", file=sys.stderr)
            except Exception as e:
                print(f"[RepowiseUpdate] WARNING: Could not regenerate dashboard: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()

