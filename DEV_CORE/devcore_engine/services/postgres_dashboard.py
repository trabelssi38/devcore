"""Bounded, project-scoped Cockpit snapshot for the PostgreSQL team profile."""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape

from devcore_engine.security.identity import Principal, ProjectAccessDenied

from .postgres_project_reads import PostgresProjectReader
from .global_stack_monitor import global_stack_health, render_global_stack_health


def _text(value: object) -> str:
    return escape(str(value if value is not None else ""), quote=True)


class PostgresDashboardProjection(PostgresProjectReader):
    def snapshot(self, principal: Principal) -> dict:
        if not isinstance(principal, Principal) or principal.action != "task.read":
            raise ProjectAccessDenied("Task read principal required")
        project = principal.project_id
        with self._transaction(project) as cursor:
            cursor.execute("SELECT count(*) FROM tasks WHERE project_id=%s", (project,))
            task_count = cursor.fetchone()[0]
            cursor.execute("""SELECT legacy_id,task_uuid,title,status,mode,version,
                steps_done,steps_total,updated_at FROM tasks WHERE project_id=%s
                ORDER BY (status IN ('active','in_progress')) DESC,updated_at DESC,task_uuid
                LIMIT 60""", (project,))
            tasks = cursor.fetchall()
            cursor.execute("""SELECT id,status,title,updated_at FROM runs
                WHERE project_id=%s ORDER BY updated_at DESC,id LIMIT 10""", (project,))
            runs = cursor.fetchall()
            cursor.execute("""SELECT event_type,created_at FROM events
                WHERE project_id=%s ORDER BY created_at DESC,id DESC LIMIT 10""", (project,))
            events = cursor.fetchall()
            cursor.execute("""SELECT id,name,status,cron,timezone,next_run_at,last_run_at,
                metadata->>'execution_ready' FROM schedules WHERE project_id=%s
                ORDER BY updated_at DESC,id LIMIT 20""", (project,))
            schedules = cursor.fetchall()
            cursor.execute("""SELECT s.name,h.event_type,h.status,h.occurred_at
                FROM schedule_history h JOIN schedules s ON s.id=h.schedule_id
                WHERE s.project_id=%s ORDER BY h.occurred_at DESC,h.id DESC LIMIT 10""", (project,))
            schedule_events = cursor.fetchall()
            cursor.execute("""SELECT name,version,enabled FROM plugins WHERE project_id=%s
                ORDER BY name,id LIMIT 20""", (project,))
            plugins = cursor.fetchall()
            cursor.execute("""SELECT task_type,count(*) FROM memory_entries WHERE project_id=%s
                GROUP BY task_type ORDER BY task_type LIMIT 20""", (project,))
            memory_groups = cursor.fetchall()
            cursor.execute("""SELECT model_tokens_daily,runs_daily,storage_mb FROM budgets
                WHERE project_id=%s LIMIT 1""", (project,))
            budget = cursor.fetchone()
            cursor.execute("""SELECT node_count,edge_rows FROM project_graph_stats
                WHERE project_id=%s LIMIT 1""", (project,))
            graph_stats = cursor.fetchone()
            cursor.execute("""SELECT count(*),coalesce(sum(prompt_tokens),0),
                coalesce(sum(completion_tokens),0),
                count(*) FILTER (WHERE usage_source='unreported')
                FROM project_llm_usage WHERE project_id=%s""", (project,))
            usage = cursor.fetchone()

        label = _text(project)
        cards = (f'<div class="project-row" data-project="{label}">'
                 f'<strong>{label}</strong> · {task_count} tâches</div>')
        missions = []
        for legacy, task_uuid, title, status, mode, version, done, total, updated in tasks:
            task_id = str(legacy or task_uuid)
            css_status = "done" if status == "done" else "active" if status in {"active", "in_progress"} else "todo"
            date = updated.isoformat() if updated else ""
            attributes = (f'data-project="{label}" data-task-id="{_text(task_id)}" '
                          f'data-version="{version}"')
            complete_button = (
                f'<button class="btn-action" {attributes} '
                'onclick="completeTask(this.dataset.project,this.dataset.taskId,event,'
                'Number(this.dataset.version))">Clôturer</button>'
                if status not in {"done", "deleted"} else ""
            )
            delete_button = (
                f'<button class="btn-action" {attributes} '
                'onclick="deleteTask(this.dataset.project,this.dataset.taskId,event,'
                'Number(this.dataset.version))">Supprimer</button>'
                if status != "deleted" else ""
            )
            missions.append(
                f'<div class="mission {css_status}" data-date="{_text(date)}">'
                f'<div class="mission-header"><span class="badge {css_status}">{_text(status)}</span>'
                f'<div class="mission-title">{_text(task_id)}: {_text(title)}</div></div>'
                f'<div>Mode: {_text(mode)} · {done}/{total} étapes · version {version}</div>'
                f'<div>{complete_button}{delete_button}</div></div>'
            )
        pipeline = (f'<details open class="project-tasks-group" data-project="{label}">'
                    f'<summary>Projet : {label} · {task_count} tâches</summary>'
                    + "".join(missions) + "</details>")
        run_items = "".join(
            f'<div>{_text(run_id)} · {_text(status)} · {_text(title)}</div>'
            for run_id, status, title, _ in runs
        ) or "<div>Aucun run récent.</div>"
        event_items = "".join(
            f'<div>{_text(kind)} · {_text(created.isoformat() if created else "")}</div>'
            for kind, created in events
        ) or "<div>Aucun événement récent.</div>"
        schedule_items = "".join(
            f'<div class="schedule-row" data-schedule="{_text(schedule_id)}">'
            f'{_text(name)} · {_text(status)} · {_text(cron)} ({_text(zone)})'
            f' · prochain : {_text(next_due.isoformat() if next_due else "—")}'
            f' · dernier : {_text(last_due.isoformat() if last_due else "—")}'
            f' · exécution qualifiée : {"oui" if qualified == "true" else "non"}</div>'
            for schedule_id, name, status, cron, zone, next_due, last_due, qualified in schedules
        ) or "<div>Aucun job planifié dans ce projet.</div>"
        history_items = "".join(
            f'<div>{_text(name)} · {_text(event_type)} · {_text(status)}'
            f' · {_text(occurred.isoformat() if occurred else "")}</div>'
            for name, event_type, status, occurred in schedule_events
        )
        schedule_panel = ('<div>Planifications PostgreSQL</div>' + schedule_items
                          + ('<div>Historique récent</div>' + history_items if history_items else ""))
        plugin_panel = "".join(
            f'<div>{_text(name)} · version {_text(version or "inconnue")} · '
            f'{"actif" if enabled else "désactivé"}</div>'
            for name, version, enabled in plugins
        ) or "<div>Aucun plugin enregistré dans ce projet.</div>"
        memory_panel = "".join(
            f'<div>{_text(task_type)} · {count} entrée(s)</div>'
            for task_type, count in memory_groups
        ) or "<div>Aucune entrée mémoire dans ce projet.</div>"
        if budget is None:
            metrics_panel = "<div>Aucun budget de projet configuré.</div>"
        else:
            model_tokens, daily_runs, storage_mb = budget
            metrics_panel = (f'<div>Plafonds du projet : {model_tokens} jetons modèle/jour, '
                             f'{daily_runs} runs/jour, {storage_mb} Mo de stockage.</div>')
        if graph_stats is None:
            graph_panel = "<div>Aucun graphe historique attribué à ce projet.</div>"
        else:
            nodes, edges = graph_stats
            graph_panel = (f'<div>{nodes} nœuds · {edges} arêtes historiques '
                           'du projet, hors relations en quarantaine.</div>')
        calls, prompt_tokens, completion_tokens, unreported = usage
        if calls == 0:
            token_panel = "<div>Aucun appel LLM attribué à ce projet.</div>"
        else:
            token_panel = (f'<div>{calls} appel(s) Gemini attribué(s) au projet · '
                           f'{prompt_tokens} jetons entrée · {completion_tokens} jetons sortie'
                           + (f' · {unreported} appel(s) sans usage fournisseur' if unreported else "")
                           + '</div>')
        return {
            "schema_version": 1,
            "project": project,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "sections": {
                "project_cards": cards,
                "tasks_pipeline": pipeline,
                "services_monitoring": render_global_stack_health(global_stack_health()),
                "automation_hooks": schedule_panel,
                "token_activity_report": token_panel,
                "context_composition": memory_panel,
                "metrics_service_summary": metrics_panel,
                "event_bus_recent": event_items,
                "knowledge_graph_summary": graph_panel,
                "plugin_status": plugin_panel,
            },
            "runs": run_items,
            "task_details": {},
            "task_interactions": {},
            "token_metrics": {},
            "cache": {},
            "counts": {"tasks": task_count, "shown_tasks": len(tasks), "runs": len(runs)},
        }
