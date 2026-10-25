"""Qualify the active v252 localhost service with 20 real-account sessions.

Only session rows are created/revoked. Task requests are read-only. Passwords
are prompted locally and never written to arguments, files, or output.
"""
from __future__ import annotations

import asyncio
import getpass
import json
import statistics
import subprocess
import time
from http.cookies import SimpleCookie

import httpx


BASE = "http://127.0.0.1:20129"
ORIGIN = {"Origin": BASE}
TASK_URL = BASE + "/api/dashboard/tasks?project=devcore&limit=10&offset=0"


def ensure_v252() -> None:
    service = subprocess.run(["sc.exe", "qc", "DevCoreIndividual"],
                             capture_output=True, text=True, encoding="utf-8",
                             errors="replace", check=True)
    if "postgres-v252" not in service.stdout:
        raise RuntimeError("DevCoreIndividual is not configured for v252; load check aborted")
    response = httpx.get(BASE + "/api/status", timeout=10)
    if response.status_code != 200:
        raise RuntimeError(f"Active status probe failed: HTTP {response.status_code}")


def login(user: str, password: str) -> dict:
    response = httpx.post(BASE + "/api/auth/session", headers=ORIGIN,
                          json={"user_id": user, "password": password, "project": "devcore"},
                          timeout=15)
    if response.status_code != 200:
        raise RuntimeError(f"{user} login failed: HTTP {response.status_code}")
    body = response.json()
    if body.get("user_id") != user or body.get("project") != "devcore":
        raise RuntimeError(f"{user} login returned an unexpected identity")
    cookie = SimpleCookie()
    cookie.load(response.headers.get("set-cookie", ""))
    if "devcore_session" not in cookie or not body.get("csrf_token"):
        raise RuntimeError(f"{user} login did not return a complete session")
    return {"user": user, "cookie": cookie["devcore_session"].value,
            "csrf": body["csrf_token"]}


async def measure(sessions: list[dict]) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        async def read(session: dict, project: str = "devcore") -> tuple[int, float]:
            url = TASK_URL if project == "devcore" else BASE + f"/api/dashboard/tasks?project={project}&limit=1&offset=0"
            start = time.perf_counter()
            response = await client.get(url, headers={**ORIGIN,
                "Cookie": "devcore_session=" + session["cookie"]})
            return response.status_code, (time.perf_counter() - start) * 1000

        denied, _ = await read(next(s for s in sessions if s["user"] == "mohd"), "scripts")
        if denied != 403:
            raise RuntimeError(f"mohd cross-project read returned HTTP {denied}, expected 403")
        warm = await asyncio.gather(*(read(session) for session in sessions))
        if any(status != 200 for status, _ in warm):
            raise RuntimeError("Warm-up task read failed")
        elapsed: list[float] = []
        for _ in range(10):
            batch = await asyncio.gather(*(read(session) for session in sessions))
            if any(status != 200 for status, _ in batch):
                raise RuntimeError("Task read failed under 20-session load")
            elapsed.extend(duration for _, duration in batch)
        elapsed.sort()
        return {"reads": len(elapsed), "median_ms": round(statistics.median(elapsed), 2),
                "p95_ms": round(elapsed[189], 2), "max_ms": round(elapsed[-1], 2),
                "cross_project_http": denied}


def logout(session: dict) -> bool:
    headers = {**ORIGIN, "Cookie": "devcore_session=" + session["cookie"],
               "X-CSRF-Token": session["csrf"]}
    response = httpx.request("DELETE", BASE + "/api/auth/session", headers=headers, timeout=15)
    after = httpx.get(BASE + "/api/auth/session", headers={**ORIGIN,
        "Cookie": "devcore_session=" + session["cookie"]}, timeout=15)
    return response.status_code == 200 and after.status_code == 401


def main() -> int:
    ensure_v252()
    sessions: list[dict] = []
    metrics = None
    try:
        for user in ("majdi", "mohd"):
            password = getpass.getpass(f"Password for {user}: ")
            try:
                for _ in range(10):
                    sessions.append(login(user, password))
            finally:
                del password
        metrics = asyncio.run(measure(sessions))
    finally:
        failed_logouts = []
        for session in sessions:
            try:
                if not logout(session):
                    failed_logouts.append(session["user"])
            except Exception:
                failed_logouts.append(session["user"])
        if failed_logouts:
            raise RuntimeError(f"Session revocation failed for {len(failed_logouts)} sessions")
    assert metrics is not None
    result = {"status": "active_v252_load_verified" if metrics["p95_ms"] < 300 else "active_v252_load_failed",
              "sessions": len(sessions), **metrics, "logouts": "verified"}
    print(json.dumps(result))
    return 0 if result["status"] == "active_v252_load_verified" else 1


if __name__ == "__main__":
    raise SystemExit(main())
