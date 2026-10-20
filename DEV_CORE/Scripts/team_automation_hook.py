"""Candidate team hook client. Installation belongs to the controlled cutover phase."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def local_api_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Hook API must use loopback")
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
        raise ValueError("Hook API URL must be a bare local origin")
    return value.rstrip("/")


def read_token(path: str) -> str:
    file = Path(path)
    if not file.is_absolute() or not file.is_file() or file.stat().st_size > 4096:
        raise ValueError("Existing absolute token file required")
    token = file.read_text(encoding="utf-8").strip()
    if not token or len(token) > 4096 or any(char.isspace() for char in token):
        raise ValueError("Invalid token file")
    return token


def request_json(opener, url: str, token: str, *, payload: dict | None = None) -> dict:
    body = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = Request(url, data=body, method="GET" if body is None else "POST",
                      headers={"Authorization": f"Bearer {token}", "Accept": "application/json",
                               "Content-Type": "application/json"})
    with opener.open(request, timeout=10) as response:
        if response.status != 200:
            raise ValueError("Hook API returned a non-success status")
        raw = response.read(65537)
        if len(raw) > 65536:
            raise ValueError("Hook API response exceeds bound")
        return json.loads(raw)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Publish one authenticated team hook event")
    parser.add_argument("--api-url", default="http://127.0.0.1:20131")
    parser.add_argument("--token-file", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--hook", choices=("session_start", "session_end", "git_commit", "tool_use"), required=True)
    parser.add_argument("--source", choices=("codex", "claude", "gemini", "git"), required=True)
    parser.add_argument("--session")
    parser.add_argument("--commit")
    parser.add_argument("--tool")
    parser.add_argument("--reported-outcome", choices=("succeeded", "failed"))
    parser.add_argument("--occurrence")
    args = parser.parse_args(argv)
    try:
        origin = local_api_url(args.api_url)
        token = read_token(args.token_file)
        opener = build_opener(NoRedirect)
        context = None
        if args.hook == "session_start":
            context = request_json(opener, origin + "/api/v1/project/context?" +
                                   urlencode({"project": args.project, "budget_bytes": 12000}), token)
        payload = {"project": args.project, "hook": args.hook, "source": args.source,
                   "session": args.session, "commit": args.commit, "tool": args.tool,
                   "reported_outcome": args.reported_outcome, "occurrence": args.occurrence}
        result = request_json(opener, origin + "/api/v1/automation/hooks", token, payload=payload)
        if context is not None:
            result["project_context"] = context
        print(json.dumps(result, ensure_ascii=False, default=str))
        return 0
    except (HTTPError, URLError, OSError, ValueError, json.JSONDecodeError) as exc:
        # Never print the bearer token, request body or a server-supplied error body.
        print(f"team hook failed: {type(exc).__name__}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
