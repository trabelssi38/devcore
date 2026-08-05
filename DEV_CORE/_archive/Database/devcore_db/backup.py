from __future__ import annotations

from pathlib import Path
from typing import Any


def _validate_backup_path(path: str | Path) -> Path:
    backup_path = Path(path)
    if backup_path.is_absolute() or ".." in backup_path.parts:
        raise ValueError("backup_path must be a relative path inside the controlled backup directory")
    if not backup_path.name:
        raise ValueError("backup_path must include a file name")
    return backup_path


def _validate_database_url(database_url: str) -> str:
    if not database_url or not database_url.strip():
        raise ValueError("database_url is required")
    return database_url.strip()


def build_backup_command(database_url: str, output_path: str | Path) -> list[str]:
    database_url = _validate_database_url(database_url)
    return [
        "pg_dump",
        "--format=custom",
        "--no-owner",
        "--no-privileges",
        f"--file={Path(output_path)}",
        database_url,
    ]


def build_restore_command(database_url: str, input_path: str | Path) -> list[str]:
    database_url = _validate_database_url(database_url)
    return [
        "pg_restore",
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-privileges",
        f"--dbname={database_url}",
        str(Path(input_path)),
    ]


def build_release_procedure_plan(
    *,
    database_url: str,
    backup_path: str | Path,
    target_revision: str,
    rollback_revision: str,
) -> dict[str, Any]:
    database_url = _validate_database_url(database_url)
    backup_path = _validate_backup_path(backup_path)
    if not target_revision.strip():
        raise ValueError("target_revision is required")
    if not rollback_revision.strip():
        raise ValueError("rollback_revision is required")

    return {
        "schema_version": 1,
        "dry_run": True,
        "steps": [
            {
                "id": "preflight",
                "description": "Check database URL, migration tooling and backup target before mutation.",
                "command": ["python", "-m", "devcore_db.backup", "preflight"],
                "destructive": False,
            },
            {
                "id": "backup",
                "description": "Create a custom-format PostgreSQL dump before upgrade.",
                "command": build_backup_command(database_url, backup_path),
                "destructive": False,
            },
            {
                "id": "upgrade",
                "description": "Apply Alembic migrations to the target revision.",
                "command": ["alembic", "upgrade", target_revision.strip()],
                "destructive": True,
            },
            {
                "id": "verify",
                "description": "Run deterministic database and API contract checks after upgrade.",
                "command": ["python", "-m", "pytest", "DEV_CORE/Database", "DEV_CORE/API"],
                "destructive": False,
            },
            {
                "id": "rollback",
                "description": "Downgrade Alembic by the configured rollback revision if verification fails.",
                "command": ["alembic", "downgrade", rollback_revision.strip()],
                "destructive": True,
            },
            {
                "id": "restore",
                "description": "Restore the pre-upgrade dump if rollback is insufficient.",
                "command": build_restore_command(database_url, backup_path),
                "destructive": True,
            },
        ],
        "safety": {
            "requires_manual_confirmation": True,
            "restore_is_destructive": True,
            "shell_interpolation": False,
            "backup_before_upgrade": True,
        },
    }
