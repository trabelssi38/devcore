import sys
from pathlib import Path


DATABASE_ROOT = Path(__file__).resolve().parent
if str(DATABASE_ROOT) not in sys.path:
    sys.path.insert(0, str(DATABASE_ROOT))


def test_backup_and_restore_commands_are_safe_and_explicit() -> None:
    from devcore_db.backup import build_backup_command, build_restore_command

    backup = build_backup_command("postgresql://user:pass@127.0.0.1:5432/devcore", Path("backup.dump"))
    restore = build_restore_command("postgresql://user:pass@127.0.0.1:5432/devcore", Path("backup.dump"))

    assert backup[:2] == ["pg_dump", "--format=custom"]
    assert "--file=backup.dump" in backup
    assert "postgresql://user:pass@127.0.0.1:5432/devcore" in backup
    assert restore[:2] == ["pg_restore", "--clean"]
    assert "--if-exists" in restore
    assert "--dbname=postgresql://user:pass@127.0.0.1:5432/devcore" in restore
    assert "backup.dump" in restore


def test_initial_alembic_revision_has_upgrade_and_downgrade() -> None:
    revision_path = DATABASE_ROOT / "alembic" / "versions" / "0001_schema_v1.py"
    content = revision_path.read_text(encoding="utf-8").lower()

    assert "revision = \"0001_schema_v1\"" in content
    assert "def upgrade()" in content
    assert "postgres_schema_v1.sql" in content
    assert "def downgrade()" in content
    for table in ["outbox_messages", "audit_log", "events", "plugins", "runs", "tasks", "projects"]:
        assert f"drop table if exists {table}" in content
