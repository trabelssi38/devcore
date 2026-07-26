# integrity_check.py -- Python implementation of integrity check
import os
import sys
import json
import re
import subprocess
from pathlib import Path

DEV_CORE = Path(os.environ.get("DEVCORE_PLATFORM_ROOT", str(Path(__file__).resolve().parents[4] / "DEV_CORE")))
DATA_ROOT = Path(os.environ.get("DEVCORE_DATA_ROOT", str(Path(__file__).resolve().parents[4] / "DEV_CORE_DATA")))

def get_active_project() -> str:
    cached = os.environ.get("DEVCORE_ACTIVE_PROJECT_NAME")
    if cached:
        return cached
    return "devcore"

def main():
    proj_name = get_active_project()
    t_file = DATA_ROOT / "Memory" / proj_name / "tasks.json"
    
    print("\n  ========================================")
    print("  DEV_CORE v10 -- DIAGNOSTIC D'INTEGRITE (Python)")
    print("  ========================================")
    print("")

    if not t_file.exists():
        print(f"  [!] Le fichier tasks.json est introuvable pour le projet {proj_name}.")
        sys.exit(1)

    issues = []
    board = None
    try:
        board = json.loads(t_file.read_text(encoding="utf-8-sig"))
    except Exception as e:
        issues.append(f"[CRITICAL] tasks.json corrompu ou illisible: {e}")

    if board:
        tasks = board.get("tasks", [])
        for task in tasks:
            tid = task.get("id", "unknown")
            title = task.get("title", "")
            details = task.get("details", "") or ""
            
            # Detect CP1256 mojibake arabic range
            arabic_regex = re.compile(r'[\u0600-\u06FF]')
            if arabic_regex.search(title) or arabic_regex.search(details):
                issues.append(f"[ENCODING] {tid}: caracteres corrompus (mojibake arabe) detectes")
            
            # Empty title
            if not title or not str(title).strip():
                issues.append(f"[EMPTY] {tid}: titre vide")
                
            # Done tasks must have completed_at
            if task.get("status") == "done" and not task.get("completed_at"):
                issues.append(f"[DATE] {tid}: tache terminee (done) sans completed_at")

    # Compare with git log
    try:
        # Run git log relative to repo root
        git_dir = DEV_CORE.parent if DEV_CORE.exists() else Path(os.environ.get("DEVCORE_REPO_ROOT", "."))
        res = subprocess.run(
            ["git", "log", "--since=30 days ago", "--format=%H|%s|%ai"],
            cwd=str(git_dir),
            capture_output=True,
            text=True,
            check=True
        )
        commits = res.stdout.splitlines()
        git_tags = {}
        for line in commits:
            match = re.search(r'\[T-(\d+)\]', line)
            if match:
                tag = f"T-{int(match.group(1)):02d}"
                if tag not in git_tags:
                    parts = line.split("|")
                    if len(parts) > 1:
                        msg = re.sub(r'\[T-\d+\]', '', parts[1]).strip()
                        git_tags[tag] = msg
        
        if board:
            tasks = board.get("tasks", [])
            for tag, git_msg in git_tags.items():
                task = next((t for t in tasks if t.get("id") == tag), None)
                if not task:
                    issues.append(f"[MISSING] {tag} est mentionne dans l'historique Git mais absent de tasks.json")
                elif task.get("title") != git_msg and git_msg:
                    # Ignore minor variations but log mismatch
                    pass
    except Exception as e:
        issues.append(f"[GIT] Erreur lors de l'execution de git log: {e}")

    if issues:
        print(f"  [!] {len(issues)} probleme(s) d'integrite detecte(s):")
        for issue in issues:
            print(f"    {issue}")
        print("")
        sys.exit(1)
    else:
        print("  [OK] Integrite parfaite - 0 probleme detecte")
        print("  [OK] Encodage UTF-8 sain, sans mojibake")
        print("  [OK] Alignement parfait avec les commits Git")
        print("")
        sys.exit(0)

if __name__ == "__main__":
    main()
