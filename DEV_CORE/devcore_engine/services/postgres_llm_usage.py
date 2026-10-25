"""Record authenticated Gemini usage without storing prompts or responses."""

from __future__ import annotations

import re
from uuid import uuid4

from devcore_engine.security.identity import Principal, ProjectAccessDenied

from .postgres_project_reads import PostgresProjectReader


_IDENTIFIER = re.compile(r"[A-Za-z0-9_.:/-]{1,128}\Z")


class PostgresLlmUsageStore(PostgresProjectReader):
    def assert_ready(self, principal: Principal) -> None:
        if not isinstance(principal, Principal) or principal.action != "task.mutate":
            raise ProjectAccessDenied("Project mutation principal required")
        import pg8000.dbapi

        db = pg8000.dbapi.connect(**self._options)
        try:
            cur = db.cursor()
            cur.execute("SELECT set_config('app.current_project_id', %s, true)",
                        (principal.project_id,))
            cur.execute("SELECT 1 FROM project_llm_usage WHERE project_id=%s LIMIT 0",
                        (principal.project_id,))
        finally:
            db.rollback()
            db.close()

    def record_gemini(
        self, principal: Principal, *, trace_id: str, model: str,
        prompt_tokens: int | None, completion_tokens: int | None,
    ) -> bool:
        if not isinstance(principal, Principal) or principal.action != "task.mutate":
            raise ProjectAccessDenied("Project mutation principal required")
        if not all(isinstance(value, str) and _IDENTIFIER.fullmatch(value)
                   for value in (trace_id, model, principal.user_id)):
            raise ValueError("Invalid Gemini usage identity")
        reported = prompt_tokens is not None or completion_tokens is not None
        if reported and (type(prompt_tokens) is not int or type(completion_tokens) is not int
                         or not 0 <= prompt_tokens <= (1 << 63) - 1
                         or not 0 <= completion_tokens <= (1 << 63) - 1
                         or prompt_tokens + completion_tokens > (1 << 63) - 1):
            raise ValueError("Invalid provider token usage")
        source = "provider_reported" if reported else "unreported"
        import pg8000.dbapi

        db = pg8000.dbapi.connect(**self._options)
        try:
            cur = db.cursor()
            cur.execute("SELECT set_config('app.current_project_id', %s, true)",
                        (principal.project_id,))
            cur.execute("""INSERT INTO project_llm_usage
                (id,project_id,user_id,trace_id,provider,model,prompt_tokens,
                 completion_tokens,usage_source)
                VALUES (%s,%s,%s,%s,'google-gemini',%s,%s,%s,%s)
                ON CONFLICT (project_id,trace_id) DO NOTHING""",
                (str(uuid4()), principal.project_id, principal.user_id, trace_id,
                 model, prompt_tokens, completion_tokens, source))
            inserted = cur.rowcount == 1
            if not inserted:
                cur.execute("""SELECT user_id,provider,model,prompt_tokens,
                    completion_tokens,usage_source FROM project_llm_usage
                    WHERE project_id=%s AND trace_id=%s""",
                    (principal.project_id, trace_id))
                existing = cur.fetchone()
                if existing is None or tuple(existing) != (
                        principal.user_id, "google-gemini", model,
                        prompt_tokens, completion_tokens, source):
                    raise ValueError("Conflicting Gemini usage trace")
            db.commit()
            return inserted
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()
