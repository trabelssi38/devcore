"""Exercise the MCP handshake in a real subprocess over stdio."""

import asyncio
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from DEV_CORE.devcore_engine.db import init_db


def test_consultation_profile_is_bound_to_one_project(tmp_path):
    local_root, data_root = tmp_path / "local", tmp_path / "shared"
    local_root.mkdir()
    data_root.mkdir()
    # A minimal pre-existing schema exposes accidental initialization by a reader.
    conn = sqlite3.connect(local_root / "devcore.db")
    conn.executescript("""
        CREATE TABLE projects(id TEXT PRIMARY KEY, name TEXT, root_path TEXT);
        CREATE TABLE tasks(id TEXT, project_id TEXT, title TEXT, status TEXT, mode TEXT,
                           priority INTEGER DEFAULT 0, created_at TEXT DEFAULT '2026-01-01');
    """)
    conn.execute("INSERT INTO projects(id,name,root_path) VALUES ('alpha','alpha','/tmp')")
    conn.execute("INSERT INTO tasks(id,project_id,title,status,mode) VALUES ('T-01','alpha','Retain','in_progress','coding')")
    conn.commit()
    original_schema = conn.execute("SELECT type,name,sql FROM sqlite_master ORDER BY name").fetchall()
    conn.close()
    script = Path(__file__).with_name("server.py")

    async def exercise():
        params = StdioServerParameters(command=sys.executable, args=[str(script)], cwd=str(script.parent),
            env={**os.environ, "DEVCORE_PLATFORM_ROOT": str(script.parents[2]),
                 "DEVCORE_LOCAL_ROOT": str(local_root), "DEVCORE_DATA_ROOT": str(data_root),
                 "DEVCORE_MCP_READ_ONLY": "1", "DEVCORE_MCP_PROJECT": "alpha"})
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as client:
                await client.initialize()
                listed = await client.list_tools()
                assert {tool.name for tool in listed.tools} == {"devcore_task_status", "devcore_check", "devcore_project_context"}
                assert not (await client.call_tool("devcore_task_status", {"project": "alpha"})).isError
                assert not (await client.call_tool("devcore_check", {"project": "alpha"})).isError
                assert (await client.call_tool("devcore_task_status", {"project": "beta"})).isError
                assert (await client.call_tool("devcore_task_status", {})).isError
                assert (await client.call_tool("devcore_task_done", {"project": "alpha"})).isError
    asyncio.run(exercise())
    conn = sqlite3.connect(local_root / "devcore.db")
    assert conn.execute("SELECT status FROM tasks WHERE project_id='alpha'").fetchone()[0] == "in_progress"
    assert conn.execute("SELECT type,name,sql FROM sqlite_master ORDER BY name").fetchall() == original_schema
    conn.close()


