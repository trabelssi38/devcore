"""Render the two Cockpit templates with a single authorized project snapshot."""

from __future__ import annotations

import json
from pathlib import Path


_PLACEHOLDERS = {
    "project_cards": "PROJECT_CARDS",
    "tasks_pipeline": "TASKS_PIPELINE",
    "services_monitoring": "SERVICES_MONITORING",
    "automation_hooks": "AUTOMATION_HOOKS",
    "token_activity_report": "TOKEN_ACTIVITY_REPORT",
    "context_composition": "CONTEXT_COMPOSITION",
    "metrics_service_summary": "METRICS_SERVICE_SUMMARY",
    "event_bus_recent": "EVENT_BUS_RECENT",
    "knowledge_graph_summary": "KNOWLEDGE_GRAPH_SUMMARY",
    "plugin_status": "PLUGIN_STATUS",
}

_TEAM_ACTIONS = """<script>
apiFetch = async function(url, options = {}) {
  const target = new URL(url, window.location.href);
  if (target.origin !== window.location.origin) throw new Error('Cross-origin action refused');
  const method = String(options.method || 'GET').toUpperCase();
  if (!['POST', 'DELETE', 'PUT', 'PATCH'].includes(method)) return fetch(target, options);
  const sessionResponse = await fetch('/api/auth/session', {cache: 'no-store'});
  if (!sessionResponse.ok) throw new Error('Session unavailable');
  const session = await sessionResponse.json();
  if (session.project !== window.devcoreActiveProject ||
      !Array.isArray(session.actions) || !session.actions.includes('task.mutate') ||
      typeof session.csrf_token !== 'string') throw new Error('Project action denied');
  const headers = new Headers(options.headers || {});
  headers.set('X-CSRF-Token', session.csrf_token);
  return fetch(target, {...options, headers});
};
</script>"""


def _script_json(value: object) -> str:
    return (json.dumps(value, ensure_ascii=True, separators=(",", ":"))
            .replace("<", "\\u003c").replace(">", "\\u003e")
            .replace("&", "\\u0026"))


def render_team_cockpit(template_dir: Path, snapshot: dict, *, terminal: bool = False) -> str:
    name = "template_terminal.html" if terminal else "template.html"
    page = (template_dir / name).read_text(encoding="utf-8")
    for section, placeholder in _PLACEHOLDERS.items():
        page = page.replace("{{" + placeholder + "}}", snapshot["sections"][section])
    for key, placeholder in (
        ("task_details", "TASK_DETAILS_MAP"),
        ("task_interactions", "TASK_INTERACTIONS_MAP"),
        ("token_metrics", "TOKEN_METRICS_JSON"),
    ):
        page = page.replace("{{" + placeholder + "}}", _script_json(snapshot[key]))
    project_literal = _script_json(snapshot["project"])[1:-1]
    page = page.replace("{{ACTIVE_PROJECT_NAME}}", project_literal)
    page = page.replace("{{VERSION}}", "team-pg")
    page = page.replace("window.location.href='index_terminal.html'",
                        "window.location.href='/index_terminal.html?project='+encodeURIComponent(window.devcoreActiveProject)")
    page = page.replace("window.location.href='/'",
                        "window.location.href='/index.html?project='+encodeURIComponent(window.devcoreActiveProject)")
    if terminal:
        page = page.replace("// Load settings on startup\nloadSettings();",
                            "// Team profile has no shared settings endpoint.")
        page = page.replace('id="sys-status">ONLINE', 'id="sys-status">—')
        page = page.replace('id="api-ok">:20129 ✓', 'id="api-ok">:20131')
        page = page.replace('SCHEDULER <span class="v-ok">ACTIVE', 'SCHEDULER <span class="v-ok">—')
        page = page.replace('REPOWISE <span class="v-cyan">MCP', 'REPOWISE <span class="v-cyan">—')
    # The historical settings and plugin controls have no scoped team backend.
    page = page.replace("</head>", "<style>#tab-settings-title,#tab-settings-content{display:none!important}</style></head>", 1)
    page = page.replace("</body>", _TEAM_ACTIONS + "</body>", 1)
    return page
