import os
import sys
from pathlib import Path

from alembic.config import Config


DATABASE_ROOT = Path(__file__).resolve().parent
if str(DATABASE_ROOT) not in sys.path:
    sys.path.insert(0, str(DATABASE_ROOT))


def test_database_config_uses_safe_local_default(monkeypatch) -> None:
    from devcore_db.config import get_database_url

    monkeypatch.delenv("DEVCORE_DATABASE_URL", raising=False)

    assert get_database_url() == "postgresql+psycopg://devcore:devcore@127.0.0.1:5432/devcore"


def test_database_config_prefers_environment_url(monkeypatch) -> None:
    from devcore_db.config import get_database_url

    monkeypatch.setenv("DEVCORE_DATABASE_URL", "postgresql+psycopg://custom")

    assert get_database_url() == "postgresql+psycopg://custom"


def test_sqlalchemy_metadata_declares_core_tables() -> None:
    from devcore_db.models import metadata

    expected_tables = {"projects", "tasks", "runs", "events", "plugins", "audit_log"}

    assert expected_tables.issubset(set(metadata.tables))
    assert metadata.tables["tasks"].c.project_id.foreign_keys
    assert metadata.tables["events"].c.payload.type.__class__.__name__ == "JSONB"
    assert metadata.tables["audit_log"].c.details.type.__class__.__name__ == "JSONB"


def test_alembic_config_points_to_local_migrations() -> None:
    config_path = DATABASE_ROOT / "alembic.ini"
    config = Config(str(config_path))

    assert config.get_main_option("script_location") == "alembic"
    assert os.path.exists(DATABASE_ROOT / "alembic" / "env.py")
