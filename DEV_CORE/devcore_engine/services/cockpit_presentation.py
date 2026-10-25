"""Shared Cockpit cards populated only from the authorized project snapshot."""

from __future__ import annotations

from collections import defaultdict
from contextlib import closing
from datetime import datetime
from html import escape
import json
from pathlib import Path
import sqlite3
from urllib.parse import urlencode
from zoneinfo import ZoneInfo


COCKPIT_TIMEZONE = ZoneInfo("Africa/Tunis")


def cockpit_datetime(value: datetime | None) -> datetime | None:
    """Present aware database timestamps in the Cockpit's Tunisia time zone."""
    return value.astimezone(COCKPIT_TIMEZONE) if value and value.tzinfo else value


def display(value: object) -> str:
    raw = str(value if value is not None else "")
    # Some historical step labels were decoded with a Windows code page during
    # import. Reverse only complete, valid UTF-8 round trips at display time.
    if any(marker in raw for marker in ('أ©', 'أ\u00a0', 'Ã', 'Â')):
        for encoding in ('cp1256', 'cp1252', 'latin1'):
            try:
                return raw.encode(encoding).decode('utf-8')
            except (UnicodeEncodeError, UnicodeDecodeError):
                continue
    return raw


def text(value: object) -> str:
    return escape(display(value), quote=True)


def panel(title: str, body: str, *, css: str = "") -> str:
    return (f'<section class="team-panel {css}"><h3>{text(title)}</h3>'
            f'<div class="team-panel-body">{body}</div></section>')


def metric(label: str, value: object, subtitle: str = "") -> str:
    return (f'<div class="card"><span class="card-title">{text(label)}</span>'
            f'<strong class="card-val">{text(value)}</strong>'
            f'<span class="card-sub">{text(subtitle)}</span></div>')


def number(value: int) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if value >= 1000:
        return f"{value / 1000:.1f}K"
    return str(value)


def _date(value: object) -> str:
    value = cockpit_datetime(value) if isinstance(value, datetime) else value
    return value.isoformat(sep=" ", timespec="seconds") if value else ""


