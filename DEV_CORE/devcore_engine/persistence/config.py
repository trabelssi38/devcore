"""Database configuration for DEV_CORE target PostgreSQL architecture.

Enforces connection limits, role separation (application vs migration),
and forbids storing active transactional data or databases in Dropbox.
"""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class DatabaseRole(str, Enum):
    """Database roles separating operational runtime from schema migrations."""
    APPLICATION = "application"
    MIGRATION = "migration"


def is_dropbox_path(path: str | Path) -> bool:
    """Detect whether a given path is located inside a Dropbox directory."""
    resolved = str(Path(path).resolve()).lower()
    dropbox_indicators = ["dropbox", ".dropbox", "dropbox.cache"]
    for indicator in dropbox_indicators:
        parts = Path(resolved).parts
        if any(indicator == p.lower() or indicator in p.lower() for p in parts):
            return True
    return False


def validate_storage_path_outside_dropbox(path: str | Path, label: str = "Database storage") -> Path:
    """Validate that storage location is strictly outside Dropbox."""
    p = Path(path).resolve()
    if is_dropbox_path(p):
        raise ValueError(
            f"{label} path '{p}' is inside a Dropbox folder. "
            "Decision D-004 strictly forbids storing transactional data or active databases in Dropbox."
        )
    return p


class DatabaseConfig:
    """Database connection and pooling parameters."""

    DEFAULT_APP_URL = "postgresql+psycopg://devcore_app:secret@127.0.0.1:5432/devcore"
    DEFAULT_MIGRATION_URL = "postgresql+psycopg://devcore_migration:secret@127.0.0.1:5432/devcore"

    def __init__(
        self,
        *,
        url: Optional[str] = None,
        migration_url: Optional[str] = None,
        pool_size: int = 5,
        max_overflow: int = 2,
        pool_timeout: float = 10.0,
        role: DatabaseRole = DatabaseRole.APPLICATION,
    ) -> None:
        # Bounded connections
        self.pool_size = max(1, min(pool_size, 20))
        self.max_overflow = max(0, min(max_overflow, 10))
        self.pool_timeout = max(1.0, min(pool_timeout, 60.0))
        self.role = role

        # Resolution from environment
        env_url = os.environ.get("DEVCORE_DATABASE_URL")
        env_migration_url = os.environ.get("DEVCORE_MIGRATION_DATABASE_URL")

        self.app_url = url or env_url or self.DEFAULT_APP_URL
        self.migration_url = migration_url or env_migration_url or self.DEFAULT_MIGRATION_URL

    @property
    def active_url(self) -> str:
        """Return the appropriate URL depending on the configured role."""
        if self.role == DatabaseRole.MIGRATION:
            return self.migration_url
        return self.app_url

    def get_engine_kwargs(self) -> dict[str, Any]:
        """Return SQLAlchemy engine parameters enforcing bounded connection pool."""
        return {
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
            "pool_timeout": self.pool_timeout,
            "pool_pre_ping": True,
        }


def get_database_config(role: DatabaseRole = DatabaseRole.APPLICATION) -> DatabaseConfig:
    """Create a DatabaseConfig configured for the specified role."""
    pool_size = int(os.environ.get("DEVCORE_DB_POOL_SIZE", "5"))
    max_overflow = int(os.environ.get("DEVCORE_DB_MAX_OVERFLOW", "2"))
    pool_timeout = float(os.environ.get("DEVCORE_DB_POOL_TIMEOUT", "10.0"))
    return DatabaseConfig(
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        role=role,
    )
