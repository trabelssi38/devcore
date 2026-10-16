"""Read-only real-user check of the loopback PostgreSQL global Gateway."""

from __future__ import annotations

import getpass
import json

import verify_two_real_pilot_users as pilot


pilot.BASE = "http://127.0.0.1:20131"


def main() -> None:
    anonymous = pilot.client()
    checks = {}
    for path, wanted in (("/login?project=devcore", 200),
                         ("/index.html?project=devcore", 401),
                         ("/api/dashboard?project=devcore", 401)):
        status, _ = pilot.call(anonymous, path)
        pilot.expect(status, wanted, "anonymous " + path)
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
                         "/index.html?project=devcore",
                         "/index_terminal.html?project=devcore",
                         "/api/dashboard/tasks?project=devcore&limit=1&offset=0"):
                status, body = pilot.call(opener, path)
                pilot.expect(status, 200, user + " " + path)
                if path.startswith("/api/dashboard?") and json.loads(body).get("project") != "devcore":
                    raise RuntimeError("Dashboard project mismatch")
            status, _ = pilot.call(opener, "/api/dashboard?project=scripts")
            pilot.expect(status, 403, user + " cross-project dashboard")
            checks[user] = {"login": 200, "cockpits": [200, 200],
                            "dashboard": 200, "tasks": 200, "cross_project": 403}
        finally:
            if csrf:
                status, _ = pilot.call(opener, "/api/auth/session", method="DELETE", csrf=csrf)
                pilot.expect(status, 200, user + " logout")
                status, _ = pilot.call(opener, "/api/auth/session")
                pilot.expect(status, 401, user + " revoked")
    print(json.dumps({"status": "global_real_users_verified", "anonymous": "denied",
                      "users": checks, "logouts": "verified"}, separators=(",", ":")))


if __name__ == "__main__":
    main()
