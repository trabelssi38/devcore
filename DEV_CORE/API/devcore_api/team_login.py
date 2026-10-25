"""Small same-origin sign-in page for the PostgreSQL team Cockpit."""

from __future__ import annotations

from html import escape
import json
from urllib.parse import parse_qs, urlencode, urlsplit


COCKPIT_PATHS = frozenset({"/cockpit", "/cockpit/terminal", "/index.html", "/index_terminal.html"})


def cockpit_destination(project: str, target: str = "") -> str:
    fallback = "/cockpit?" + urlencode({"project": project})
    try:
        parts = urlsplit(target)
        query = parse_qs(parts.query)
        if (parts.scheme or parts.netloc or parts.fragment or parts.path not in COCKPIT_PATHS
                or query.get("project") != [project]):
            return fallback
        params = {"project": project}
        if "task_offset" in query:
            values = query["task_offset"]
            if len(values) != 1 or not values[0].isascii() or not values[0].isdecimal():
                return fallback
            offset = int(values[0])
            if offset > 100000:
                return fallback
            params["task_offset"] = offset
        return parts.path + "?" + urlencode(params)
    except (ValueError, TypeError):
        return fallback


def render_team_login(project: str, return_to: str = "") -> str:
    safe_project = escape(project, quote=True)
    destination = json.dumps(cockpit_destination(project, return_to)).replace("<", "\\u003c")
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DevCore — connexion</title>
<style>body{{font:16px system-ui,sans-serif;background:#101924;color:#e8edf5;margin:0;display:grid;min-height:100vh;place-items:center}}
main{{width:min(25rem,calc(100% - 2rem));background:#1b2938;padding:2rem;border-radius:1rem}}
label{{display:block;margin:1rem 0 .35rem}}input,button{{box-sizing:border-box;width:100%;font:inherit;padding:.7rem;border-radius:.4rem}}
input{{background:#f8fafc;color:#17202c;border:0}}button{{margin-top:1.5rem;border:0;background:#70c4ff;color:#0b1824;cursor:pointer}}
#error{{color:#ffb8b8;min-height:1.5rem}}</style></head>
<body><main><h1>DevCore</h1><p>Projet <strong>{safe_project}</strong></p>
<form id="login"><label for="user">Identifiant</label><input id="user" autocomplete="username" required>
<label for="password">Mot de passe</label><input id="password" type="password" autocomplete="current-password" required>
<button type="submit">Se connecter</button><p id="error" role="alert"></p></form></main>
<script>
const project = document.querySelector('strong').textContent;
document.querySelector('#login').addEventListener('submit', async event => {{
  event.preventDefault();
  const error = document.querySelector('#error'); error.textContent = '';
  const response = await fetch('/api/auth/session', {{method:'POST', credentials:'same-origin',
    headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{
      project, user_id:document.querySelector('#user').value,
      password:document.querySelector('#password').value
    }})}});
  document.querySelector('#password').value = '';
  if (!response.ok) {{ error.textContent = 'Connexion refusée'; return; }}
  location.assign({destination});
}});
</script></body></html>"""
