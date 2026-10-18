"""Render the two Cockpit templates with a single authorized project snapshot."""

from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path
from urllib.parse import quote


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
  if (!['POST', 'DELETE', 'PUT', 'PATCH'].includes(method)) return teamFetch(target, options);
  const sessionResponse = await teamFetch('/api/auth/session', {cache: 'no-store'});
  if (!sessionResponse.ok) throw new Error('Session unavailable');
  const session = await sessionResponse.json();
  if (session.project !== window.devcoreActiveProject ||
      !Array.isArray(session.actions) || !session.actions.includes('task.mutate') ||
      typeof session.csrf_token !== 'string') throw new Error('Project action denied');
  const headers = new Headers(options.headers || {});
  headers.set('X-CSRF-Token', session.csrf_token);
  return teamFetch(target, {...options, headers});
};
</script>"""


def _script_json(value: object) -> str:
    return (json.dumps(value, ensure_ascii=True, separators=(",", ":"))
            .replace("<", "\\u003c").replace(">", "\\u003e")
            .replace("&", "\\u0026"))


def _configuration(snapshot: dict) -> str:
    names = {'router': 'Gemini Router', 'headroom-native': 'Headroom natif',
             'headroom-auxiliary': 'Headroom auxiliaire', 'gateway': 'API Gateway',
             'scheduler': 'Scheduler PostgreSQL', 'repowise': 'RepoWise'}
    states = snapshot.get('service_health', {}).get('services', {})
    rows = ''.join('<div class="component"><span>' + label + '</span>'
                   + '<span data-team-service="' + name + '">'
                   + ('En ligne' if states.get(name) else 'Non supervisé') + '</span></div>'
                   for name, label in names.items())
    return ('<section class="team-panel"><h3>Configuration du projet</h3><div class="team-panel-body">'
            '<div class="component"><span>Projet connecté</span><strong data-team-project-name>' + escape(snapshot['project']) + '</strong></div>'
            '<div class="component"><span>Profil</span><strong>Équipe · PostgreSQL</strong></div>'
            '<div class="component"><span>Rafraîchissement</span><strong>60 secondes</strong></div>'
            '<h4>Composants supervisés</h4>' + rows
            + '<p>Cette vue est en lecture seule. Les services et les clés API sont administrés sur le serveur.</p></div></section>')


def render_team_cockpit(template_dir: Path, snapshot: dict, *, terminal: bool = False, user_id: str | None = None) -> str:
    name = "template_terminal.html" if terminal else "template.html"
    page = (template_dir / name).read_text(encoding="utf-8")
    if user_id is not None:
        safe_user = escape(user_id)
        safe_project = escape(snapshot['project'])
        login_href = '/login?project=' + escape(quote(snapshot['project'], safe=''), quote=True)
        identity = ('<details id="team-profile" class="team-profile">'
                    '<summary id="team-connected-user" aria-label="Profil de ' + safe_user + '">'
                    '<span class="team-profile-avatar" aria-hidden="true">●</span>'
                    '<span>' + safe_user + '</span></summary>'
                    '<div class="team-profile-panel" aria-label="Profil">'
                    '<h3>Profil</h3>'
                    '<div>Utilisateur connecté : <strong>' + safe_user + '</strong></div>'
                    '<div>Projet : <strong data-team-profile-project>' + safe_project + '</strong></div>'
                    '<a id="team-logout" href="' + login_href + '">Déconnexion</a>'
                    '<p id="team-profile-error" role="alert"></p>'
                    '</div></details>')
        if terminal:
            page = page.replace('<div id="tbar-r">', '<div id="tbar-r">' + identity, 1)
        else:
            page = page.replace('</header>', identity + '</header>', 1)
    for section, placeholder in _PLACEHOLDERS.items():
        value = '' if section == 'project_cards' else snapshot["sections"][section]
        page = page.replace("{{" + placeholder + "}}", value)
    page = re.sub(r'<div id="project-cards"[^>]*>\s*</div>',
                  '<nav id="team-projects" class="team-projects-initial" aria-label="Mes projets">'
                  '<span class="team-project-loading-label" role="status">Chargement des projets…</span>'
                  '</nav>', page, count=1)
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
    # Team profile deliberately has no shared settings endpoint. The standard
    # template calls it on load even though the settings panel is hidden.
    page = page.replace("// Load settings on startup\nloadSettings();",
                        "// Team profile has no shared settings endpoint.")
    page = page.replace(":20129", ":20131")
    page = page.replace('Auto-refresh 15s', 'Auto-refresh 60s')
    for old_path in ('../../README.md', '../../DEV_CORE_DATA/Logs/scripts/'):
        page = page.replace('onclick="window.open(\'' + old_path + '\',\'_blank\')"',
                            'aria-disabled="true" title="Document historique non publié dans ce profil"')
    page = page.replace('recordAppliedDashboardSnapshot(data);',
                        'recordAppliedDashboardSnapshot(data); syncTeamCockpit(data);')
    # An in-flight response for the previous session must never repaint the new project.
    page = page.replace('validateDashboardSnapshot(payload);',
                        'validateDashboardSnapshot(payload); if (payload.project !== window.devcoreActiveProject) return false;')
    page = page.replace('validateDashboardSnapshot(data);',
                        'validateDashboardSnapshot(data); if (data.project !== window.devcoreActiveProject) return false;')
    if terminal:
        page = page.replace('const sse = new EventSource(',
                            'const sse = window.devcoreTeamEventSource = new EventSource(')
    page = page.replace('/api/dashboard?project=${encodeURIComponent(window.devcoreActiveProject)}',
                        '/api/dashboard?project=${encodeURIComponent(window.devcoreActiveProject)}&task_offset=${Number(new URLSearchParams(window.location.search).get("task_offset") || 0)}')
    # The former optimization percentages were static claims, not project data.
    page = re.sub(r'<h2>Token Optimization Stack</h2>.*?(?=<div id="context-composition")',
                  '', page, flags=re.DOTALL)
    if terminal:
        page = page.replace('<body>', '<body class="team-terminal">', 1)
    # Keep the familiar tab with observable settings, without exposing shared
    # service administration or credential controls to project contributors.
    page = re.sub(r'<form id="settings-form".*?</form>', lambda _: _configuration(snapshot),
                  page, count=1, flags=re.DOTALL)
    assets = Path(__file__).parent
    style = (assets / 'team_cockpit_style.css').read_text(encoding='utf-8')
    display = (assets / 'team_cockpit_display.js').read_text(encoding='utf-8')
    bootstrap = ('window.devcoreTeamCounts=' + _script_json(snapshot.get('counts', {}))
                 + ';window.devcoreTeamHealth=' + _script_json(snapshot.get('service_health', {})) + ';')
    # Browser requests keep API errors machine-readable and return the user to login.
    page = page.replace('fetch(', 'teamFetch(')
    login_guard = """<script>
async function teamFetch(url, options) {
  const response = await fetch(url, options);
  const target = new URL(typeof url === 'string' ? url : url.url || String(url), location.href);
  const staleProject = target.searchParams.has('project') &&
    target.searchParams.get('project') !== window.devcoreActiveProject &&
    (target.pathname === '/api/dashboard' || target.pathname === '/api/dashboard/stream');
  if (!staleProject && target.origin === location.origin && [401, 403].includes(response.status)) {
    const project = window.devcoreActiveProject || new URLSearchParams(location.search).get('project');
    if (project) location.assign('/login?' + new URLSearchParams({
      project, next: location.pathname + location.search
    }).toString());
  }
  return response;
}
</script>"""
    page = page.replace('</head>', login_guard + '</head>', 1)
    page = page.replace("</head>", '<style>' + style + '</style></head>', 1)
    page = page.replace("</body>", _TEAM_ACTIONS + '<script>' + bootstrap + display + '</script></body>', 1)
    return page
