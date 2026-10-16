"""Small same-origin sign-in page for the PostgreSQL team Cockpit."""

from __future__ import annotations

from html import escape


def render_team_login(project: str) -> str:
    safe_project = escape(project, quote=True)
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
  location.assign('/cockpit?project=' + encodeURIComponent(project));
}});
</script></body></html>"""
