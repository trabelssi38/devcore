"""Bounded, project-scoped Cockpit snapshot for the PostgreSQL team profile."""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape

from devcore_engine.security.identity import Principal, ProjectAccessDenied

from .postgres_project_reads import PostgresProjectReader
from .global_stack_monitor import global_stack_health, render_global_stack_health
from .cockpit_presentation import (task_cards, project_card, usage_panel, panel, metric,
                                   project_code_health, code_health_card)


def _text(value: object) -> str:
    return escape(str(value if value is not None else ""), quote=True)


def _empty_state(status: str, detail: str, source: str) -> str:
    return ('<div class="team-empty-state"><strong>' + _text(status) + '</strong>'
            + '<span>' + _text(detail) + '</span>'
            + '<small>Source : ' + _text(source) + '</small></div>')


class PostgresDashboardProjection(PostgresProjectReader):
    def snapshot(self, principal: Principal, *, task_offset: int = 0) -> dict:
        if not isinstance(principal, Principal) or principal.action != "task.read":
            raise ProjectAccessDenied("Task read principal required")
        if type(task_offset) is not int or not 0 <= task_offset <= 100000:
            raise ValueError("Task offset must be an integer in 0..100000")
        project = principal.project_id
        with self._transaction(project) as cursor:
            cursor.execute("SELECT count(*) FROM tasks WHERE project_id=%s", (project,))
            task_count = cursor.fetchone()[0]
            cursor.execute("""SELECT legacy_id,task_uuid,title,status,mode,version,
                steps_done,steps_total,updated_at,worktree,metadata,started_at,completed_at
                FROM tasks WHERE project_id=%s
                ORDER BY (status IN ('active','in_progress')) DESC,updated_at DESC,task_uuid
                LIMIT 60 OFFSET %s""", (project, task_offset))
            tasks = cursor.fetchall()
            cursor.execute("""SELECT id,status,title,updated_at FROM runs
                WHERE project_id=%s ORDER BY updated_at DESC,id LIMIT 10""", (project,))
            runs = cursor.fetchall()
            cursor.execute("""SELECT event_type,created_at,task_uuid,source FROM events
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
            # SUM(bigint) is PostgreSQL numeric, decoded as Decimal by pg8000.
            # These counters are integral and must remain JSON serializable.
            usage = tuple(int(value or 0) for value in cursor.fetchone())
            cursor.execute("""SELECT provider,model,count(*),coalesce(sum(prompt_tokens),0),
                coalesce(sum(completion_tokens),0) FROM project_llm_usage WHERE project_id=%s
                GROUP BY provider,model ORDER BY count(*) DESC,provider,model LIMIT 20""", (project,))
            usage_models = cursor.fetchall()
            cursor.execute("""SELECT model,prompt_tokens,completion_tokens,usage_source,recorded_at
                FROM project_llm_usage WHERE project_id=%s ORDER BY recorded_at DESC,id DESC LIMIT 10""", (project,))
            usage_recent = cursor.fetchall()
            cursor.execute("SELECT root_path FROM projects WHERE id=%s AND status='active'", (project,))
            registered = cursor.fetchone()
            cursor.execute("SELECT count(*) FROM tasks WHERE project_id=%s AND status='done'", (project,))
            done_count = cursor.fetchone()[0]
            cursor.execute("""SELECT type,count(*) FROM legacy_kg_nodes WHERE project_id=%s
                GROUP BY type ORDER BY count(*) DESC,type LIMIT 12""", (project,))
            graph_types = cursor.fetchall()

        label = _text(project)
        active_id = next((str(row[0] or row[1]) for row in tasks if row[3] in {"active", "in_progress"}), "")
        cards = project_card(project, task_count, done_count, active_id, usage[1] + usage[2])
        pipeline, task_details, task_interactions = task_cards(project, tasks, task_count, events, offset=task_offset)
        health = global_stack_health()
        run_items = "".join(
            f'<div>{_text(run_id)} · {_text(status)} · {_text(title)}</div>'
            for run_id, status, title, _ in runs
        ) or "<div>Aucun run récent.</div>"
        event_items = "".join(
            f'<div class="team-event-row"><time>{_text(created.isoformat() if created else "")}</time>'
            f'<strong>{_text(kind)}</strong><span>{_text(source or "")}</span></div>'
            for kind, created, _, source in events
        ) or "<div>Aucun événement récent.</div>"
        schedule_items = "".join(
            f'<div class="schedule-row" data-schedule="{_text(schedule_id)}">'
            f'{_text(name)} · {_text(status)} · {_text(cron)} ({_text(zone)})'
            f' · prochain : {_text(next_due.isoformat() if next_due else "—")}'
            f' · dernier : {_text(last_due.isoformat() if last_due else "—")}'
            f' · exécution qualifiée : {"oui" if qualified == "true" else "non"}</div>'
            for schedule_id, name, status, cron, zone, next_due, last_due, qualified in schedules
        )
        history_items = "".join(
            f'<div>{_text(name)} · {_text(event_type)} · {_text(status)}'
            f' · {_text(occurred.isoformat() if occurred else "")}</div>'
            for name, event_type, status, occurred in schedule_events
        )
        schedule_panel = (schedule_items
                          + ('<div>Historique récent</div>' + history_items if history_items else ""))
        if not schedule_panel:
            schedule_panel = _empty_state(
                "Aucune planification",
                "Aucun job du projet n'est enregistré ici. Les tâches Windows ne sont pas incluses.",
                "planifications PostgreSQL du projet")
        plugin_panel = "".join(
            f'<div>{_text(name)} · version {_text(version or "inconnue")} · '
            f'{"actif" if enabled else "désactivé"}</div>'
            for name, version, enabled in plugins
        ) or _empty_state(
            "Aucun plugin",
            "Le registre de ce projet est vide. Les plugins Codex du poste ne sont pas inclus.",
            "registre Plugin SDK du projet")
        plugin_panel = ('<div class="team-metric-grid">'
                        + metric("Plugins affichés", len(plugins))
                        + metric("Activés affichés", sum(bool(enabled) for _, _, enabled in plugins))
                        + metric("Contrôles", "—", "Non mesurés") + '</div>' + plugin_panel)
        memory_panel = "".join(
            f'<div>{_text(task_type)} · {count} entrée(s)</div>'
            for task_type, count in memory_groups
        ) or _empty_state(
            "Aucune entrée mémoire",
            "Aucune mémoire n'est attribuée à ce projet. La fiche de contexte Codex n'est pas comptée ici.",
            "mémoire du projet")
        if budget is None:
            metrics_panel = _empty_state(
                "Non configuré", "Aucun plafond de consommation n'est enregistré pour ce projet.",
                "budget du projet")
        else:
            model_tokens, daily_runs, storage_mb = budget
            metrics_panel = (f'<div>Plafonds du projet : {model_tokens} jetons modèle/jour, '
                             f'{daily_runs} runs/jour, {storage_mb} Mo de stockage.</div>')
        if graph_stats is None:
            graph_panel = "<div>Aucun graphe historique attribué à ce projet.</div>"
        else:
            nodes, edges = graph_stats
            graph_panel = ('<div class="team-metric-grid team-two-metrics">'
                           + metric("Nœuds", nodes) + metric("Arêtes", edges) + '</div>'
                           + f'<div class="component-detail">{nodes} nœuds · {edges} arêtes historiques du projet, hors relations en quarantaine.</div>'
                           + ''.join(f'<div class="token-layer"><span class="token-name">{_text(kind)}</span>'
                                     f'<span class="token-reduction">{count} nœuds</span></div>' for kind, count in graph_types))
        service_metrics = ('<div class="team-metric-grid team-two-metrics">'
                           + metric("Événements récents", len(events)) + metric("Runs récents", len(runs))
                           + metric("Jetons attribués", usage[1] + usage[2]) + metric("Coût", "—", "Non disponible") + '</div>')
        availability = _empty_state(
            "Non mesurées",
            "La mesure quotidienne des dépassements n'est pas disponible pour ce projet."
            if budget else "Aucun budget n'est enregistré et aucun dépassement quotidien n'est mesuré.",
            "budget et consommation quotidienne du projet")
        protocol_compliance = _empty_state(
            "Non mesurée", "Aucun contrôle du protocole agent n'est produit pour ce projet.",
            "contrôles de conformité du projet")
        postgres_card = ('<div class="component team-service"><div><strong>PostgreSQL · lecture du projet vérifiée</strong>'
                         f'<div class="component-detail">{task_count} tâches · source transactionnelle du projet</div>'
                         '<span class="team-service-tag">Lecture vérifiée</span><span class="team-service-tag">Droits par projet</span>'
                         '<span class="team-service-tag">Persistance</span></div><span class="status-ok">✓</span></div>')
        code_health = project_code_health(registered[0] if registered else None)
        return {
            "schema_version": 1,
            "project": project,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "sections": {
                "project_cards": cards,
                "tasks_pipeline": pipeline,
                "services_monitoring": code_health_card(project, code_health) + render_global_stack_health(health) + postgres_card + panel("Planifications du projet", schedule_panel),
                "automation_hooks": panel("Planifications PostgreSQL", schedule_panel),
                "token_activity_report": usage_panel(usage, usage_models, usage_recent, run_items),
                "context_composition": panel(
                    "Composition du contexte",
                    '<div class="team-context-document" data-team-context-document '
                    'role="status">Chargement de la fiche et des décisions du projet…</div>'
                    + memory_panel),
                "metrics_service_summary": panel("Metrics Service", service_metrics) + panel("Budget du projet", metrics_panel) + panel("Alertes de consommation", availability) + panel("Conformité du protocole agent", protocol_compliance),
                "event_bus_recent": panel("Événements récents", '<div class="team-scroll">' + event_items + '</div>'),
                "knowledge_graph_summary": panel("Graphe du projet", graph_panel),
                "plugin_status": panel("Plugin SDK", plugin_panel),
            },
            "runs": run_items,
            "task_details": task_details,
            "task_interactions": task_interactions,
            "token_metrics": {"totals": {"tokens": usage[1] + usage[2]},
                              "projects": {project: {"tokens": usage[1] + usage[2]}}},
            "service_health": health,
            "context_sources": {"repowise": {"available": code_health is not None,
                                              "indexed_commit": code_health["commit"] if code_health else "",
                                              "file_count": code_health["count"] if code_health else 0}},
            "cache": {},
            "counts": {"tasks": task_count, "shown_tasks": len(tasks), "runs": len(runs)},
        }
