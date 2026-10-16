"""Verify the DevCore TLS pilot from a second Windows host.

Copy this script and the public cert.pem to that host. Passwords are prompted
locally and never printed or passed in command-line arguments.
"""
from __future__ import annotations

import argparse
from getpass import getpass
import http.cookiejar
import json
from pathlib import Path
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request


INTERNAL_PORTS = (5432, 7337, 8787, 8789, 20130, 20131)


def client(certificate: Path):
    context = ssl.create_default_context(cafile=str(certificate))
    cookies = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPSHandler(context=context),
                                       urllib.request.HTTPCookieProcessor(cookies))


def request(opener, origin: str, path: str, *, method="GET", body=None, csrf=None):
    headers = {"Accept": "application/json"}
    if method != "GET":
        headers["Origin"] = origin
    if csrf:
        headers["X-CSRF-Token"] = csrf
    payload = None if body is None else json.dumps(body).encode("utf-8")
    if payload is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(origin + path, data=payload, headers=headers, method=method)
    try:
        with opener.open(req, timeout=10) as response:
            content = response.read(65537)
            parsed = (json.loads(content) if content and len(content) <= 65536
                      and response.headers.get_content_type() == "application/json" else None)
            return response.status, parsed
    except urllib.error.HTTPError as exc:
        exc.close()
        return exc.code, None


def port_closed(address: str, port: int) -> bool:
    try:
        with socket.create_connection((address, port), timeout=2):
            return False
    except OSError:
        return True


def run(origin: str, certificate: Path) -> dict:
    parsed = urllib.parse.urlsplit(origin)
    if parsed.scheme != "https" or parsed.hostname != "172.16.210.32" or parsed.port != 20129 or parsed.path or parsed.query or parsed.fragment:
        raise ValueError("Expected the exact DevCore pilot HTTPS origin")
    if certificate.is_symlink() or not certificate.is_file():
        raise ValueError("Public certificate file is missing")
    anonymous = client(certificate)
    if request(anonymous, origin, "/project")[0] != 200 or request(anonymous, origin, "/api/auth/session")[0] != 401:
        raise RuntimeError("TLS shell or anonymous session check failed")

    results = {"tls_verified": True, "anonymous_http": 401}
    for user in ("majdi", "mohd"):
        password = getpass(f"DevCore password for {user}: ")
        opener = client(certificate)
        try:
            status, session = request(opener, origin, "/api/auth/session", method="POST",
                                      body={"user_id": user, "password": password, "project": "devcore"})
        finally:
            password = None
        if status != 200 or not isinstance(session, dict) or session.get("user_id") != user:
            raise RuntimeError(f"{user} login failed: HTTP {status}")
        if request(opener, origin, "/api/dashboard/tasks?project=devcore&limit=1")[0] != 200:
            raise RuntimeError(f"{user} DevCore read failed")
        cross_status = request(opener, origin, "/api/dashboard/tasks?project=scripts&limit=1")[0]
        if cross_status != 403:
            raise RuntimeError(f"{user} project-scoped session crossed projects")
        logout, _ = request(opener, origin, "/api/auth/session", method="DELETE",
                            csrf=session.get("csrf_token"))
        if logout != 200 or request(opener, origin, "/api/auth/session")[0] != 401:
            raise RuntimeError(f"{user} logout failed")
        results[user] = {"login": 200, "devcore_read": 200, "scripts_from_devcore_session": 403,
                         "logout": 200, "revoked": 401}

    denied = [port for port in INTERNAL_PORTS if port_closed(parsed.hostname, port)]
    if len(denied) != len(INTERNAL_PORTS):
        raise RuntimeError(f"Internal ports unexpectedly reachable: {sorted(set(INTERNAL_PORTS) - set(denied))}")
    results["internal_ports_unreachable"] = denied
    results["status"] = "v253_second_host_verified"
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", default="https://172.16.210.32:20129")
    parser.add_argument("--certificate", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.origin, args.certificate), separators=(",", ":")))


if __name__ == "__main__":
    main()
