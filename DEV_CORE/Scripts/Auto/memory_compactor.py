# memory_compactor.py -- LLM-assisted memory compaction for DEV_CORE
import os
import re
import sys
import json
import argparse
import tempfile
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

PLATFORM_ROOT = Path(os.environ.get("DEVCORE_PLATFORM_ROOT", str(Path(__file__).resolve().parents[4] / "DEV_CORE")))
DATA_ROOT = Path(os.environ.get("DEVCORE_DATA_ROOT", str(Path(__file__).resolve().parents[4] / "DEV_CORE_DATA")))
AUXILIARY_URL = "http://127.0.0.1:8789/v1/chat/completions"

PROJECT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")


def project_lessons_paths(project_id: str) -> tuple[Path, Path]:
    if not isinstance(project_id, str) or not PROJECT_ID_RE.fullmatch(project_id):
        raise ValueError("A simple project id is required")
    if not DATA_ROOT.is_absolute():
        raise ValueError("DEVCORE_DATA_ROOT must be absolute")
    project_root = DATA_ROOT / "Memory" / project_id
    return project_root / "LESSONS.md", project_root / "archive"


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=path.parent,
                                         prefix=f".{path.name}.", suffix=".tmp", delete=False) as stream:
            temp_path = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def create_backup(lessons_path: Path, archive_dir: Path):
    if not lessons_path.exists():
        print("[memory_compactor] LESSONS.md not found, skipping backup.")
        return None
    today_str = datetime.now().strftime("%Y-%m-%d_%H%M%S_%f")
    backup_path = archive_dir / f"LESSONS_pre_compaction_{today_str}.md"
    content = lessons_path.read_text(encoding="utf-8")
    atomic_write_text(backup_path, content)
    print(f"[memory_compactor] Backup created at: {backup_path}")
    return backup_path

def call_llm_compaction(section_title: str, lines: list) -> list:
    prompt = f"""Tu es un compacteur de mémoire d'agent IA expert.
Voici une liste de leçons extraites de la section '{section_title}' d'un fichier de mémoire d'ingénierie.
Ta mission est de :
1. Fusionner les leçons redondantes ou très similaires.
2. Synthétiser et reformuler pour obtenir un maximum de 5 leçons concises et à haute valeur ajoutée.
3. Pour chaque leçon finale, conserver le format strict : '- [score: 0.8] [created: YYYY-MM-DD] [tag:...] Texte de la leçon'.
4. Conserver les tags pertinents et attribuer un score réaliste (entre 0.5 et 0.95).

Leçons à compacte :
""" + "\n".join(lines) + """

Format de réponse attendu : Retourne UNIQUEMENT la liste des leçons sous forme de puces markdown ('- [score: ...] ...'), sans aucun texte d'introduction ni d'explication.
"""

    payload = {
        "model": "devcore-summary",
        "task_type": "summary",
        "fallback_providers": [],
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }

    try:
        req = urllib.request.Request(
            AUXILIARY_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        # Do not inherit an HTTP proxy or follow a redirect to another provider.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        with opener.open(req, timeout=30) as resp:
            raw = resp.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024:
                raise ValueError("Compaction response exceeds 1 MiB")
            data = json.loads(raw.decode("utf-8"))
            content = data["choices"][0]["message"]["content"].strip()
            compacted_lines = [line.strip() for line in content.splitlines() if line.strip().startswith("-")]
            if compacted_lines:
                return compacted_lines
    except Exception as e:
        print(f"[memory_compactor] Warning: LLM compaction failed for section '{section_title}': {e}")
    
    return lines  # Fallback to original if LLM call fails

def compact_lessons_file(project_id: str):
    lessons_path, archive_dir = project_lessons_paths(project_id)
    lessons_path.parent.mkdir(parents=True, exist_ok=True)
    if not lessons_path.exists():
        print("[memory_compactor] LESSONS.md does not exist.")
        return

    create_backup(lessons_path, archive_dir)

    raw_text = lessons_path.read_text(encoding="utf-8")
    lines = raw_text.splitlines()

    header_lines = []
    sections = {}
    current_section = "General"
    sections[current_section] = []

    for line in lines:
        if line.startswith("# ") or line.startswith("<!--"):
            header_lines.append(line)
        elif line.startswith("## "):
            current_section = line[3:].strip()
            if current_section not in sections:
                sections[current_section] = []
        else:
            if line.strip():
                sections[current_section].append(line)

    compacted_content = []
    if header_lines:
        compacted_content.extend(header_lines)
        compacted_content.append("")

    total_compacted = 0
    for sec_title, sec_lines in sections.items():
        if sec_title != "General":
            compacted_content.append(f"## {sec_title}")
        
        # If section has more than 10 items, compact via LLM in chunks of 40
        item_lines = [l for l in sec_lines if l.strip().startswith("-")]
        other_lines = [l for l in sec_lines if not l.strip().startswith("-")]

        if len(item_lines) > 10:
            print(f"[memory_compactor] Compacting section '{sec_title}' ({len(item_lines)} entries) in chunks via LLM...")
            chunk_size = 40
            compacted_items = []
            for i in range(0, len(item_lines), chunk_size):
                chunk = item_lines[i:i+chunk_size]
                compacted_chunk = call_llm_compaction(f"{sec_title} (part {i//chunk_size + 1})", chunk)
                compacted_items.extend(compacted_chunk)
            item_lines = compacted_items
        
        compacted_content.extend(other_lines)
        compacted_content.extend(item_lines)
        compacted_content.append("")
        total_compacted += len(item_lines)

    final_text = "\n".join(compacted_content).strip() + "\n"
    atomic_write_text(lessons_path, final_text)
    print(f"[memory_compactor] Compaction complete. LESSONS.md rewritten with {total_compacted} total entries.")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compact lessons for one DevCore project")
    parser.add_argument("--project", required=True, help="Project id whose lessons may be rewritten")
    args = parser.parse_args(argv)
    try:
        compact_lessons_file(args.project)
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
