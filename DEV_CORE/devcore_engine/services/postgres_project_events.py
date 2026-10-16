"""Bounded project change cursors backed by PostgreSQL events."""

from __future__ import annotations

import re

from .postgres_project_reads import PostgresProjectReader


EVENT_CURSOR = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def validate_event_cursor(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str) or not EVENT_CURSOR.fullmatch(value) or ".." in value:
        raise ValueError("Invalid Last-Event-ID cursor")
    return value


class PostgresProjectEventReader(PostgresProjectReader):
    def changes(self, project: str, after_id: str | None, *, limit: int = 100):
        """Return (new event IDs, next cursor, resync required) under project RLS."""
        after_id = validate_event_cursor(after_id)
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("Event limit must be 1..100")
        with self._transaction(project) as cursor:
            if after_id is None:
                cursor.execute("""SELECT id FROM events WHERE project_id=%s
                    ORDER BY created_at DESC,id DESC LIMIT 1""", (project,))
                latest = cursor.fetchone()
                return [], latest[0] if latest else None, True
            cursor.execute("SELECT created_at FROM events WHERE project_id=%s AND id=%s",
                           (project, after_id))
            boundary = cursor.fetchone()
            if boundary is None:
                cursor.execute("""SELECT id FROM events WHERE project_id=%s
                    ORDER BY created_at DESC,id DESC LIMIT 1""", (project,))
                latest = cursor.fetchone()
                return [], latest[0] if latest else None, True
            cursor.execute("""SELECT id FROM events WHERE project_id=%s
                AND (created_at,id)>(%s,%s)
                ORDER BY created_at,id LIMIT %s""",
                (project, boundary[0], after_id, limit))
            rows = cursor.fetchall()
            ids = [row[0] for row in rows]
            return ids, ids[-1] if ids else after_id, False
