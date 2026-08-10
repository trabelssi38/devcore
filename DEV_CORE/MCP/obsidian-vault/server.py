# MCP Server for Obsidian Vault
# Permet a Hermes de lire/ecrire des notes Obsidian

import json
from pathlib import Path
from datetime import datetime

import os
try:
    from devcore_engine.db import get_data_root
    DATA_ROOT = get_data_root()
except Exception:
    DATA_ROOT = Path(os.environ.get("DEVCORE_DATA_ROOT", "C:/devcore/DEV_CORE_DATA"))

# Obsidian vault paths
VAULT_PATH = DATA_ROOT / "Vault"
DAILY_NOTES = VAULT_PATH / "Daily Notes"
DECISIONS_PATH = VAULT_PATH / "Decisions"
LESSONS_PATH = VAULT_PATH / "Lessons"


def resolve_vault_path(file_path: str) -> Path:
    """Resolve a path and ensure it stays inside the Obsidian vault."""
    vault_root = VAULT_PATH.resolve()
    candidate = Path(file_path)
    if not candidate.is_absolute():
        candidate = vault_root / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(vault_root)
    except ValueError as exc:
        raise ValueError(f"Path escapes vault root: {vault_root}") from exc
    return resolved


def get_today_string() -> str:
    """Get today's date in YYYY-MM-DD format."""
    return datetime.now().strftime("%Y-%m-%d")


def read_file(file_path: str) -> dict:
    """Read a markdown file."""
    try:
        path = resolve_vault_path(file_path)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        return {
            "success": True,
            "path": str(path),
            "exists": True,
            "content": content,
            "size": path.stat().st_size if path.exists() else 0
        }
    except FileNotFoundError:
        return {
            "success": False,
            "path": str(file_path),
            "exists": False,
            "error": "Fichier non trouve"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def write_file(file_path: str, content: str, append: bool = False) -> dict:
    """Write to a markdown file."""
    try:
        path = resolve_vault_path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        mode = 'a' if append else 'w'
        with open(path, mode, encoding='utf-8') as f:
            f.write(content)
        return {
            "success": True,
            "path": str(path),
            "mode": "append" if append else "write",
            "size": path.stat().st_size
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def search_vault(query: str, max_results: int = 10) -> dict:
    """Simple text search in vault."""
    results = []
    try:
        vault_root = resolve_vault_path(".")
        for md_file in vault_root.rglob("*.md"):
            if md_file.name.startswith("."):
                continue
            try:
                content = md_file.read_text(encoding='utf-8')
                if query.lower() in content.lower():
                    # Extract snippet
                    idx = content.lower().find(query.lower())
                    start = max(0, idx - 50)
                    end = min(len(content), idx + len(query) + 50)
                    snippet = content[start:end].replace('\n', ' ')

                    results.append({
                        "path": str(md_file.relative_to(vault_root)),
                        "snippet": f"...{snippet}...",
                        "size": len(content)
                    })

                if len(results) >= max_results:
                    break
            except:
                continue

        return {
            "success": True,
            "query": query,
            "results_found": len(results),
            "results": results
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# Tool definitions
TOOLS = [
    {
        "name": "obsidian_daily_note_read",
        "description": "Lit la note quotidienne du jour",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Date au format YYYY-MM-DD (defaut: aujourd'hui)"
                }
            }
        }
    },
    {
        "name": "obsidian_daily_note_append",
        "description": "Ajoute du contenu a la note quotidienne",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Contenu markdown a ajouter"
                },
                "section": {
                    "type": "string",
                    "description": "Section de la note (Resume, Taches, Decisions, Lecons)",
                    "enum": ["Resume", "Taches accomplies", "Decisions", "Lecons", "Next actions"]
                },
                "date": {
                    "type": "string",
                    "description": "Date au format YYYY-MM-DD (defaut: aujourd'hui)"
                }
            },
            "required": ["content", "section"]
        }
    },
    {
        "name": "obsidian_search",
        "description": "Recherche dans tout le vault Obsidian",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Texte a rechercher"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Nombre max de resultats (defaut: 10)",
                    "default": 10
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "obsidian_create_note",
        "description": "Cree une nouvelle note dans le vault",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Chemin relatif dans le vault (ex: Decisions/2026-05-12-decision.md)"
                },
                "content": {
                    "type": "string",
                    "description": "Contenu markdown de la note"
                },
                "frontmatter": {
                    "type": "object",
                    "description": "Metadonnees frontmatter (tags, date, etc.)"
                }
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "obsidian_read_note",
        "description": "Lit une note du vault",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Chemin relatif dans le vault"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "obsidian_list_notes",
        "description": "Liste les notes dans un dossier du vault",
        "input_schema": {
            "type": "object",
            "properties": {
                "folder": {
                    "type": "string",
                    "description": "Dossier relatif (defaut: racine)",
                    "default": ""
                },
                "max_results": {
                    "type": "integer",
                    "description": "Nombre max de resultats",
                    "default": 20
                }
            }
        }
    }
]


