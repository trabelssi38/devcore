"""CLI subprocesses share API admission and outcomes with the individual MCP client."""

import asyncio
from contextlib import AsyncExitStack, closing
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import importlib.util

import pytest

from test_individual_context import runtime, context_runtime, live_api, secret_file, session
from devcore_engine.security.identity import CONTEXT_READ, READ, WRITE, AUDIT_READ, issue_credential, revoke_credential, set_membership
from devcore_engine.clients.individual_tasks import IndividualApiClient
from services.individual_tasks import IndividualApiClient as McpApiClient

SCRIPT = Path(__file__).resolve().parents[2] / "Scripts/individual_project_client.py"


def call(tmp_path, origin, secret, project, *args, isolated=False, timeout=10, entry="source"):
    local, data = tmp_path / "cli-local", tmp_path / "cli-data"
    local.mkdir(exist_ok=True)
    data.mkdir(exist_ok=True)
    (local / "devcore.db").write_bytes(b"NO CLI DATABASE ACCESS")
    # -I -S ensures this client doesn't depend on the MCP/FastAPI distributions.
    prefixes = {
        "source": [sys.executable] + (["-I", "-S"] if isolated else []) + [str(SCRIPT)],
        "engine": [sys.executable, "-m", "devcore_engine.cli", "individual"],
        "package": [sys.executable, "-m", "devcore_engine", "individual"],
        "legacy": [sys.executable, "-I", "-S", str(SCRIPT.parent / "dc.py"), "individual"],
        "powershell": ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT.parent / "dc.ps1"), "individual"],
    }
    prefix = prefixes[entry] if isinstance(entry, str) else [str(entry), "individual"]
    command = prefix + [
        "--api-url", origin, "--credential-file", str(secret), "--project", project,
        "--timeout-seconds", str(timeout), *args]
    result = subprocess.run(command, env={**os.environ, "DEVCORE_LOCAL_ROOT": str(local), "DEVCORE_DATA_ROOT": str(data),
        "DEVCORE_CONTEXT_ROOT": str(tmp_path / "FORBIDDEN-LOCAL-FALLBACK"),
        "DEVCORE_PYTHON": sys.executable,
        "PYTHONPATH": str(SCRIPT.parent.parent) if isinstance(entry, str) else ""},
        cwd=tmp_path, capture_output=True, timeout=30)
    assert result.stderr == b"", "CLI exposed diagnostics on stderr"
    assert result.stdout.endswith(b"\n") and result.stdout.count(b"\n") == 1
    value = json.loads(result.stdout)
    assert (local / "devcore.db").read_bytes() == b"NO CLI DATABASE ACCESS"
    assert {p.name for p in local.iterdir()} == {"devcore.db"} and not list(data.iterdir())
    return result, value


def test_mcp_and_cli_use_the_same_client_implementation():
    assert IndividualApiClient is McpApiClient


@pytest.mark.skipif(os.name != "nt", reason="Real NTFS credential qualification")
@pytest.mark.parametrize("entry", ["engine", "package", "legacy", "powershell"])
def test_dc_individual_entrypoints_share_context_admission_and_mutation(context_runtime, tmp_path, entry):
    module, _, _, identity, local, _, _ = context_runtime
    identifier, token = issue_credential(identity, "alice", ["alpha"], [CONTEXT_READ, READ, WRITE])
    private = secret_file(tmp_path / "alice-private.json", token)
    with live_api(module.app) as origin:
        response, context = call(tmp_path, origin, private, "alpha", "context", entry=entry)
        assert response.returncode == 0 and context["measurement"]["used"] == len(response.stdout)
        _, direct = call(tmp_path, origin, private, "alpha", "context")
        assert context == direct
        response, foreign = call(tmp_path, origin, private, "beta", "tasks", entry=entry)
        assert response.returncode == 1 and foreign["http_status"] == 403 and "tasks" not in foreign
        response, page = call(tmp_path, origin, private, "alpha", "tasks", entry=entry)
        assert response.returncode == 0 and page["tasks"][0]["version"] == 1
        response, receipt = call(tmp_path, origin, private, "alpha", "done", "--task-id", "T-01", "--expected-version", "1", entry=entry)
        assert response.returncode == 0 and receipt["acknowledged"] and receipt["refresh_required"]
        response, stale = call(tmp_path, origin, private, "alpha", "done", "--task-id", "T-01", "--expected-version", "1", entry=entry)
        assert response.returncode == 1 and stale["code"] == "stale_task_version"
        revoke_credential(identity, identifier)
        response, revoked = call(tmp_path, origin, private, "alpha", "tasks", entry=entry)
        assert response.returncode == 1 and revoked["http_status"] == 401
    with closing(sqlite3.connect(local / "devcore.db")) as conn:
        assert conn.execute("SELECT status,version FROM tasks WHERE project_id='beta'").fetchone() == ("in_progress", 1)
        assert conn.execute("SELECT actor FROM audit_log").fetchall() == [("alice",)]


