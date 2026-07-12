from __future__ import annotations

from pathlib import Path


def build_backup_command(database_url: str, output_path: str | Path) -> list[str]:
    return [
        "pg_dump",
        "--format=custom",
        "--no-owner",
        "--no-privileges",
        f"--file={Path(output_path)}",
        database_url,
    ]


def build_restore_command(database_url: str, input_path: str | Path) -> list[str]:
    return [
        "pg_restore",
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-privileges",
        f"--dbname={database_url}",
        str(Path(input_path)),
    ]