def task_cards(project: str, rows: list, task_count: int, events: list, *, offset: int = 0) -> tuple:
    groups: dict[str, list[str]] = defaultdict(list)
    details, interactions = {}, {}
    for legacy, uuid, title, status, mode, version, done, total, updated, worktree, metadata, started, completed in rows:
        task_id = str(legacy or uuid)
        key = f"{project}_{task_id}"
        metadata = metadata if isinstance(metadata, (dict, list)) else {}
        steps = metadata if isinstance(metadata, list) else metadata.get("steps", [])
        steps = steps[:100] if isinstance(steps, list) else []
        lines, inline = [], []
        for step in steps:
            label = display(step.get("title", ""))[:2000] if isinstance(step, dict) else display(step)[:2000]
            checked = step.get("done") is True if isinstance(step, dict) else False
            lines.append(f'[{"v" if checked else " "}] {label}')
            inline.append(f'<div class="step-item {"step-done" if checked else ""}">'
                          f'<b>[{"v" if checked else " "}]</b> {text(label)}</div>')
        description = metadata.get("details", "") if isinstance(metadata, dict) else ""
        description = display(description) if isinstance(description, str) else ""
        detail = "\n".join(([description[:12000]] if description else []) + lines)
        if detail:
            details[key] = detail
        task_events = [{"event_type": kind, "created_at": _date(created), "details": ""}
                       for kind, created, event_uuid, *_ in events if str(event_uuid) == str(uuid)]
        interactions[key] = {"project": project, "task_id": task_id, "title": display(title),
                             "events": task_events, "metrics_available": False}
        css = "done" if status == "done" else "active" if status in {"active", "in_progress"} else "todo"
        attrs = (f'data-project="{text(project)}" data-task-id="{text(task_id)}" '
                 f'data-version="{version}" data-status="{text(status)}"')
        buttons = ''
        if detail:
            buttons += (f'<button class="btn-action btn-details" {attrs} '
                        'onclick="showDetails(this.dataset.project,this.dataset.taskId,this.dataset.status,this,event)">Détails</button>')
        buttons += (f'<button class="btn-action btn-interactions" {attrs} '
                    'onclick="showInteractions(this.dataset.project,this.dataset.taskId,this,event)">Inter.</button>')
        mutations = ''
        if status not in {"done", "deleted"}:
            mutations += (f'<button class="btn-action btn-done" {attrs} '
                          'onclick="completeTask(this.dataset.project,this.dataset.taskId,event,Number(this.dataset.version))">Clôturer</button>')
        if status != "deleted":
            mutations += (f'<button class="btn-action btn-delete" title="Supprimer la tâche" {attrs} '
                          'onclick="deleteTask(this.dataset.project,this.dataset.taskId,event,Number(this.dataset.version))">⌫</button>')
        dates = " · ".join(value for value in (
            f"Début : {_date(started)}" if started else "",
            f"Fin : {_date(completed)}" if completed else "") if value)
        steps_html = '<div class="steps-container">' + ''.join(inline) + '</div>' if inline else ''
        groups[str(worktree or "Non renseigné")].append(
            f'<article class="mission {css} {"active-task" if css == "active" else ""}" data-date="{text(_date(updated))}">'
            f'<div class="mission-header team-mission-header"><span class="badge {css}">{text(status.upper())}</span>'
            f'<div class="team-mission-main"><div class="mission-title team-mission-title">'
            f'<span class="team-task-label" title="{text(task_id)}: {text(title)}">{text(task_id)}: {text(title)}</span>'
            f'<span class="team-task-actions">{buttons}</span></div>'
            f'<div class="component-detail">Mode: {text(mode)} · {done}/{total} étapes · version {version}</div>'
            f'{f"<div class=component-detail>{text(dates)}</div>" if dates else ""}</div>'
            f'<div class="team-mutations">{mutations}</div></div>'
            f'{steps_html}</article>')
    body = ''.join(f'<details open class="team-worktree"><summary>Worktree : {text(wt)}</summary>'
                   + ''.join(cards) + '</details>' for wt, cards in groups.items())
    navigation = ''
    for label, page in (('← Tâches précédentes', max(0, offset - 60)), ('Tâches plus anciennes →', offset + 60)):
        if (page < offset) or (page > offset and page < task_count):
            navigation += f'<a class="btn-action btn-details" href="?{text(urlencode({"project": project, "task_offset": page}))}">{label}</a>'
    pipeline = (f'<details open class="project-tasks-group" data-project="{text(project)}">'
                f'<summary class="team-project-title">Projet : {text(project)} · {task_count} tâches</summary>'
                f'{body}<div class="component-detail">{len(rows)} tâches affichées sur {task_count} · à partir de {offset + 1 if rows else 0}.</div>'
                f'<nav class="team-pagination">{navigation}</nav></details>')
    return pipeline, details, interactions


def project_card(project: str, task_count: int, done_count: int, active_id: str, tokens: int) -> str:
    progress = round(100 * done_count / task_count) if task_count else 0
    return (f'<div class="project-row team-project-card selected" data-project="{text(project)}">'
            f'<div class="team-project-heading"><span class="project-dot status-ok"></span>'
            f'<strong>{text(project)}</strong><strong>{progress}%</strong></div>'
            f'<div class="component-detail">{text(active_id or "Aucune tâche active")} · {task_count} tâches</div>'
            f'<div class="team-progress"><span style="width:{progress}%"></span></div>'
            f'<div class="component-detail">{done_count} terminées · {number(tokens)} jetons attribués</div></div>')