def handle_tool_call(tool_name: str, arguments: dict) -> dict:
    """Handle tool call from Hermes."""
    date = arguments.get("date", get_today_string())

    handlers = {
        "obsidian_daily_note_read": lambda args: read_file(str(DAILY_NOTES / f"{date}.md")),

        "obsidian_daily_note_append": lambda args: write_file(
            str(DAILY_NOTES / f"{date}.md"),
            f"\n\n## {args['section']}\n{args['content']}\n",
            append=True
        ),

        "obsidian_search": lambda args: search_vault(
            args['query'],
            args.get('max_results', 10)
        ),

        "obsidian_create_note": lambda args: create_note_with_frontmatter(
            args['path'],
            args['content'],
            args.get('frontmatter')
        ),

        "obsidian_read_note": lambda args: read_file(args['path']),

        "obsidian_list_notes": lambda args: {
            "success": True,
            "folder": args.get('folder', ''),
            "files": list_notes_in_folder(args.get('folder', ''), args.get('max_results', 20))
        }
    }

    if tool_name in handlers:
        return handlers[tool_name](arguments)
    else:
        return {"error": f"Unknown tool: {tool_name}"}


def create_note_with_frontmatter(file_path: str, content: str, frontmatter: dict = None) -> dict:
    """Create a note with optional frontmatter."""
    full_content = ""
    if frontmatter:
        full_content += "---\n"
        for key, value in frontmatter.items():
            if isinstance(value, list):
                full_content += f"{key}: [{', '.join(value)}]\n"
            else:
                full_content += f"{key}: {value}\n"
        full_content += "---\n\n"

    full_content += content + "\n"
    return write_file(file_path, full_content)


def list_notes_in_folder(folder: str, max_results: int = 20) -> list:
    """List notes in a folder."""
    results = []
    try:
        vault_root = resolve_vault_path(".")
        search_path = resolve_vault_path(folder or ".")
        for md_file in search_path.rglob("*.md"):
            if md_file.name.startswith("."):
                continue
            results.append({
                "name": md_file.name,
                "path": str(md_file.relative_to(vault_root)),
                "size": md_file.stat().st_size,
                "modified": datetime.fromtimestamp(md_file.stat().st_mtime).isoformat()
            })
            if len(results) >= max_results:
                break
    except Exception as e:
        return [{"error": str(e)}]
    return results


def main():
    """Main entry point for MCP server."""
    print("Obsidian Vault MCP Server started")
    print(f"Vault path: {VAULT_PATH}")
    print(f"Daily notes: {DAILY_NOTES}")
    print(f"Decisions: {DECISIONS_PATH}")
    print(f"Lessons: {LESSONS_PATH}")
    print(f"Available tools: {len(TOOLS)}")

    vault_exists = VAULT_PATH.exists()
    print(f"Vault accessible: {vault_exists}")

    for tool in TOOLS:
        print(f"  - {tool['name']}: {tool['description']}")


if __name__ == "__main__":
    main()