@pytest.mark.parametrize("entry", ["engine", "package", "legacy"])
def test_individual_dispatch_does_not_import_local_stores_even_without_site_packages(tmp_path, entry):
    # A broken local adapter must not prevent a separately authorized API client.
    local, data = tmp_path / "local", tmp_path / "data"
    local.mkdir()
    data.mkdir()
    bootstrap = """
import importlib.abc, runpy, sys
class RejectLocalAdapters(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname in {'devcore_engine.db', 'devcore_engine.migrate_to_unified_db',
                        'devcore_engine.services.tasks', 'devcore_engine.services.memory',
                        'devcore_engine.services.memory_hierarchy', 'devcore_engine.services.events',
                        'devcore.paths', 'mcp', 'fastapi', 'sqlite_vec'}:
            raise RuntimeError('Forbidden local adapter import: ' + fullname)
sys.meta_path.insert(0, RejectLocalAdapters())
sys.path.insert(0, sys.argv.pop(1))
entry = sys.argv.pop(1)
sys.argv = [entry, 'individual', '--token', 'synthetic-secret-not-accepted']
if entry.endswith('.py'):
    runpy.run_path(entry, run_name='__main__')
else:
    runpy.run_module(entry, run_name='__main__')
"""
    target = str(SCRIPT.parent / "dc.py") if entry == "legacy" else "devcore_engine.cli" if entry == "engine" else "devcore_engine"
    result = subprocess.run([sys.executable, "-I", "-S", "-c", bootstrap, str(SCRIPT.parent.parent), target],
        cwd=tmp_path, env={**os.environ, "DEVCORE_LOCAL_ROOT": str(local), "DEVCORE_DATA_ROOT": str(data)},
        capture_output=True, timeout=10)
    assert result.returncode == 2 and result.stderr == b""
    assert json.loads(result.stdout)["code"] == "invalid_arguments"
    assert b"synthetic-secret" not in result.stdout and not list(local.iterdir()) and not list(data.iterdir())


@pytest.mark.skipif(os.name != "nt", reason="PowerShell entry point")
def test_powershell_individual_dispatch_skips_platform_discovery(tmp_path):
    scripts = tmp_path / "Scripts"
    scripts.mkdir()
    shutil.copyfile(SCRIPT.parent / "dc.ps1", scripts / "dc.ps1")
    (scripts / "platform_version.ps1").write_text("throw 'Forbidden Dropbox/platform discovery'", encoding="utf-8")
    (scripts / "individual_project_client.py").write_text(
        "import json,sys\nprint(json.dumps({'args':sys.argv[1:]}))\nsys.exit(2)\n", encoding="utf-8")
    local, data = tmp_path / "local", tmp_path / "data"
    local.mkdir()
    data.mkdir()
    result = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(scripts / "dc.ps1"),
        "individual", "--project", "projet avec espace", "tasks"], cwd=tmp_path,
        env={**os.environ, "DEVCORE_PYTHON": sys.executable, "DEVCORE_LOCAL_ROOT": str(local), "DEVCORE_DATA_ROOT": str(data)},
        capture_output=True, timeout=15)
    assert result.returncode == 2 and result.stderr == b""
    assert json.loads(result.stdout)["args"] == ["--project", "projet avec espace", "tasks"]
    assert not list(local.iterdir()) and not list(data.iterdir())


