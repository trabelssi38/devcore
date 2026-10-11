"""Read context from a registered repository after individual admission.

The HTTP adapter supplies an authenticated principal; this is not authentication
for OS-local SDK callers. Registered roots and their writers must be trusted.
"""

from contextlib import closing
from pathlib import Path
import sqlite3

from devcore_engine.security.identity import CONTEXT_READ, Principal, ProjectAccessDenied
from .project_context import ContextBudgetExceeded, load_project_context


class ProjectContextUnavailable(RuntimeError):
    pass


def load_registered_project_context(db_path, principal, *, budget_bytes=12000, query=""):
    """No initialization, migration, caller directory or global-context fallback."""
    if not isinstance(principal, Principal) or principal.action != CONTEXT_READ:
        raise ProjectAccessDenied("Context read principal required")
    try:
        with closing(sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=ro",
                                     uri=True, timeout=1)) as conn:
            conn.execute("PRAGMA query_only=ON")
            row = conn.execute("SELECT root_path FROM projects WHERE id=?",
                               (principal.project_id,)).fetchone()
        if row is None or not isinstance(row[0], str) or not row[0].strip():
            raise ValueError("Registered project root required")
        root = Path(row[0])
        if not root.is_absolute() or not root.is_dir():
            raise ValueError("Existing absolute registered root required")
        root = root.resolve()
        directory = (root / "docs" / "project-context").resolve()
        if not directory.is_relative_to(root) or not directory.is_dir():
            raise ValueError("Context must be inside the registered root")
        return load_project_context(directory, principal.project_id,
                                    budget_bytes=budget_bytes, query=query)
    except ContextBudgetExceeded:
        raise
    except (OSError, ValueError, TypeError, sqlite3.Error) as exc:
        # Do not expose paths, SQLite details or foreign manifest contents.
        raise ProjectContextUnavailable("Registered project context unavailable") from exc
