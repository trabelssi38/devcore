"""Real MCP -> HTTP admission, with synthetic stores and protected NTFS credentials."""

import asyncio
from contextlib import AsyncExitStack, contextmanager
import copy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time

import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "Scripts"))
from test_dashboard_individual_access import runtime
from test_dashboard_project_context import context_runtime
from devcore_engine.security.identity import (
    CONTEXT_READ, disable_user, issue_credential, remove_membership, revoke_credential, set_membership,
)
from devcore_engine.security.secret_files import protect_reserved_file
from devcore_engine.services.project_context import encode_context
from services.individual_context import IndividualContextClient


@contextmanager
def live_api(app):
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen(10)
    origin = f"http://127.0.0.1:{sock.getsockname()[1]}"
    server = uvicorn.Server(uvicorn.Config(app, log_level="critical", access_log=False, lifespan="off",
                                         timeout_graceful_shutdown=2, timeout_keep_alive=1))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 5
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert server.started, "Temporary API did not start"
        yield origin
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        sock.close()
        assert not thread.is_alive(), "Temporary API did not stop"


def secret_file(path, token):
    path.touch(exist_ok=False)
    protect_reserved_file(path)
    path.write_text(json.dumps({"token": token}), encoding="utf-8")
    return path


async def session(stack, tmp_path, project, origin, secret, *, task_access="disabled", readonly="0", delete_enabled=False, audit_enabled=False, transitions_enabled=False):
    client_root = tmp_path / ("client-" + project)
    local, shared = client_root / "local", client_root / "shared"
    local.mkdir(parents=True)
    shared.mkdir()
    # A deliberately invalid file proves individual clients don't inspect a business database.
    (local / "devcore.db").write_bytes(b"NO CLIENT DATABASE ACCESS")
    script = Path(__file__).with_name("server.py")
    params = StdioServerParameters(command=sys.executable, args=[str(script)], cwd=str(script.parent), env={
        **os.environ, "DEVCORE_LOCAL_ROOT": str(local), "DEVCORE_DATA_ROOT": str(shared),
        "DEVCORE_MCP_AUTH_PROFILE": "individual", "DEVCORE_MCP_API_URL": origin,
        "DEVCORE_MCP_PROJECT": project, "DEVCORE_MCP_CREDENTIAL_FILE": str(secret),
        "DEVCORE_CONTEXT_MAX_BYTES": "12000", "DEVCORE_MCP_READ_ONLY": readonly,
        "DEVCORE_MCP_TASK_ACCESS": task_access,
        "DEVCORE_MCP_TASK_DELETE": "1" if delete_enabled else "0",
        "DEVCORE_MCP_TASK_TRANSITIONS": "1" if transitions_enabled else "0",
        "DEVCORE_MCP_TASK_AUDIT": "1" if audit_enabled else "0",
        "DEVCORE_CONTEXT_ROOT": str(tmp_path / "FORBIDDEN-LOCAL-CONTEXT"),
    })
    read, write = await stack.enter_async_context(stdio_client(params))
    client = await stack.enter_async_context(ClientSession(read, write))
    await client.initialize()
    return client