@pytest.mark.skipif(
    os.name != "nt" or (importlib.util.find_spec("setuptools") is None and not os.environ.get("DEVCORE_TEST_BUILD_TOOLS")),
    reason="Wheel console and real NTFS credential qualification require build tooling",
)
def test_installed_wheel_dc_individual_needs_no_server_dependencies(context_runtime, tmp_path):
    # Build from a minimal source copy; never write build metadata in this checkout.
    build = tmp_path / "build"
    build.mkdir()
    platform = SCRIPT.parent.parent
    for name in ("pyproject.toml", "README.md"):
        shutil.copyfile(platform / name, build / name)
    shutil.copytree(platform / "devcore_engine", build / "devcore_engine",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "tests"))
    wheels, environment = tmp_path / "wheels", tmp_path / "installed"
    local, data = tmp_path / "build-local", tmp_path / "build-data"
    local.mkdir()
    data.mkdir()
    isolated_env = {**os.environ, "DEVCORE_LOCAL_ROOT": str(local), "DEVCORE_DATA_ROOT": str(data),
                    "PYTHONPATH": os.environ.get("DEVCORE_TEST_BUILD_TOOLS", "")}
    def run(command):
        result = subprocess.run(command, env=isolated_env, cwd=tmp_path, capture_output=True, timeout=90)
        assert result.returncode == 0, result.stderr.decode(errors="replace")
    # Build tooling is provided separately; the runtime itself may contain no pip.
    result = subprocess.run([sys.executable, "-c",
        "import sys; from setuptools.build_meta import build_wheel; build_wheel(sys.argv[1])", str(wheels)],
        env=isolated_env, cwd=build, capture_output=True, timeout=90)
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    run([sys.executable, "-m", "venv", "--without-pip", str(environment)])
    installed_python = environment / "Scripts/python.exe"
    run([str(installed_python), "-I", "-m", "ensurepip"])
    wheel, = wheels.glob("*.whl")
    run([str(installed_python), "-I", "-m", "pip", "install", "--no-index", "--no-deps",
         "--no-compile", "--disable-pip-version-check", str(wheel)])
    run([str(installed_python), "-I", "-c", "import importlib.util; assert all(importlib.util.find_spec(n) is None for n in ['mcp','fastapi','sqlite_vec','argon2'])"])
    assert not list(local.iterdir()) and not list(data.iterdir())
    module, _, _, identity, server_local, _, _ = context_runtime
    _, token = issue_credential(identity, "alice", ["alpha"], [CONTEXT_READ, READ, WRITE])
    private = secret_file(tmp_path / "alice.json", token)
    console = environment / "Scripts/dc.exe"
    with live_api(module.app) as origin:
        response, context = call(tmp_path, origin, private, "alpha", "context", entry=console)
        assert response.returncode == 0 and context["measurement"]["used"] == len(response.stdout)
        response, page = call(tmp_path, origin, private, "alpha", "tasks", entry=console)
        assert response.returncode == 0 and page["tasks"][0]["version"] == 1
        response, receipt = call(tmp_path, origin, private, "alpha", "done", "--task-id", "T-01", "--expected-version", "1", entry=console)
        assert response.returncode == 0 and receipt["acknowledged"]
        set_membership(identity, "alice", "alpha", "owner")
        _, audit_token = issue_credential(identity, "alice", ["alpha"], [AUDIT_READ])
        private.write_text(json.dumps({"token": audit_token}), encoding="utf-8")
        response, audit = call(tmp_path, origin, private, "alpha", "audit", "--task-id", "T-01", entry=console)
        assert response.returncode == 0 and audit["events"][0]["actor"] == "alice"
        assert audit["events"][0]["after"] == {"status": "done", "version": 2}
    with closing(sqlite3.connect(server_local / "devcore.db")) as conn:
        assert conn.execute("SELECT actor FROM audit_log").fetchall() == [("alice",)]


