"""Serve a frozen legacy Cockpit snapshot from an isolated qualification copy.

This server deliberately has no write routes, token injection, SSE, or generator.
It must never be pointed at the active platform or data roots.
"""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def serve(snapshot: Path, port: int) -> None:
    snapshot = snapshot.resolve(strict=True)
    if not snapshot.is_dir() or not 1 <= port <= 65535:
        raise ValueError("Existing snapshot directory and valid port required")
    files = {
        "/": (snapshot / "index.html", "text/html; charset=utf-8"),
        "/index.html": (snapshot / "index.html", "text/html; charset=utf-8"),
        "/index_terminal.html": (snapshot / "index_terminal.html", "text/html; charset=utf-8"),
        "/api/dashboard": (snapshot / "dashboard_payload.json", "application/json; charset=utf-8"),
    }
    for path, _ in files.values():
        if not path.is_file() or not path.resolve().is_relative_to(snapshot):
            raise ValueError(f"Missing or unsafe snapshot artifact: {path}")
    payload = json.loads(files["/api/dashboard"][0].read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("Unsupported dashboard snapshot schema")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            route = self.path.split("?", 1)[0]
            if route == "/api/status":
                body = b'{"status":"snapshot","read_only":true}'
                content_type = "application/json; charset=utf-8"
            elif route in files:
                path, content_type = files[route]
                body = path.read_bytes()
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; connect-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:
            self.send_error(405, "Read-only snapshot")

        def do_DELETE(self) -> None:
            self.send_error(405, "Read-only snapshot")

    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    serve(args.snapshot, args.port)


if __name__ == "__main__":
    main()