@pytest.mark.skipif(os.name != "nt", reason="Individual MCP credential protection qualified on Windows NTFS")
def test_real_stdio_http_project_isolation_rotation_revocation_and_no_local_access(context_runtime, tmp_path):
    module, _, existing, identity, local, repositories, tokens = context_runtime
    business_before = (local / "devcore.db").read_bytes()
    contexts_before = {p: p.read_bytes() for root in repositories.values() for p in root.rglob("*") if p.is_file()}
    alice = secret_file(tmp_path / "alice.json", tokens["alice"][1])
    bob = secret_file(tmp_path / "bob.json", tokens["bob"][1])

    async def exercise(origin):
        async with AsyncExitStack() as stack:
            alpha = await session(stack, tmp_path, "alpha", origin, alice)
            beta = await session(stack, tmp_path, "beta", origin, bob)
            assert [tool.name for tool in (await alpha.list_tools()).tools] == ["devcore_project_context"]
            for client, project in ((alpha, "alpha"), (beta, "beta")):
                result = await client.call_tool("devcore_project_context", {"project": project, "query": "worker"})
                assert not result.isError and result.structuredContent is None and len(result.content) == 1
                body = result.content[0].text
                context = json.loads(body)
                assert context["project"] == project
                assert context["measurement"]["used"] == len(body.encode("utf-8")) <= 12000
                assert [d["id"] for d in context["decisions"]] == ["local", "worker"]
                assert context["excluded_superseded"] == ["old"]
                assert context["measurement"]["model_tokens_measured"] is False
            for name, arguments, code in (
                ("devcore_task_status", {"project": "alpha"}, "individual_tool_unavailable"),
                ("devcore_task_done", {"project": "alpha"}, "individual_tool_unavailable"),
                ("devcore_project_context", {"project": "beta"}, "invalid_arguments"),
                ("devcore_project_context", {}, "invalid_arguments"),
                ("devcore_project_context", {"project": "alpha", "directory": str(repositories["beta"])}, "invalid_arguments"),
                ("devcore_project_context", {"project": "alpha", "budget_bytes": 12001}, "invalid_arguments"),
                ("devcore_project_context", {"project": "alpha", "budget_bytes": 256}, "context_budget_exceeded"),
            ):
                result = await alpha.call_tool(name, arguments)
                assert result.isError and json.loads(result.content[0].text)["code"] == code
                assert "privées" not in result.content[0].text
            # Rotation to a valid foreign credential is denied by the API, not only project binding.
            for credential, code in ((tokens["bob"][1], "project_access_denied"),
                                     (existing["alice"][1], "project_access_denied")):
                alice.write_text(json.dumps({"token": credential}), encoding="utf-8")
                result = await alpha.call_tool("devcore_project_context", {"project": "alpha"})
                assert result.isError and json.loads(result.content[0].text)["code"] == code
            alice.write_text(json.dumps({"token": tokens["alice"][1]}), encoding="utf-8")
            revoke_credential(identity, tokens["alice"][0])
            refused = await alpha.call_tool("devcore_project_context", {"project": "alpha"})
            assert refused.isError and json.loads(refused.content[0].text)["http_status"] == 401
            replacement = issue_credential(identity, "alice", ["alpha"], [CONTEXT_READ])
            alice.write_text(json.dumps({"token": replacement[1]}), encoding="utf-8")
            assert not (await alpha.call_tool("devcore_project_context", {"project": "alpha"})).isError
            remove_membership(identity, "alice", "alpha")
            denied = await alpha.call_tool("devcore_project_context", {"project": "alpha"})
            assert denied.isError and json.loads(denied.content[0].text)["http_status"] == 403
            set_membership(identity, "alice", "alpha", "reader")
            disable_user(identity, "alice")
            denied = await alpha.call_tool("devcore_project_context", {"project": "alpha"})
            assert denied.isError and json.loads(denied.content[0].text)["http_status"] == 401
            expired = issue_credential(identity, "bob", ["beta"], [CONTEXT_READ], now=1)
            bob.write_text(json.dumps({"token": expired[1]}), encoding="utf-8")
            denied = await beta.call_tool("devcore_project_context", {"project": "beta"})
            assert denied.isError and json.loads(denied.content[0].text)["http_status"] == 401
            bob.write_text(json.dumps({"token": tokens["bob"][1]}), encoding="utf-8")
            assert not (await beta.call_tool("devcore_project_context", {"project": "beta"})).isError

    with live_api(module.app) as origin:
        asyncio.run(exercise(origin))
    assert (local / "devcore.db").read_bytes() == business_before
    assert all(p.read_bytes() == data for p, data in contexts_before.items())
    for project in ("alpha", "beta"):
        root = tmp_path / ("client-" + project)
        assert [p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()] == ["local/devcore.db"]
        assert (root / "local/devcore.db").read_bytes() == b"NO CLIENT DATABASE ACCESS"


