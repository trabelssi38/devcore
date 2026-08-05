from __future__ import annotations

import os


DEFAULT_DATABASE_URL = "postgresql+psycopg://devcore:devcore@127.0.0.1:5432/devcore"


def get_database_url() -> str:
    return os.environ.get("DEVCORE_DATABASE_URL", DEFAULT_DATABASE_URL).strip()
