"""Read-only HTTP pilot for two real users of the active localhost service.

The script creates then revokes browser sessions. Passwords are prompted
locally, never accepted on the command line, and never printed.
"""
from __future__ import annotations

import getpass
import http.cookiejar
import json
import urllib.error
import urllib.parse
import urllib.request


BASE = "http://127.0.0.1:20129"


def client():
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def call(opener, path: str, *, method="GET", payload=None, csrf=None):
    headers = {"Origin": BASE}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if csrf is not None:
        headers["X-CSRF-Token"] = csrf
    request = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with opener.open(request, timeout=15) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def expect(status, wanted, label):
    if status != wanted:
        raise RuntimeError(f"{label}: HTTP {status}, expected {wanted}")


def main():
    accounts = {}
    result = {}
    logout_failures = []
    try:
        for user in ("majdi", "mohd"):
            opener = client()
            password = getpass.getpass(f"Password for {user}: ")
            try:
                status, body = call(opener, "/api/auth/session", method="POST",
                                    payload={"user_id": user, "password": password, "project": "devcore"})
                expect(status, 200, f"{user} login")
                session = json.loads(body)
                if session.get("user_id") != user or session.get("project") != "devcore":
                    raise RuntimeError(f"{user}: unexpected session identity")
                accounts[user] = (opener, session["csrf_token"])
                if user == "majdi":
                    scripts_opener = client()
                    status, body = call(scripts_opener, "/api/auth/session", method="POST",
                                        payload={"user_id": user, "password": password, "project": "scripts"})
                    expect(status, 200, "majdi scripts login")
                    scripts_session = json.loads(body)
                    if scripts_session.get("user_id") != user or scripts_session.get("project") != "scripts":
                        raise RuntimeError("majdi: unexpected scripts session identity")
                    accounts["majdi_scripts"] = (scripts_opener, scripts_session["csrf_token"])
            finally:
                del password

        for user in ("majdi", "mohd"):
            opener, _ = accounts[user]
            status, body = call(opener, "/api/dashboard/tasks?project=devcore&limit=10&offset=0")
            expect(status, 200, f"{user} devcore read")
            tasks = json.loads(body)
            if not isinstance(tasks, list) or any(task.get("project") != "devcore" for task in tasks):
                raise RuntimeError(f"{user}: unexpected project in task response")
            result[f"{user}_devcore_read"] = status

        status, _ = call(accounts["mohd"][0], "/api/dashboard/tasks?project=scripts&limit=1&offset=0")
        expect(status, 403, "mohd cross-project read")
        result["mohd_scripts_denied"] = status

        status, _ = call(accounts["majdi"][0], "/api/dashboard/tasks?project=scripts&limit=1&offset=0")
        expect(status, 403, "majdi devcore session cross-project read")
        result["majdi_devcore_session_scripts_denied"] = status

        status, _ = call(accounts["majdi_scripts"][0], "/api/dashboard/tasks?project=scripts&limit=1&offset=0")
        expect(status, 200, "majdi scripts read")
        result["majdi_scripts_read"] = status
    finally:
        for user, (opener, csrf) in accounts.items():
            try:
                status, _ = call(opener, "/api/auth/session", method="DELETE", csrf=csrf)
                after, _ = call(opener, "/api/auth/session")
                if status != 200 or after != 401:
                    logout_failures.append({"user": user, "logout": status, "after": after})
            except Exception as exc:
                logout_failures.append({"user": user, "error": type(exc).__name__})
    if logout_failures:
        raise RuntimeError(f"Logout verification failed: {logout_failures}")
    print(json.dumps({"status": "two_real_users_http_verified", **result,
                      "logouts": "verified"}))


if __name__ == "__main__":
    main()