@pytest.mark.skipif(os.name != "nt", reason="Individual MCP NTFS qualification")
def test_slow_context_does_not_block_mcp_control_or_other_project(context_runtime, tmp_path, monkeypatch):
    from devcore_engine.services import registered_project_context as adapter
    module, _, _, _, _, _, tokens = context_runtime
    entered, release = threading.Event(), threading.Event()
    original = adapter.load_registered_project_context
    def delayed(db, principal, **kwargs):
        if principal.project_id == "alpha":
            entered.set()
            assert release.wait(10), "Slow fixture was not released"
        return original(db, principal, **kwargs)
    monkeypatch.setattr(adapter, "load_registered_project_context", delayed)
    alice = secret_file(tmp_path / "alice.json", tokens["alice"][1])
    bob = secret_file(tmp_path / "bob.json", tokens["bob"][1])
    async def exercise(origin):
        async with AsyncExitStack() as stack:
            alpha = await session(stack, tmp_path, "alpha", origin, alice)
            beta = await session(stack, tmp_path, "beta", origin, bob)
            pending = asyncio.create_task(alpha.call_tool("devcore_project_context", {"project": "alpha"}))
            try:
                assert await asyncio.to_thread(entered.wait, 5)
                tools = await asyncio.wait_for(alpha.list_tools(), timeout=1)
                assert len(tools.tools) == 1
                result = await asyncio.wait_for(beta.call_tool("devcore_project_context", {"project": "beta"}), timeout=3)
                assert not result.isError and not pending.done()
            finally:
                release.set()
                assert not (await pending).isError
    with live_api(module.app) as origin:
        asyncio.run(exercise(origin))


@contextmanager
def fake_http(callback):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            callback(self)
        def do_POST(self):
            callback(self)
        def do_DELETE(self):
            callback(self)
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def send(handler, body, status=200, **headers):
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    for name, value in headers.items():
        handler.send_header(name, value)
    handler.end_headers()
    handler.wfile.write(body)


@pytest.mark.parametrize("origin", ["http://example.com", "http://127.0.0.2", "http://user:pass@localhost",
    "https://example.com/api", "http://localhost?x=1", "http://localhost#fragment", "file:///private", "http://localhost:bad"])
def test_invalid_origin_refused_before_credentials(tmp_path, origin):
    with pytest.raises(ValueError):
        IndividualContextClient(origin, tmp_path / "unused.json", "alpha")


def test_arguments_are_refused_before_secret_read_or_http(tmp_path, monkeypatch):
    client = IndividualContextClient("http://127.0.0.1:1", tmp_path / "unused.json", "alpha")
    def forbidden():
        raise AssertionError("Invalid request read a credential")
    monkeypatch.setattr(client, "_authorization", forbidden)
    for args in ({}, {"project": "beta"}, {"project": "alpha", "token": "not-accepted"},
                 {"project": "alpha", "budget_bytes": True}, {"project": "alpha", "query": None},
                 {"project": "alpha", "query": "x" * 4097}, {"project": "alpha", "budget_bytes": 12001}):
        assert client.call("devcore_project_context", args)["code"] == "invalid_arguments"
    assert client.call("devcore_check", {})["code"] == "individual_tool_unavailable"


@pytest.mark.parametrize("setting,value", [("DEVCORE_MCP_AUTH_PROFILE", "unknown"),
    ("DEVCORE_MCP_API_URL", "http://example.com"), ("DEVCORE_MCP_CREDENTIAL_FILE", "relative.json"),
    ("DEVCORE_MCP_PROJECT", ""), ("DEVCORE_CONTEXT_MAX_BYTES", "65537"),
    ("DEVCORE_MCP_API_TIMEOUT_SECONDS", "31"), ("DEVCORE_MCP_TASK_ACCESS", "unknown")])
def test_invalid_startup_configuration_has_no_legacy_fallback(tmp_path, setting, value):
    local, shared = tmp_path / "local", tmp_path / "shared"
    local.mkdir()
    shared.mkdir()
    env = {**os.environ, "DEVCORE_LOCAL_ROOT": str(local), "DEVCORE_DATA_ROOT": str(shared),
        "DEVCORE_MCP_AUTH_PROFILE": "individual", "DEVCORE_MCP_API_URL": "http://127.0.0.1:1",
        "DEVCORE_MCP_CREDENTIAL_FILE": str(tmp_path / "unused.json"), "DEVCORE_MCP_PROJECT": "alpha",
        "DEVCORE_CONTEXT_MAX_BYTES": "12000", "DEVCORE_MCP_API_TIMEOUT_SECONDS": "10"}
    env[setting] = value
    result = subprocess.run([sys.executable, str(Path(__file__).with_name("server.py"))],
                            env=env, capture_output=True, timeout=10)
    assert result.returncode != 0 and result.stdout == b""
    assert not list(local.iterdir()) and not list(shared.iterdir())