def test_stdio_initialize_list_and_call(tmp_path):
    script = Path(__file__).with_name("server.py")
    data_root = tmp_path / "shared"
    local_root = tmp_path / "local"
    board_dir = data_root / "Memory" / "devcore"
    board_dir.mkdir(parents=True)
    local_root.mkdir()
    (board_dir / "tasks.json").write_text(json.dumps({
        "project": "devcore",
        "current_task": "T-01",
        "tasks": [{"id": "T-01", "title": "Protocol", "status": "active"}],
    }), encoding="utf-8")
    conn = init_db(local_root / "devcore.db")
    conn.execute("INSERT INTO projects(id,name,root_path) VALUES ('devcore','devcore','/tmp')")
    conn.execute("""INSERT INTO tasks(id,project_id,title,status,mode)
                    VALUES ('T-01','devcore','Protocol','in_progress','coding')""")
    conn.execute("INSERT INTO projects(id,name,root_path) VALUES ('other','other','/tmp')")
    conn.execute("""INSERT INTO tasks(id,project_id,title,status,mode)
                    VALUES ('T-01','other','Other project','todo','coding')""")
    conn.commit()
    conn.close()

    async def exercise():
        params = StdioServerParameters(
            command=sys.executable,
            args=[str(script)],
            cwd=str(script.parent),
            env={**os.environ,
                 "DEVCORE_PLATFORM_ROOT": str(script.parents[2]),
                 "DEVCORE_DATA_ROOT": str(data_root),
                 "DEVCORE_LOCAL_ROOT": str(local_root)},
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as client:
                initialized = await client.initialize()
                assert initialized.serverInfo.name == "devcore-scripts"
                listed = await client.list_tools()
                assert any(tool.name == "devcore_task_status" for tool in listed.tools)
                result = await client.call_tool("devcore_task_status", {"project": "devcore"})
                assert not result.isError
                assert "T-01" in result.structuredContent["stdout"]
                missing_project = await client.call_tool("devcore_task_status", {})
                assert missing_project.isError
                unknown_project = await client.call_tool("devcore_task_status", {"project": "missing"})
                assert unknown_project.isError
                checked = await client.call_tool("devcore_check", {"project": "devcore"})
                assert not checked.isError
                assert checked.structuredContent["tasks_json"]["tasks"][0]["title"] == "Protocol"
                other = await client.call_tool("devcore_check", {"project": "other"})
                assert other.structuredContent["tasks_json"]["tasks"][0]["title"] == "Other project"
                emitted = await client.call_tool(
                    "devcore_event_emit", {"project": "devcore", "event_type": "ProtocolChecked", "payload": {"ok": True}}
                )
                assert not emitted.isError
                assert emitted.structuredContent["event_id"].startswith("evt_")
                bad_event = await client.call_tool(
                    "devcore_event_emit", {"project": "devcore", "event_type": "../escape", "payload": {}}
                )
                assert bad_event.isError
                no_project_event = await client.call_tool(
                    "devcore_event_emit", {"event_type": "ProtocolChecked", "payload": {}}
                )
                assert no_project_event.isError
                completed = await client.call_tool("devcore_task_done", {"project": "devcore"})
                assert not completed.isError
                updated = await client.call_tool("devcore_task_status", {"project": "devcore"})
                assert "1/1 completed" in updated.structuredContent["stdout"]
                queue = board_dir / "task_prompt_queue.jsonl"
                queue.write_text(json.dumps({"title": "Suggested", "mode": "coding"}) + "\n", encoding="utf-8")
                imported = await client.call_tool("devcore_task_sync", {"project": "devcore"})
                assert not imported.isError
                assert "1 task(s) added" in imported.structuredContent["stdout"]
                assert not queue.exists()
                repeated = await client.call_tool("devcore_task_sync", {"project": "devcore"})
                assert "0 tasks added" in repeated.structuredContent["stdout"]
                queue.write_text("{bad json\n", encoding="utf-8")
                invalid = await client.call_tool("devcore_task_sync", {"project": "devcore"})
                assert invalid.isError
                assert queue.exists()
                queue.write_text(json.dumps({"title": "Recovered"}) + "\n", encoding="utf-8")
                recovered = await client.call_tool("devcore_task_sync", {"project": "devcore"})
                assert not recovered.isError
                assert "1 task(s) added" in recovered.structuredContent["stdout"]
                assert not queue.exists()

    asyncio.run(exercise())
    conn = init_db(local_root / "devcore.db")
    assert conn.execute(
        "SELECT COUNT(*) FROM bus_events WHERE project = 'devcore' AND event_type = 'ProtocolChecked'"
    ).fetchone()[0] == 1
    conn.close()
    assert not list((local_root / "Bus" / "events").glob("*ProtocolChecked*"))
    subprocess.run(
        [sys.executable, "-c", "from services.task_service import apply_rtk; apply_rtk('one\\ntwo')"],
        cwd=script.parent,
        env={**os.environ,
             "DEVCORE_PLATFORM_ROOT": str(script.parents[2]),
             "DEVCORE_DATA_ROOT": str(data_root),
             "DEVCORE_LOCAL_ROOT": str(local_root)},
        check=True,
    )
    assert (local_root / "Metrics" / "kpi.csv").is_file()
    assert not (data_root / "Metrics" / "kpi.csv").exists()


def test_consultation_does_not_create_a_missing_database(tmp_path):
    local_root, data_root = tmp_path / "local", tmp_path / "shared"
    local_root.mkdir()
    data_root.mkdir()
    script = Path(__file__).with_name("server.py")

    async def exercise():
        params = StdioServerParameters(command=sys.executable, args=[str(script)], cwd=str(script.parent),
            env={**os.environ, "DEVCORE_PLATFORM_ROOT": str(script.parents[2]),
                 "DEVCORE_LOCAL_ROOT": str(local_root), "DEVCORE_DATA_ROOT": str(data_root),
                 "DEVCORE_MCP_READ_ONLY": "1", "DEVCORE_MCP_PROJECT": "alpha"})
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as client:
                await client.initialize()
                for name in ("devcore_task_status", "devcore_check"):
                    result = await client.call_tool(name, {"project": "alpha"})
                    assert result.isError
                    assert "does not exist" in result.structuredContent["error"]
    asyncio.run(exercise())
    assert not (local_root / "devcore.db").exists()


def test_project_context_mcp_is_bound_measured_and_has_no_database_effects(tmp_path):
    local_root, data_root, context_root = (tmp_path / name for name in ("local", "shared", "context"))
    for directory in (local_root, data_root, context_root):
        directory.mkdir()
    card = context_root / "card.md"
    card.write_text("# Alpha\nLocal pilot, PostgreSQL target not yet deployed.\n", encoding="utf-8")
    manifest = {
        "schema_version": 1, "project": "alpha", "reviewed_at": "2026-10-03", "card": "card.md",
        "card_sha256": hashlib.sha256(card.read_bytes()).hexdigest(),
        "decisions": [
            {"id": "cloud", "status": "superseded", "required": False, "date": None,
             "decision": "Use cloud immediately", "rationale": "Old direction", "validation": "Old request",
             "sources": ["conversation"], "tags": [], "replaces": []},
            {"id": "local", "status": "effective", "required": True, "date": "2026-10-03",
             "decision": "Deploy local first", "rationale": "Local pilot", "validation": "User choice",
             "sources": ["plan"], "tags": [], "replaces": ["cloud"]}
        ]
    }
    (context_root / "context.json").write_text(json.dumps(manifest), encoding="utf-8")
    before = {path.name: path.read_bytes() for path in context_root.iterdir()}
    script = Path(__file__).with_name("server.py")

    async def exercise():
        params = StdioServerParameters(command=sys.executable, args=[str(script)], cwd=str(script.parent),
            env={**os.environ, "DEVCORE_PLATFORM_ROOT": str(script.parents[2]),
                 "DEVCORE_LOCAL_ROOT": str(local_root), "DEVCORE_DATA_ROOT": str(data_root),
                 "DEVCORE_MCP_READ_ONLY": "1", "DEVCORE_MCP_PROJECT": "alpha",
                 "DEVCORE_CONTEXT_ROOT": str(context_root), "DEVCORE_CONTEXT_MAX_BYTES": "8000"})
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as client:
                await client.initialize()
                response = await client.call_tool("devcore_project_context", {"project": "alpha"})
                assert not response.isError
                assert response.structuredContent is None
                assert len(response.content) == 1
                text = response.content[0].text
                context = json.loads(text)
                assert context["measurement"]["used"] == len(text.encode("utf-8"))
                assert context["measurement"]["used"] <= 8000
                assert "Use cloud immediately" not in text
                assert context["decisions"][0]["id"] == "local"
                for arguments in ({"project": "beta"}, {}, {"project": "alpha", "budget_bytes": 8001},
                                  {"project": "alpha", "directory": str(tmp_path)},
                                  {"project": "alpha", "budget_bytes": 256}):
                    refused = await client.call_tool("devcore_project_context", arguments)
                    assert refused.isError
                    assert "Local pilot, PostgreSQL" not in refused.content[0].text
    asyncio.run(exercise())
    assert {path.name: path.read_bytes() for path in context_root.iterdir()} == before
    assert not list(local_root.rglob("*"))
    assert not list(data_root.rglob("*"))


def test_project_context_mcp_has_no_implicit_directory(tmp_path):
    local_root, data_root = tmp_path / "local", tmp_path / "shared"
    local_root.mkdir()
    data_root.mkdir()
    script = Path(__file__).with_name("server.py")
    env = {**os.environ, "DEVCORE_PLATFORM_ROOT": str(script.parents[2]),
           "DEVCORE_LOCAL_ROOT": str(local_root), "DEVCORE_DATA_ROOT": str(data_root),
           "DEVCORE_MCP_READ_ONLY": "1", "DEVCORE_MCP_PROJECT": "alpha"}
    env.pop("DEVCORE_CONTEXT_ROOT", None)

    async def exercise():
        params = StdioServerParameters(command=sys.executable, args=[str(script)], cwd=str(script.parent), env=env)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as client:
                await client.initialize()
                result = await client.call_tool("devcore_project_context", {"project": "alpha"})
                assert result.isError
                assert "DEVCORE_CONTEXT_ROOT" in result.content[0].text
    asyncio.run(exercise())
    assert not list(local_root.rglob("*"))
    assert not list(data_root.rglob("*"))


def test_conditional_mcp_completion_refuses_stale_state_without_advancing_queue(tmp_path):
    script = Path(__file__).with_name("server.py")
    local_root, data_root = tmp_path / "local", tmp_path / "shared"
    local_root.mkdir()
    data_root.mkdir()
    database = local_root / "devcore.db"
    conn = init_db(database)
    for project in ("alpha", "beta"):
        conn.execute("INSERT INTO projects(id,name,root_path) VALUES (?,?,'.')", (project, project))
        conn.execute("INSERT INTO tasks(id,project_id,title,status) VALUES ('T-01',?,?,'in_progress')", (project, project))
    conn.execute("INSERT INTO tasks(id,project_id,title,status) VALUES ('T-02','alpha','Next','todo')")
    conn.execute("UPDATE tasks SET title='Changed elsewhere' WHERE project_id='alpha' AND id='T-01'")
    conn.commit()
    conn.close()

    async def exercise():
        params = StdioServerParameters(command=sys.executable, args=[str(script)], cwd=str(script.parent),
            env={**os.environ, "DEVCORE_PLATFORM_ROOT": str(script.parents[2]),
                 "DEVCORE_LOCAL_ROOT": str(local_root), "DEVCORE_DATA_ROOT": str(data_root),
                 "DEVCORE_MCP_READ_ONLY": "0", "DEVCORE_MCP_PROJECT": "alpha"})
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as client:
                await client.initialize()
                for _ in range(3):
                    stale = await client.call_tool("devcore_task_done", {"project": "alpha", "task_id": "T-01", "expected_version": 1})
                    assert stale.isError
                    assert stale.structuredContent["code"] == "stale_task_version"
                with sqlite3.connect(database) as check:
                    assert check.execute("SELECT COUNT(*) FROM bus_events").fetchone()[0] == 0
                    assert check.execute("SELECT status,version FROM tasks WHERE project_id='alpha' AND id='T-01'").fetchone() == ("in_progress", 2)
                missing_id = await client.call_tool("devcore_task_done", {"project": "alpha", "expected_version": 2})
                assert missing_id.isError
                assert missing_id.structuredContent["code"] == "invalid_arguments"
                cross = await client.call_tool("devcore_task_done", {"project": "beta", "task_id": "T-01", "expected_version": 1})
                assert cross.isError
                completed = await client.call_tool("devcore_task_done", {"project": "alpha", "task_id": "t-01", "expected_version": 2})
                assert not completed.isError
                assert completed.structuredContent["version"] == 3
                assert completed.structuredContent["task_id"] == "T-01"
                assert completed.structuredContent["project"] == "alpha"
    asyncio.run(exercise())
    with sqlite3.connect(database) as check:
        assert check.execute("SELECT status,version FROM tasks WHERE project_id='alpha' AND id='T-01'").fetchone() == ("done", 3)
        assert check.execute("SELECT status FROM tasks WHERE project_id='alpha' AND id='T-02'").fetchone()[0] == "todo"
        assert check.execute("SELECT status,version FROM tasks WHERE project_id='beta'").fetchone() == ("in_progress", 1)
        assert check.execute("SELECT COUNT(*) FROM bus_events WHERE event_type='TaskCompleted'").fetchone()[0] == 1


def test_conditional_mcp_completion_does_not_migrate_old_schema(tmp_path):
    script = Path(__file__).with_name("server.py")
    local_root, data_root = tmp_path / "local", tmp_path / "shared"
    local_root.mkdir()
    data_root.mkdir()
    database = local_root / "devcore.db"
    with sqlite3.connect(database) as conn:
        conn.executescript("""CREATE TABLE projects(id TEXT);
            CREATE TABLE tasks(id TEXT, project_id TEXT, title TEXT, status TEXT);
            INSERT INTO projects VALUES ('alpha');
            INSERT INTO tasks VALUES ('T-01','alpha','Old task','in_progress');""")
        schema = conn.execute("SELECT sql FROM sqlite_master ORDER BY name").fetchall()

    async def exercise():
        params = StdioServerParameters(command=sys.executable, args=[str(script)], cwd=str(script.parent),
            env={**os.environ, "DEVCORE_PLATFORM_ROOT": str(script.parents[2]),
                 "DEVCORE_LOCAL_ROOT": str(local_root), "DEVCORE_DATA_ROOT": str(data_root),
                 "DEVCORE_MCP_READ_ONLY": "0", "DEVCORE_MCP_PROJECT": "alpha"})
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as client:
                await client.initialize()
                result = await client.call_tool("devcore_task_done", {"project": "alpha", "task_id": "T-01", "expected_version": 1})
                assert result.isError
                assert result.structuredContent["code"] == "task_version_unavailable"
    asyncio.run(exercise())
    with sqlite3.connect(database) as conn:
        assert conn.execute("SELECT sql FROM sqlite_master ORDER BY name").fetchall() == schema
        assert conn.execute("SELECT status FROM tasks").fetchone()[0] == "in_progress"
