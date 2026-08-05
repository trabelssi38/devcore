# secret_scanner.py -- Native Python cross-platform secret scanner
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Any

SKIP_EXTENSIONS = {
    ".7z", ".dll", ".exe", ".gif", ".ico", ".jpg", ".jpeg", ".pdf", ".png",
    ".pyc", ".sqlite", ".zip"
}
SKIP_PREFIXES = (
    ".git/",
    ".repowise/",
    ".repowise-workspace/",
    "DEV_CORE_DATA/"
)
ALLOW_FILES = {
    ".env.example",
    "DEV_CORE/Config/gemini_api_key.txt"
}

PATTERNS = [
    {"name": "OpenAI-style token", "regex": re.compile(r"\bsk-[a-z0-9][a-z0-9_-]{19,}\b", re.IGNORECASE)},
    {"name": "Gemini AI Studio token", "regex": re.compile(r"\bAQ\.[A-Za-z0-9_-]{30,}\b")},
    {"name": "Google API key", "regex": re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b")},
]


def scan_repository(path: str = ".") -> List[Dict[str, Any]]:
    root_path = Path(path).resolve()
    git_root = None
    try:
        res = subprocess.run(["git", "-C", str(root_path), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
        if res.returncode == 0 and res.stdout.strip():
            git_root = Path(res.stdout.strip())
    except Exception:
        pass

    if git_root:
        root_path = git_root
        res = subprocess.run(["git", "-C", str(root_path), "ls-files"], capture_output=True, text=True)
        relative_files = res.stdout.splitlines() if res.returncode == 0 else []
    else:
        relative_files = [str(p.relative_to(root_path)) for p in root_path.rglob("*") if p.is_file()]

    findings = []
    for rel in relative_files:
        if not rel:
            continue
        normalized = rel.replace("\\", "/")
        if normalized in ALLOW_FILES:
            continue
        if any(normalized.startswith(prefix) for prefix in SKIP_PREFIXES):
            continue

        ext = Path(normalized).suffix.lower()
        if ext in SKIP_EXTENSIONS:
            continue

        full_path = root_path / rel
        if not full_path.exists() or full_path.stat().st_size > 1024 * 1024:
            continue

        try:
            text = full_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for pat in PATTERNS:
            for match in pat["regex"].finditer(text):
                prefix_text = text[:match.start()]
                line_num = 1 + prefix_text.count("\n")
                findings.append({
                    "file": normalized,
                    "line": line_num,
                    "type": pat["name"]
                })

    return findings
