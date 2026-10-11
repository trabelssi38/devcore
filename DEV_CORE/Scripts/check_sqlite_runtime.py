"""Check the SQLite loaded by this Python before WAL concurrency qualification.

No DevCore imports, database paths, migrations or journal changes. A passing
version check is a prerequisite, never an operational qualification.
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from contextlib import closing

SOURCE = "https://sqlite.org/wal.html#the_wal_reset_bug"


def wal_reset_fix_known(version: str) -> bool:
    """Recognize upstream fixes; unknown/vendor version strings fail closed."""
    if not isinstance(version, str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        return False
    major, minor, patch = map(int, version.split("."))
    # Do not infer guarantees about a future major version or older branches.
    return major == 3 and (
        (minor == 44 and patch >= 6)
        or (minor == 50 and patch >= 7)
        or (minor == 51 and patch >= 3)
        or minor > 51
    )


def inspect_runtime() -> dict:
    # :memory: cannot open an active database, even with arbitrary environment
    # roots. Query the actual loaded library rather than a lockfile/package tag.
    with closing(sqlite3.connect(":memory:")) as connection:
        version, source_id = connection.execute(
            "SELECT sqlite_version(), sqlite_source_id()"
        ).fetchone()
        options = sorted(row[0] for row in connection.execute("PRAGMA compile_options"))
    versions_match = version == sqlite3.sqlite_version
    fixed = versions_match and wal_reset_fix_known(version)
    wal_available = "OMIT_WAL" not in options
    return {
        "schema_version": 1,
        "python_executable": sys.executable,
        "python_version": sys.version.split()[0],
        "sqlite_version": version,
        "sqlite_module_version": sqlite3.sqlite_version,
        "sqlite_source_id": source_id,
        "compile_options": options,
        "versions_match": versions_match,
        "wal_available": wal_available,
        "wal_reset_fix_known": fixed,
        "eligible_for_wal_qualification": fixed and wal_available,
        "operationally_qualified": False,
        "source": SOURCE,
        "policy_reviewed_at": "2026-10-03",
        "scope": "loaded_stdlib_sqlite_only",
        "next_action": (
            "qualify concurrent writes/checkpoints and DevCore regressions on fixtures"
            if fixed and wal_available
            else "prepare a separate runtime with a documented SQLite WAL fix; rerun this check"
        ),
    }


def main() -> int:
    try:
        result = inspect_runtime()
    except sqlite3.Error:
        print(json.dumps({"schema_version": 1, "eligible_for_wal_qualification": False,
                          "operationally_qualified": False, "error": "sqlite_probe_failed"}))
        return 2
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0 if result["eligible_for_wal_qualification"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
