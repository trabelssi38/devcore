#!/usr/bin/env python3
"""ensure_all_repowiseignore.py -- Checks all projects in projects.json and adds .repowiseignore if missing.
"""
import os
import json
import shutil
from pathlib import Path

# Paths
PLATFORM_ROOT = Path(os.environ.get("DEVCORE_PLATFORM_ROOT", Path(__file__).resolve().parent.parent))
PROJECTS_JSON = PLATFORM_ROOT / "Config" / "projects.json"
TEMPLATE_IGNORE = PLATFORM_ROOT.parent / ".repowiseignore"

DEFAULT_IGNORE_CONTENT = """node_modules/
.git/objects/
.git/logs/
DEV_CORE_DATA/Logs/
DEV_CORE_DATA/Backups/
DEV_CORE_DATA/qdrant_storage/
DEV_CORE_DATA/Dashboard/
__pycache__/
*.log
*.pyc
*.tmp
*.bak
hermes/.venv/
.next/
dist/
build/
"""

def load_projects():
    if not PROJECTS_JSON.exists():
        print(f"[ERROR] projects.json not found at {PROJECTS_JSON}")
        return []
    try:
        data = json.loads(PROJECTS_JSON.read_text(encoding="utf-8"))
        return data.get("projects", [])
    except Exception as e:
        print(f"[ERROR] Failed to load projects.json: {e}")
        return []

def get_template_content():
    if TEMPLATE_IGNORE.exists():
        try:
            return TEMPLATE_IGNORE.read_text(encoding="utf-8")
        except Exception as e:
            print(f"[WARNING] Error reading template {TEMPLATE_IGNORE}: {e}")
    return DEFAULT_IGNORE_CONTENT

def main():
    projects = load_projects()
    if not projects:
        print("No projects loaded.")
        return

    ignore_content = get_template_content()
    created_count = 0
    skipped_count = 0
    not_found_count = 0

    print(f"Checking {len(projects)} projects...")
    for proj in projects:
        name = proj.get("name")
        path_str = proj.get("path")
        if not name or not path_str:
            continue
        
        proj_path = Path(path_str)
        if not proj_path.exists():
            print(f"  [NOT FOUND] {name} -> {proj_path}")
            not_found_count += 1
            continue

        ignore_file = proj_path / ".repowiseignore"
        if ignore_file.exists():
            print(f"  [EXISTS] {name} -> {ignore_file}")
            skipped_count += 1
        else:
            try:
                ignore_file.write_text(ignore_content, encoding="utf-8")
                print(f"  [CREATED] {name} -> {ignore_file}")
                created_count += 1
            except Exception as e:
                print(f"  [ERROR] Failed to write ignore for {name}: {e}")

    print("\nSummary:")
    print(f"  Created: {created_count}")
    print(f"  Already existed: {skipped_count}")
    print(f"  Directories not found: {not_found_count}")

if __name__ == "__main__":
    main()
