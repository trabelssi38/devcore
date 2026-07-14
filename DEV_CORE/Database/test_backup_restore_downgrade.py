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


def test_release_procedure_plan_orders_backup_upgrade_verify_and_rollback() -> None:
    from devcore_db.backup import build_release_procedure_plan

    plan = build_release_procedure_plan(
        database_url="postgresql://user:pass@127.0.0.1:5432/devcore",
        backup_path=Path("backup.dump"),
        target_revision="head",
        rollback_revision="-1",
    )

    assert plan["schema_version"] == 1
    assert plan["dry_run"] is True
    assert [step["id"] for step in plan["steps"]] == [
        "preflight",
        "backup",
        "upgrade",
        "verify",
        "rollback",
        "restore",
    ]
    assert plan["steps"][1]["command"][:2] == ["pg_dump", "--format=custom"]
    assert plan["steps"][2]["command"] == ["alembic", "upgrade", "head"]
    assert plan["steps"][4]["command"] == ["alembic", "downgrade", "-1"]
    assert plan["steps"][5]["command"][:2] == ["pg_restore", "--clean"]
    assert plan["safety"]["requires_manual_confirmation"] is True
    assert plan["safety"]["restore_is_destructive"] is True


def test_release_procedure_rejects_unsafe_paths_and_empty_database_url() -> None:
    from devcore_db.backup import build_release_procedure_plan

    for kwargs in [
        {
            "database_url": "",
            "backup_path": Path("backup.dump"),
            "target_revision": "head",
            "rollback_revision": "-1",
        },
        {
            "database_url": "postgresql://user:pass@127.0.0.1:5432/devcore",
            "backup_path": Path("../backup.dump"),
            "target_revision": "head",
            "rollback_revision": "-1",
        },
    ]:
        try:
            build_release_procedure_plan(**kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError(f"unsafe release procedure accepted: {kwargs}")
