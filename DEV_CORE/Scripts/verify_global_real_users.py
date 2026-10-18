"""Read-only real-user check of the loopback PostgreSQL global Gateway."""

from __future__ import annotations

import getpass
import json
from urllib.parse import parse_qs, urlsplit

import verify_two_real_pilot_users as pilot


pilot.BASE = "http://127.0.0.1:20131"


def verify_attributed_usage(snapshot: dict, project: str) -> None:
    """Check project counters and either supported usage presentation."""
    report = snapshot.get("sections", {}).get("token_activity_report", "")
    metrics = snapshot.get("token_metrics", {})
    projects = metrics.get("projects", {})
    total = metrics.get("totals", {}).get("tokens")
    if (snapshot.get("project") != project or not isinstance(projects, dict)
            or set(projects) != {project}
            or not isinstance(projects.get(project), dict)
            or type(total) is not int or total < 0
            or type(projects[project].get("tokens")) is not int
            or projects[project]["tokens"] != total):
        raise RuntimeError("Project LLM counters are missing or not isolated")
    if not isinstance(report, str):
        raise RuntimeError("Project LLM usage report missing")
    legacy = ("Aucun appel LLM attribué" in report
              or "appel(s) Gemini attribué(s)" in report)
    current = ('class="team-panel team-usage"' in report
               and "Appels du projet" in report
               and "Consommation par modèle" in report
               and "Appels récents" in report)
    if not (legacy or current):
        raise RuntimeError("Project LLM usage presentation unavailable")


def main() -> None:
    anonymous = pilot.client()
    checks = {}
    for path, wanted in (("/login?project=devcore", 200),
                         ("/api/dashboard?project=devcore", 401)):
        status, _ = pilot.call(anonymous, path)
        pilot.expect(status, wanted, "anonymous " + path)
    # urllib follows the Cockpit's 303; require its final destination to be login.
    for path in ("/index.html", "/index_terminal.html"):
        with anonymous.open(pilot.BASE + path + "?project=devcore", timeout=10) as response:
            target = urlsplit(response.geturl())
            query = parse_qs(target.query)
            if (response.status != 200 or target.path != "/login"
                    or query.get("project") != ["devcore"]
                    or query.get("next") != [path + "?project=devcore"]):
                raise RuntimeError("Anonymous Cockpit did not redirect to project login")
    for user in ("majdi", "mohd"):
        opener = pilot.client()
        csrf = None
        password = getpass.getpass(f"DevCore password for {user}: ")
        try:
            status, body = pilot.call(opener, "/api/auth/session", method="POST",
                                      payload={"user_id": user, "password": password,
                                               "project": "devcore"})
            pilot.expect(status, 200, user + " login")
            session = json.loads(body)
            if session.get("user_id") != user or session.get("project") != "devcore":
                raise RuntimeError("Unexpected session identity")
            csrf = session["csrf_token"]
        finally:
            del password
        try:
            for path in ("/api/dashboard?project=devcore",
                         "/cockpit?project=devcore",
                         "/cockpit/terminal?project=devcore",
                         "/index.html?project=devcore",
                         "/index_terminal.html?project=devcore",
                         "/api/dashboard/tasks?project=devcore&limit=1&offset=0"):
                status, body = pilot.call(opener, path)
                pilot.expect(status, 200, user + " " + path)
                if path.startswith("/api/dashboard?"):
                    snapshot = json.loads(body)
                    if snapshot.get("project") != "devcore":
                        raise RuntimeError("Dashboard project mismatch")
                    sections = snapshot.get("sections", {})
                    for name in ("plugin_status", "context_composition",
                                 "metrics_service_summary", "knowledge_graph_summary",
                                 "token_activity_report"):
                        value = sections.get(name)
                        if not isinstance(value, str) or not value or "non encore" in value:
                            raise RuntimeError("Cockpit source section unavailable: " + name)
                    if "2268 nœuds · 681642 arêtes historiques" not in sections["knowledge_graph_summary"]:
                        raise RuntimeError("Project graph scope differs from qualified source")
                    verify_attributed_usage(snapshot, "devcore")
            status, _ = pilot.call(opener, "/api/dashboard?project=scripts")
            pilot.expect(status, 403, user + " cross-project dashboard")
            checks[user] = {"login": 200, "cockpits": [200, 200, 200, 200],
                            "dashboard": 200, "tasks": 200, "cross_project": 403}
        finally:
            if csrf:
                status, _ = pilot.call(opener, "/api/auth/session", method="DELETE", csrf=csrf)
                pilot.expect(status, 200, user + " logout")
                status, _ = pilot.call(opener, "/api/auth/session")
                pilot.expect(status, 401, user + " revoked")
    print(json.dumps({"status": "global_real_users_verified", "anonymous": "denied",
                      "cockpit_sources": ["plugins", "memory_entries", "budgets",
                                          "project_graph", "project_llm_usage"],
                      "users": checks, "logouts": "verified"}, separators=(",", ":")))


if __name__ == "__main__":
    main()