def usage_panel(usage: tuple, models: list, recent: list, runs: str) -> str:
    calls, prompt, completion, unreported = usage
    cards = metric("Jetons entrée", number(prompt)) + metric("Jetons sortie", number(completion))
    cards += metric("Appels du projet", calls, f"{unreported} sans usage fournisseur" if unreported else "Usage fournisseur")
    model_rows = ''.join(f'<div class="team-model-row"><span>{text(provider)} · {text(model)}</span>'
                         f'<span>{n} appel(s) · {number(p or 0)} entrée / {number(c or 0)} sortie</span></div>'
                         for provider, model, n, p, c in models)
    call_rows = ''.join(f'<div class="session-row team-session-row" data-project="">'
                        f'<strong>{text(model)}</strong><span>{text(_date(at))}</span>'
                        f'<span>{number((p or 0) + (c or 0))} jetons · {text(source)}</span></div>'
                        for model, p, c, source, at in recent)
    body = f'<div class="team-metric-grid">{cards}</div>'
    body += '<div class="component-detail">Coût : non disponible dans les données attribuées au projet.</div>'
    body += '<h4>Consommation par modèle</h4><div class="team-scroll">' + (model_rows or '<p>Aucun appel LLM attribué à ce projet.</p>') + '</div>'
    body += '<h4>Appels récents</h4><div class="team-scroll">' + (call_rows or '<p>Aucun appel récent.</p>') + '</div>'
    body += '<h4>Runs récents</h4><div class="team-scroll">' + runs + '</div>'
    return ('<details open class="team-panel team-usage"><summary class="team-panel-heading">'
            'Supervision Headroom · Consommation & activité du projet'
            f'<span class="headroom-toggle-text"></span></summary><div class="team-panel-body">{body}</div></details>')


def project_code_health(root: object) -> dict | None:
    """Read the registered project's own RepoWise snapshot, without DB writes."""
    try:
        if not Path(root).is_absolute():
            return None
        base = Path(root).resolve(strict=True)
        directory = (base / ".repowise").resolve(strict=True)
        db = (directory / "wiki.db").resolve(strict=True)
        state_file = (directory / "state.json").resolve(strict=True)
        if not base.is_absolute() or not directory.is_relative_to(base) or not db.is_relative_to(directory) or not state_file.is_relative_to(directory):
            return None
        if state_file.stat().st_size > 65536:
            return None
        state = json.loads(state_file.read_text(encoding="utf-8"))
        with closing(sqlite3.connect(db.as_uri() + "?mode=ro", uri=True, timeout=1)) as connection:
            connection.execute("PRAGMA query_only=ON")
            row = connection.execute("""SELECT count(*),avg(score),avg(maintainability_score),
                avg(performance_score),sum(score>=8),sum(score>=6 AND score<8),sum(score<6)
                FROM health_file_metrics""").fetchone()
            targets = connection.execute("SELECT file_path,score FROM health_file_metrics WHERE score<6 ORDER BY score,file_path LIMIT 3").fetchall()
        if not row or not row[0]:
            return None
        return {"count": row[0], "score": row[1], "maintainability": row[2], "performance": row[3],
                "bands": row[4:], "targets": targets, "commit": str(state.get("last_sync_commit", ""))[:12]}
    except (OSError, ValueError, TypeError, sqlite3.Error):
        return None


def code_health_card(project: str, health: dict | None) -> str:
    if health is None:
        return panel(f"RepoWise Health : {project}", '<p>Mesures du dépôt indisponibles pour ce projet.</p>')
    def score(value):
        return f"{value:.1f}/10" if value is not None else "—"
    metrics = metric("Score global", score(health['score']), f"{health['count']} fichiers")
    metrics += metric("Maintenabilité", score(health['maintainability']))
    metrics += metric("Performance", score(health['performance']))
    band_rows = []
    for n, label, color in zip(health['bands'], ('sains', 'à surveiller', 'alertes'), ('#00ff88','#ffe44e','#ff4455')):
        percent = 100 * (n or 0) / health['count']
        band_rows.append(f'<span style="width:{percent:.2f}%;background:{color}" title="{n or 0} {label}"></span>')
    targets = ''.join(f'<div class="team-target"><code>{text(path)}</code><span>{score(value)}</span></div>' for path, value in health['targets'])
    body = f'<div class="component-detail">Index local du projet · instantané {text(health["commit"])}</div>'
    body += f'<div class="team-metric-grid">{metrics}</div><div class="team-distribution">{"".join(band_rows)}</div>'
    body += '<div class="component-detail">' + ' · '.join(f'{n or 0} {label} ({100 * (n or 0) / health["count"]:.1f}%)' for n,label in zip(health['bands'],('sains','à surveiller','alertes'))) + '</div>'
    body += '<h4>Cibles prioritaires de refactoring</h4>' + (targets or '<p>Aucune alerte dans cet index.</p>')
    return panel(f"RepoWise Health : {project}", body, css="repowise-health-card").replace(
        '<section ', f'<section data-project="{text(project)}" ', 1)
