"""Read the supervised global-stack candidate without trusting stale receipts."""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape
import json
import os
from pathlib import Path


NAMES = {
    "router": "Gemini Router",
    "headroom-native": "Headroom natif",
    "headroom-auxiliary": "Headroom auxiliaire",
    "gateway": "API Gateway",
    "scheduler": "Scheduler PostgreSQL",
    "repowise": "RepoWise",
}


def global_stack_health(path: str | None = None, *, now: datetime | None = None) -> dict:
    raw_path = path if path is not None else os.environ.get("DEVCORE_GLOBAL_STACK_MANIFEST", "")
    if not raw_path or not Path(raw_path).is_absolute():
        return {"status": "unmonitored", "services": {}}
    try:
        manifest_path = Path(raw_path)
        if manifest_path.stat().st_size > 65536:
            raise ValueError("Manifest too large")
        record = json.loads(manifest_path.read_text(encoding="utf-8"))
        checked = datetime.fromisoformat(record["heartbeat_utc"])
        current = now or datetime.now(timezone.utc)
        age = (current - checked).total_seconds()
        if checked.tzinfo is None or age < -5 or age > 8 or record.get("status") != "ready":
            raise ValueError("Manifest is not live")
        processes = record["processes"]
        health = record["health"]
        services = {name: bool(health.get(name)) for name in NAMES if name in processes}
        if not all(name in services for name in NAMES if name != "repowise"):
            raise ValueError("Missing core service")
        return {"status": "ready" if all(services.values()) else "degraded",
                "services": services, "checked_at": checked.isoformat()}
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return {"status": "unavailable", "services": {}}


def render_global_stack_health(state: dict) -> str:
    from .cockpit_presentation import panel

    status = state.get("status")
    if status != "ready" and status != "degraded":
        return panel("Services & infrastructure", "<div>Supervision de pile globale indisponible.</div>")
    ports = {"router": "20130", "headroom-native": "8787", "headroom-auxiliary": "8789",
             "gateway": "20131", "scheduler": "PostgreSQL · baux durables", "repowise": "7337"}
    roles = {"router": "Routage Gemini", "headroom-native": "Route native", "headroom-auxiliary": "Route auxiliaire",
             "gateway": "Cockpit API", "scheduler": "Orchestration", "repowise": "Analytics & MCP"}
    rows = []
    for name, label in NAMES.items():
        if name not in state["services"]:
            continue
        state_label = "en ligne" if state["services"][name] else "indisponible"
        css = 'status-ok' if state['services'][name] else 'status-error'
        rows.append(f'<div class="component service-row team-service" data-service="{escape(name, quote=True)}">'
                    f'<div><strong>{escape(label)} · {state_label}</strong>'
                    f'<div class="component-detail">{ports[name]}</div>'
                    f'<span class="team-service-tag">Sonde : {state_label}</span>'
                    '<span class="team-service-tag">Solic. : non mesurée</span>'
                    f'<span class="team-service-tag team-impact">{roles[name]}</span></div>'
                    f'<span class="{css}">{"✓" if state["services"][name] else "✗"}</span></div>')
    return panel('Services & infrastructure', "".join(rows))