@pytest.mark.skipif(os.name != "nt", reason="Real NTFS credential qualification")
def test_cli_context_exact_measurement_tasks_completion_and_revocation(context_runtime, tmp_path):
    module, _, _, identity, local, _, _ = context_runtime
    identifier, token = issue_credential(identity, "alice", ["alpha"], [CONTEXT_READ, READ, WRITE])
    private = secret_file(tmp_path / "alice-private.json", token)
    with live_api(module.app) as origin:
        response, value = call(tmp_path, origin, private, "alpha", "context", "--query", "worker", isolated=True)
        assert response.returncode == 0 and value["project"] == "alpha"
        assert value["measurement"]["used"] == len(response.stdout) <= 12000
        assert [d["id"] for d in value["decisions"]] == ["local", "worker"]
        assert value["excluded_superseded"] == ["old"] and value["measurement"]["model_tokens_measured"] is False
        response, value = call(tmp_path, origin, private, "alpha", "context", "--budget-bytes", "256")
        assert response.returncode == 1 and value["code"] == "context_budget_exceeded" and "card" not in value
        response, value = call(tmp_path, origin, private, "beta", "tasks")
        assert response.returncode == 1 and value["http_status"] == 403 and "tasks" not in value
        response, page = call(tmp_path, origin, private, "alpha", "tasks", "--limit", "1")
        assert response.returncode == 0 and page["tasks"][0]["version"] == 1
        assert page["tasks"][0]["project"] == "alpha" and page["page_may_have_more"]
        response, receipt = call(tmp_path, origin, private, "alpha", "done", "--task-id", "T-01", "--expected-version", "1")
        assert response.returncode == 0 and receipt["acknowledged"] and receipt["refresh_required"]
        assert "version" not in receipt
        response, value = call(tmp_path, origin, private, "alpha", "done", "--task-id", "T-01", "--expected-version", "1")
        assert response.returncode == 1 and value["code"] == "stale_task_version"
        response, page = call(tmp_path, origin, private, "alpha", "tasks", isolated=True)
        assert response.returncode == 0 and page["tasks"][0]["version"] == 2 and page["tasks"][0]["status"] == "done"
        revoke_credential(identity, identifier)
        response, value = call(tmp_path, origin, private, "alpha", "tasks")
        assert response.returncode == 1 and value["http_status"] == 401
    with closing(sqlite3.connect(local / "devcore.db")) as conn:
        assert conn.execute("SELECT status,version FROM tasks WHERE project_id='beta'").fetchone() == ("in_progress", 1)
        actor, details = conn.execute("SELECT actor,details FROM audit_log").fetchone()
        assert actor == "alice" and json.loads(details)["after"]["version"] == 2
        assert token not in details
        assert conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0] == 1


@pytest.mark.skipif(os.name != "nt", reason="Real NTFS credential qualification")
def test_equivalent_cli_and_mcp_task_read_and_conflict(runtime, tmp_path):
    module, _, credentials, _, local = runtime
    private = secret_file(tmp_path / "alice.json", credentials["alice"][1])
    with closing(sqlite3.connect(local / "devcore.db")) as conn, conn:
        conn.execute("UPDATE tasks SET title='Changed elsewhere' WHERE project_id='alpha'")
    async def exercise(origin):
        async with AsyncExitStack() as stack:
            client = await session(stack, tmp_path, "alpha", origin, private, task_access="write")
            result = await client.call_tool("devcore_task_status", {"project": "alpha", "limit": 1})
            _, cli = await asyncio.to_thread(call, tmp_path, origin, private, "alpha", "tasks", "--limit", "1")
            assert cli == json.loads(result.content[0].text)
            result = await client.call_tool("devcore_task_done", {"project": "alpha", "task_id": "T-01", "expected_version": 1})
            response, cli = await asyncio.to_thread(call, tmp_path, origin, private, "alpha", "done", "--task-id", "T-01", "--expected-version", "1")
            assert result.isError and response.returncode == 1 and cli == json.loads(result.content[0].text)
    with live_api(module.app) as origin:
        asyncio.run(exercise(origin))
    with closing(sqlite3.connect(local / "devcore.db")) as conn:
        assert conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0] == 0
        assert conn.execute("SELECT status,version FROM tasks WHERE project_id='alpha'").fetchone() == ("in_progress", 2)


