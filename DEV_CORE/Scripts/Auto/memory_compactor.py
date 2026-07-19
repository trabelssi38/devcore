# memory_compactor.py -- LLM-assisted memory compaction for DEV_CORE
import os
import re
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

PLATFORM_ROOT = Path(os.environ.get("DEVCORE_PLATFORM_ROOT", r"C:\devcore\DEV_CORE"))
DATA_ROOT = Path(os.environ.get("DEVCORE_DATA_ROOT", r"C:\devcore\DEV_CORE_DATA"))
ROUTER_URL = os.environ.get("DEVCORE_ROUTER_URL", "http://127.0.0.1:20130/v1/chat/completions")

LESSONS_PATH = DATA_ROOT / "Memory" / "LESSONS.md"
ARCHIVE_DIR = DATA_ROOT / "Memory" / "archive"

def create_backup():
    if not LESSONS_PATH.exists():
        print("[memory_compactor] LESSONS.md not found, skipping backup.")
        return None
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    today_str = datetime.now().strftime("%Y-%m-%d")
    backup_path = ARCHIVE_DIR / f"LESSONS_pre_compaction_{today_str}.md"
    content = LESSONS_PATH.read_text(encoding="utf-8")
    backup_path.write_text(content, encoding="utf-8")
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
        "model": "gemini-2.5-flash",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }

    try:
        req = urllib.request.Request(
            ROUTER_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"].strip()
            compacted_lines = [line.strip() for line in content.splitlines() if line.strip().startswith("-")]
            if compacted_lines:
                return compacted_lines
    except Exception as e:
        print(f"[memory_compactor] Warning: LLM compaction failed for section '{section_title}': {e}")
    
    return lines  # Fallback to original if LLM call fails

def compact_lessons_file():
    if not LESSONS_PATH.exists():
        print("[memory_compactor] LESSONS.md does not exist.")
        return

    create_backup()

    raw_text = LESSONS_PATH.read_text(encoding="utf-8")
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
        
        # If section has more than 10 items, compact via LLM in chunks of 20
        item_lines = [l for l in sec_lines if l.strip().startswith("-")]
        other_lines = [l for l in sec_lines if not l.strip().startswith("-")]

        if len(item_lines) > 10:
            print(f"[memory_compactor] Compacting section '{sec_title}' ({len(item_lines)} entries) in chunks via LLM...")
            chunk_size = 20
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
    LESSONS_PATH.write_text(final_text, encoding="utf-8")
    print(f"[memory_compactor] Compaction complete. LESSONS.md rewritten with {total_compacted} total entries.")

if __name__ == "__main__":
    compact_lessons_file()