def test_redirect_is_never_followed_and_remote_errors_not_exposed(tmp_path, monkeypatch):
    calls = []
    def receive(handler):
        calls.append(handler.path)
        send(handler, b'{"detail":"REMOTE SECRET ERROR"}', status=307, Location="/stolen")
    with fake_http(receive) as origin:
        client = IndividualContextClient(origin, tmp_path / "unused.json", "alpha")
        monkeypatch.setattr(client, "_authorization", lambda: "Bearer synthetic-test-only")
        result = client.call("devcore_project_context", {"project": "alpha"})
    assert result["http_status"] == 307 and "REMOTE SECRET" not in json.dumps(result)
    assert len(calls) == 1 and calls[0].startswith("/api/project/context?")


def test_socket_timeout_has_no_local_context_fallback(tmp_path, monkeypatch):
    release, entered = threading.Event(), threading.Event()
    def receive(handler):
        entered.set()
        release.wait(3)
    with fake_http(receive) as origin:
        client = IndividualContextClient(origin, tmp_path / "unused.json", "alpha", timeout=1)
        monkeypatch.setattr(client, "_authorization", lambda: "Bearer synthetic-test-only")
        try:
            result = client.call("devcore_project_context", {"project": "alpha"})
            assert entered.is_set() and result["code"] == "context_api_unavailable"
            assert "card" not in result
        finally:
            release.set()


@pytest.mark.parametrize("damage", ["foreign", "measurement", "superseded", "proposal_required", "oversize", "invalid", "compressed", "provenance", "duplicate", "omitted", "truncated"])
def test_invalid_or_oversize_api_response_has_no_partial_context(context_runtime, tmp_path, monkeypatch, damage):
    _, api, _, _, _, _, tokens = context_runtime
    baseline = api.get("/api/project/context?project=alpha&budget_bytes=12000", headers={"Authorization": "Bearer " + tokens["alice"][1]}).json()
    result = copy.deepcopy(baseline)
    if damage == "foreign": result["project"] = "beta"
    if damage == "measurement": result["measurement"]["used"] = 1
    if damage == "superseded": result["decisions"][0]["status"] = "superseded"
    if damage == "proposal_required": result["decisions"][0]["status"] = "proposed"
    if damage == "oversize": result["card"] = "PRIVATE OVERSIZE " * 1000
    if damage == "provenance": result["provenance"]["source_contents_verified"] = True
    if damage == "duplicate": result["decisions"].append(result["decisions"][0].copy())
    if damage == "omitted": result["omitted"][0]["id"] = "local"
    if damage != "measurement":
        for _ in range(8): result["measurement"]["used"] = len((encode_context(result) + "\n").encode("utf-8"))
    body = (encode_context(result) + "\n").encode("utf-8") if damage != "invalid" else b"PRIVATE NOT JSON"
    def receive(handler):
        if damage == "truncated":
            handler.send_response(200)
            handler.send_header("Content-Type", "application/json")
            handler.send_header("Content-Length", str(len(body) + 100))
            handler.end_headers()
            handler.wfile.write(body[:50])
        else:
            send(handler, body, **({"Content-Encoding": "gzip"} if damage == "compressed" else {}))
    with fake_http(receive) as origin:
        client = IndividualContextClient(origin, tmp_path / "unused.json", "alpha")
        monkeypatch.setattr(client, "_authorization", lambda: "Bearer synthetic-test-only")
        rejected = client.call("devcore_project_context", {"project": "alpha"})
    assert rejected["code"] == "context_api_unavailable" and "card" not in rejected


@pytest.mark.skipif(os.name != "nt", reason="Native NTFS credential checks")
@pytest.mark.parametrize("damage", ["missing", "public", "invalid", "large", "header_injection"])
def test_credential_failure_prevents_network_and_hides_secret_path(tmp_path, monkeypatch, damage):
    path = tmp_path / "credential-private-name.json"
    if damage != "missing":
        if damage == "public":
            path.write_text('{"token":"' + "a" * 43 + '"}')
        else:
            secret_file(path, "a" * 43)
            if damage == "invalid": path.write_text("NOT JSON SECRET")
            if damage == "large": path.write_text("X" * 4097)
            if damage == "header_injection": path.write_text(json.dumps({"token": "a" * 43 + "\r\nX-Injection: true"}))
    client = IndividualContextClient("http://127.0.0.1:1", path, "alpha")
    def forbidden(*args, **kwargs):
        raise AssertionError("Invalid credential opened the network")
    monkeypatch.setattr("devcore_engine.clients.individual_context.build_opener", forbidden)
    result = client.call("devcore_project_context", {"project": "alpha"})
    assert result["code"] == "individual_credential_unavailable"
    assert str(path) not in json.dumps(result) and "token" not in result
