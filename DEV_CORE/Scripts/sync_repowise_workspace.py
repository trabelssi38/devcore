#!/usr/bin/env python3
"""sync_repowise_workspace.py -- Synchronizes DEV_CORE projects with Repowise workspace config.

- Auto-adds valid existing projects from DEV_CORE/Config/projects.json
- Auto-removes workspace entries whose directories no longer exist on disk
- Retains 'devcore' (path: .) as primary/default repository
"""
import os
import sys
import json
import re
from pathlib import Path

PLATFORM_ROOT = Path(os.environ.get("DEVCORE_PLATFORM_ROOT", r"C:\devcore\DEV_CORE"))
REPO_ROOT = Path(os.environ.get("DEVCORE_REPO_ROOT", r"C:\devcore"))
PROJECTS_JSON = PLATFORM_ROOT / "Config" / "projects.json"
WORKSPACE_YAML = REPO_ROOT / ".repowise-workspace.yaml"

def parse_simple_yaml(path: Path) -> dict:
    if not path.exists():
        return {
            "version": 1,
            "default_repo": "devcore",
            "repos": [{"path": ".", "alias": "devcore", "is_primary": True}]
        }
    
    content = path.read_text(encoding="utf-8")
    repos = []
    current_repo = None
    
    for line in content.splitlines():
        line_strip = line.strip()
        if line_strip.startswith("- path:"):
            if current_repo:
                repos.append(current_repo)
            path_val = line_strip.split("- path:", 1)[1].strip().strip("'\"")
            current_repo = {"path": path_val}
        elif current_repo and ":" in line_strip:
            key, val = line_strip.split(":", 1)
            key = key.strip()
            val = val.strip().strip("'\"")
            if val == "true":
                val = True
            elif val == "false":
                val = False
            current_repo[key] = val

    if current_repo:
        repos.append(current_repo)

    return {
        "version": 1,
        "default_repo": "devcore",
        "repos": repos
    }

def dump_simple_yaml(data: dict) -> str:
    lines = [
        f"version: {data.get('version', 1)}",
        f"default_repo: {data.get('default_repo', 'devcore')}",
        "repos:"
    ]
    
    for repo in data.get("repos", []):
        path_str = repo.get("path", ".")
        lines.append(f"- path: {path_str}")
        if repo.get("alias"):
            lines.append(f"  alias: {repo['alias']}")
        if repo.get("is_primary"):
            lines.append("  is_primary: true")
        if repo.get("indexed_at"):
            lines.append(f"  indexed_at: '{repo['indexed_at']}'")
        if repo.get("last_commit_at_index"):
            lines.append(f"  last_commit_at_index: {repo['last_commit_at_index']}")

    return "\n".join(lines) + "\n"

def sync_workspace():
    data = parse_simple_yaml(WORKSPACE_YAML)
    existing_repos = data.get("repos", [])
    
    # 1. Map existing entries by normalized alias and path
    repo_map = {}
    for item in existing_repos:
        repo_map[item.get("alias") or item.get("path")] = item

    # Ensure devcore primary entry exists
    if "devcore" not in repo_map:
        devcore_entry = {"path": ".", "alias": "devcore", "is_primary": True}
        existing_repos.insert(0, devcore_entry)
        repo_map["devcore"] = devcore_entry
    else:
        repo_map["devcore"]["is_primary"] = True

    # 2. Gather candidates from projects.json
    managed_projects = []
    if PROJECTS_JSON.exists():
        try:
            pdata = json.loads(PROJECTS_JSON.read_text(encoding="utf-8"))
            managed_projects = pdata.get("projects", [])
        except Exception as e:
            print(f"[SyncRepowiseWorkspace] Warning: failed to parse {PROJECTS_JSON}: {e}")

    for proj in managed_projects:
        name = proj.get("name")
        p_path_str = proj.get("path")
        if not name or not p_path_str:
            continue
            
        p_path = Path(p_path_str)
        # Verify physical existence
        if p_path.exists():
            # Check relative path
            try:
                rel_path = p_path.relative_to(REPO_ROOT).as_posix()
            except ValueError:
                rel_path = p_path.as_posix()
                
            if rel_path == ".":
                continue
                
    # 2b. Discover physical project directories on disk (e.g. C:\src)
    search_dirs = [Path(r"C:\src")]
    for sdir in search_dirs:
        if sdir.exists():
            for child in sdir.iterdir():
                if child.is_dir() and not child.name.startswith("."):
                    alias_name = child.name.replace(" ", "_").lower()
                    posix_path = child.as_posix()
                    if alias_name not in repo_map and posix_path not in repo_map:
                        new_entry = {
                            "path": posix_path,
                            "alias": alias_name
                        }
                        existing_repos.append(new_entry)
                        repo_map[alias_name] = new_entry
                        print(f"[SyncRepowiseWorkspace] Discovered physical project '{alias_name}' ({posix_path})")

                        # Also sync into projects.json if not present
                        if PROJECTS_JSON.exists():
                            try:
                                pdata = json.loads(PROJECTS_JSON.read_text(encoding="utf-8"))
                                projs = pdata.get("projects", [])
                                if not any(p.get("name") == alias_name for p in projs):
                                    projs.append({"name": alias_name, "path": posix_path})
                                    pdata["projects"] = sorted(projs, key=lambda x: x.get("name", ""))
                                    PROJECTS_JSON.write_text(json.dumps(pdata, indent=2), encoding="utf-8")
                            except Exception as e:
                                print(f"[SyncRepowiseWorkspace] Error updating projects.json: {e}")

    # 3. Prune entries whose physical directory does not exist
    filtered_repos = []
    for item in existing_repos:
        p_str = item.get("path", ".")
        alias = item.get("alias", p_str)
        
        if p_str == "." or alias == "devcore":
            filtered_repos.append(item)
            continue
            
        # Resolve path against REPO_ROOT
        full_path = (REPO_ROOT / p_str).resolve() if not Path(p_str).is_absolute() else Path(p_str)
        
        if full_path.exists():
            filtered_repos.append(item)
        else:
            print(f"[SyncRepowiseWorkspace] Removed missing project '{alias}' ({p_str})")

    data["repos"] = filtered_repos
    out_yaml = dump_simple_yaml(data)
    WORKSPACE_YAML.write_text(out_yaml, encoding="utf-8")
    print(f"[SyncRepowiseWorkspace] Workspace configuration synchronized ({len(filtered_repos)} repos active).")

if __name__ == "__main__":
    sync_workspace()
