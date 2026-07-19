"""
DEV_CORE -- Tools/devcore/file_utils.py
Utilitaires de scan de fichiers performants avec exclusion de répertoires.

APPROCHE: os.walk(topdown=True) avec modification in-place de dirnames.
C'est la méthode recommandée par Python docs pour exclure des répertoires
sans traverser leurs sous-arbres. Beaucoup plus rapide que la récursion Python.

Sprint 12 baseline: rglob p95=10,835ms
Sprint 12 après fast_scan_os_walk: cible < 500ms
"""

from __future__ import annotations

import fnmatch
import json
import os
from pathlib import Path

# Répertoires à exclure par défaut lors du scan du dépôt DEV_CORE
DEFAULT_EXCLUDE_DIRS: frozenset[str] = frozenset({
    # Environnements virtuels Python
    ".venv", "venv", "env", ".env",
    # Dépendances Node.js
    "node_modules",
    # Build Next.js
    ".next", "out",
    # Caches Python
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    # Git et VCS
    ".git", ".hg", ".svn",
    # IDEs
    ".idea", ".vscode",
    # Compilation / artifacts
    "bin", "obj", "target",
    # Qdrant storage (vecteurs binaires)
    "qdrant_storage",
    # Archives DEV_CORE
    "Archive", "_archive",
    # Ancienne application Hermes
    "hermes", "hermes_temp",
})


def fast_rglob(
    root: Path,
    pattern: str,
    exclude_dirs: frozenset[str] | set[str] | None = None,
    max_depth: int = 20,
    _current_depth: int = 0,
) -> list[Path]:
    """
    Équivalent de Path.rglob(pattern) avec exclusion de répertoires.
    Utilise os.walk avec topdown=True pour éviter la traversée des sous-arbres exclus.

    Args:
        root: Répertoire racine du scan.
        pattern: Glob pattern (ex: "*.py", "*.ps1", "tasks.json").
        exclude_dirs: Noms de répertoires à ignorer (utilise DEFAULT_EXCLUDE_DIRS si None).
        max_depth: Profondeur maximale de récursion (défaut: 20).
        _current_depth: Non utilisé (conservé pour compatibilité API).

    Returns:
        Liste de Path objets correspondant au pattern.
    """
    if exclude_dirs is None:
        exclude_dirs = DEFAULT_EXCLUDE_DIRS

    results: list[Path] = []
    root_str = str(root)
    root_depth = root_str.count(os.sep)

    for dirpath, dirnames, filenames in os.walk(root_str, topdown=True):
        # Profondeur courante
        current_depth = dirpath.count(os.sep) - root_depth
        if current_depth >= max_depth:
            dirnames.clear()
            continue

        # Exclure les répertoires en modifiant dirnames in-place
        # os.walk ne descendra pas dans les répertoires supprimés
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]

        # Filtrer les fichiers par pattern
        for fname in filenames:
            if fnmatch.fnmatch(fname, pattern):
                results.append(Path(dirpath) / fname)

    return results


def find_file(
    root: Path,
    filename: str,
    exclude_dirs: frozenset[str] | set[str] | None = None,
) -> Path | None:
    """
    Trouve le premier fichier correspondant au nom exact dans le dépôt.
    Utilise os.walk avec topdown=True pour une recherche rapide.

    Args:
        root: Répertoire racine.
        filename: Nom de fichier exact (ex: "tasks.json").
        exclude_dirs: Répertoires à exclure.

    Returns:
        Path du premier fichier trouvé, ou None si absent.
    """
    if exclude_dirs is None:
        exclude_dirs = DEFAULT_EXCLUDE_DIRS

    for dirpath, dirnames, filenames in os.walk(str(root), topdown=True):
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
        if filename in filenames:
            return Path(dirpath) / filename

    return None


def scan_devcore_files(
    root: Path,
    patterns: list[str] | None = None,
    exclude_dirs: frozenset[str] | set[str] | None = None,
) -> list[Path]:
    """
    Scan des fichiers DEV_CORE avec patterns multiples et exclusions.

    Args:
        root: Répertoire racine (ex: Path("C:/devcore")).
        patterns: Liste de patterns (défaut: ["*.py", "*.ps1"]).
        exclude_dirs: Répertoires à exclure (défaut: DEFAULT_EXCLUDE_DIRS).

    Returns:
        Liste dédupliquée de Path objets, triée par chemin.
    """
    if patterns is None:
        patterns = ["*.py", "*.ps1"]

    seen: set[str] = set()
    results: list[Path] = []

    if exclude_dirs is None:
        exclude_dirs = DEFAULT_EXCLUDE_DIRS

    for dirpath, dirnames, filenames in os.walk(str(root), topdown=True):
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
        for fname in filenames:
            for pat in patterns:
                if fnmatch.fnmatch(fname, pat):
                    full = os.path.join(dirpath, fname)
                    if full not in seen:
                        seen.add(full)
                        results.append(Path(full))
                    break

    results.sort()
    return results


if __name__ == "__main__":
    import time
    import sys

    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("C:/devcore")

    print(f"Scanning: {root}")
    print(f"Exclude dirs: {sorted(DEFAULT_EXCLUDE_DIRS)}\n")

    t0 = time.perf_counter()
    py_files = fast_rglob(root, "*.py")
    ps_files = fast_rglob(root, "*.ps1")
    elapsed = (time.perf_counter() - t0) * 1000

    print(f"Python files : {len(py_files)}")
    print(f"PS1 files    : {len(ps_files)}")
    print(f"Total        : {len(py_files) + len(ps_files)}")
    print(f"Elapsed      : {elapsed:.1f}ms")

    t0 = time.perf_counter()
    tasks_json = find_file(root, "tasks.json")
    elapsed2 = (time.perf_counter() - t0) * 1000
    print(f"\ntasks.json   : {tasks_json}")
    print(f"Elapsed      : {elapsed2:.1f}ms")
