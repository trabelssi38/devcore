"""schema v1

Revision ID: 0001_schema_v1
Revises:
Create Date: 2026-07-12
"""

from __future__ import annotations

from pathlib import Path

from alembic import op


revision = "0001_schema_v1"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema_path = Path(__file__).resolve().parents[2] / "postgres_schema_v1.sql"
    op.execute(schema_path.read_text(encoding="utf-8"))


def downgrade() -> None:
    op.execute("drop table if exists audit_log cascade")
    op.execute("drop table if exists events cascade")
    op.execute("drop table if exists plugins cascade")
    op.execute("drop table if exists runs cascade")
    op.execute("drop table if exists tasks cascade")
    op.execute("drop table if exists projects cascade")
