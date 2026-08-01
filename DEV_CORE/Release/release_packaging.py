from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Iterable


EXCLUDED_DIRS = {
    ".git",
    ".claude",
    ".vscode",
    ".idea",
    ".pytest_cache",
    ".repowise",
    ".repowise-workspace",
    "__pycache__",
    "node_modules",
}
EXCLUDED_PREFIXES = {
    "download/",
    # Dashboard HTML files are runtime-generated artefacts — excluded for reproducibility
    "Dashboard/index.html",
    "Dashboard/index_terminal.html",
}
EXCLUDED_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".sqlite",
    ".zip",
}


def _read_platform(root: Path) -> dict:
    platform_path = root / "Config" / "platform.json"
    return json.loads(platform_path.read_text(encoding="utf-8"))


def _is_release_file(root: Path, path: Path) -> bool:
    rel = path.relative_to(root).as_posix()
    parts = set(path.relative_to(root).parts)
    if parts & EXCLUDED_DIRS:
        return False
    if any(rel.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
        return False
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    if path.name.startswith(".") and path.name not in {".gitkeep"}:
        return False
    return True


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_release_manifest(root: Path, *, git_sha: str, created_at: str) -> dict:
    platform = _read_platform(root)
    files = []
    for path in root.rglob("*"):
        if not path.is_file() or not _is_release_file(root, path):
            continue
        rel = path.relative_to(root).as_posix()
        files.append(
            {
                "path": rel,
                "size": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    files = sorted(files, key=lambda item: item["path"])
    return {
        "schema_version": 1,
        "name": platform["name"],
        "version": platform["version"],
        "git_sha": git_sha,
        "created_at": created_at,
        "archive": {
            "format": "zip",
            "compression": "deflate",
            "reproducible": True,
            "timestamp_policy": "fixed-or-source-date-epoch",
        },
        "files": files,
    }


def _parse_commit(line: str) -> tuple[str, str, str]:
    match = re.match(r"^(?P<sha>[0-9a-f]+)\s+(?P<kind>[a-z]+)(?:\([^)]+\))?:\s+(?P<title>.+?)(?:\s+\[(?P<task>T-\d+)\])?$", line)
    if not match:
        return "Other", "", line.strip()
    kind = match.group("kind")
    task = match.group("task") or ""
    title = match.group("title").strip()
    section = {
        "feat": "Features",
        "fix": "Fixes",
        "security": "Security",
        "test": "Tests",
        "docs": "Documentation",
        "ci": "CI",
        "chore": "Maintenance",
    }.get(kind, "Other")
    return section, task, title


def build_release_notes(*, version: str, git_sha: str, commits: Iterable[str]) -> str:
    grouped: dict[str, list[str]] = {}
    for commit in commits:
        section, task, title = _parse_commit(commit)
        prefix = f"`{task}` " if task else ""
        grouped.setdefault(section, []).append(f"- {prefix}{title}")

    lines = [
        f"# DEV_CORE v{version} Release Notes",
        "",
        f"Git SHA: `{git_sha}`",
        "",
    ]
    for section in ["Features", "Fixes", "Security", "Tests", "Documentation", "CI", "Maintenance", "Other"]:
        items = grouped.get(section)
        if not items:
            continue
        lines.extend([f"## {section}", "", *items, ""])
    lines.extend(
        [
            "## Validation",
            "",
            "- `ci_python_tests.ps1` must pass.",
            "- `secret_scan.ps1` must pass before publishing.",
            "- Release manifest and SBOM must be committed with the release.",
            "",
        ]
    )
    return "\n".join(lines)


def write_release_artifacts(
    root: Path,
    output_dir: Path,
    *,
    git_sha: str,
    commits: Iterable[str],
    created_at: str = "2026-07-14T00:00:00Z",
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    version = _read_platform(root)["version"]
    manifest = build_release_manifest(root, git_sha=git_sha, created_at=created_at)
    notes = build_release_notes(version=version, git_sha=git_sha, commits=commits)

    manifest_path = output_dir / "release-manifest.json"
    notes_path = output_dir / "RELEASE_NOTES.md"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    notes_path.write_text(notes if notes.endswith("\n") else notes + "\n", encoding="utf-8")
    return {"manifest": manifest_path, "notes": notes_path}


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[1]
    output = repo_root / "Release"
    artifacts = write_release_artifacts(
        repo_root,
        output,
        git_sha="uncommitted",
        commits=[],
    )
    print(json.dumps({key: str(value) for key, value in artifacts.items()}, indent=2))