@pytest.mark.parametrize("args", [[], ["--api-url", "http://127.0.0.1:1"],
    ["--token", "synthetic-secret-not-accepted"],
    ["--api-url", "http://127.0.0.1:1", "--credential-file", "unused.json", "--project", "alpha", "done", "--task-id", "T-01"]])
def test_parser_refuses_incomplete_or_secret_arguments_without_echo(tmp_path, args):
    local, data = tmp_path / "local", tmp_path / "data"
    local.mkdir()
    data.mkdir()
    result = subprocess.run([sys.executable, str(SCRIPT), *args], env={**os.environ,
        "DEVCORE_LOCAL_ROOT": str(local), "DEVCORE_DATA_ROOT": str(data)}, capture_output=True, timeout=10)
    assert result.returncode == 2 and result.stderr == b""
    assert json.loads(result.stdout)["code"] == "invalid_arguments"
    assert b"synthetic-secret" not in result.stdout and not list(local.iterdir()) and not list(data.iterdir())


@pytest.mark.parametrize("change,command", [("remote_http", ["tasks"]), ("relative_file", ["tasks"]),
    ("bad_budget", ["context"]), ("negative_offset", ["tasks", "--offset", "-1"]),
    ("invalid_version", ["done", "--task-id", "T-01", "--expected-version", "0"])])
def test_invalid_configuration_or_operation_fails_before_credential_or_api(tmp_path, change, command):
    origin = "http://example.com" if change == "remote_http" else "http://127.0.0.1:1"
    private = "unused.json" if change == "relative_file" else tmp_path / "missing-secret.json"
    args = (["--context-max-bytes", "65537"] if change == "bad_budget" else []) + command
    response, value = call(tmp_path, origin, private, "alpha", *args)
    assert response.returncode == 2 and value["code"] in {"invalid_configuration", "invalid_arguments"}
    assert str(private).encode() not in response.stdout


@pytest.mark.skipif(os.name != "nt", reason="Real NTFS credential qualification")
def test_missing_or_public_credential_is_refused_without_path_exposure(tmp_path):
    private = tmp_path / "private-name.json"
    for exists in (False, True):
        if exists:
            private.write_text(json.dumps({"token": "a" * 43}))
        response, value = call(tmp_path, "http://127.0.0.1:1", private, "alpha", "tasks")
        assert response.returncode == 1 and value["code"] == "individual_credential_unavailable"
        assert str(private).encode() not in response.stdout


@pytest.mark.skipif(os.name != "nt", reason="Real NTFS credential qualification")
def test_cli_lost_response_after_commit_is_uncertain_and_does_not_retry(runtime, tmp_path, monkeypatch):
    module, _, credentials, _, local = runtime
    original = module.complete_task
    def delay_after_commit(*args, **kwargs):
        import time
        result = original(*args, **kwargs)
        time.sleep(2)
        return result
    monkeypatch.setattr(module, "complete_task", delay_after_commit)
    private = secret_file(tmp_path / "alice.json", credentials["alice"][1])
    with live_api(module.app) as origin:
        response, value = call(tmp_path, origin, private, "alpha", "done", "--task-id", "T-01", "--expected-version", "1", timeout=1)
        assert response.returncode == 1 and value["code"] == "mutation_outcome_unknown"
        response, page = call(tmp_path, origin, private, "alpha", "tasks")
        assert response.returncode == 0 and page["tasks"][0]["status"] == "done"
    with closing(sqlite3.connect(local / "devcore.db")) as conn:
        assert conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM bus_events WHERE event_type='TaskCompleted'").fetchone()[0] == 1
