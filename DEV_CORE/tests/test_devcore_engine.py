"""
test_devcore_engine.py -- Unit Tests for DEV_CORE Engine Python Runtime
"""

from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

import pytest
import sqlite3
from devcore_engine.db import init_db, HAS_SQLITE_VEC
from devcore_engine.services.memory import MemoryService
from devcore_engine.services.events import EventBus
from devcore_engine.services.tasks import TaskService
from devcore_engine.services.skills import SkillService
from devcore_engine.services.knowledge import KnowledgeGraph
from devcore_engine.services.plugins import PluginService
from devcore_engine.lifecycle.session import SessionManager
from devcore_engine.infra.diagnose import DiagnosticEngine


def test_db_initialization(tmp_path):
    db_file = tmp_path / "test_devcore.db"
    conn = init_db(db_file)
    assert db_file.exists()
    cursor = conn.cursor()
    tables = [r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    assert "projects" in tables
    assert "tasks" in tables
    assert "events" in tables
    assert "memory_entries" in tables
    conn.close()


def test_memory_service(tmp_path):
    db_file = tmp_path / "test_devcore.db"
    conn = init_db(db_file)
    ms = MemoryService(conn)
    
    ms.write_text("PERSONA", "Test Persona Content")
    content = ms.get_text("PERSONA")
    assert content == "Test Persona Content"

    appended = ms.append_text("PERSONA", "Second Line")
    assert "Second Line" in appended
    conn.close()


def test_event_bus(tmp_path):
    db_file = tmp_path / "test_devcore.db"
    conn = init_db(db_file)
    bus = EventBus(conn)

    evt_id = bus.publish("UnitTested", {"payload": "val"})
    assert evt_id.startswith("evt_")

    recent = bus.tail(5)
    assert len(recent) >= 1
    assert recent[0]["event_type"] == "UnitTested"
    conn.close()


def test_task_service(tmp_path):
    db_file = tmp_path / "test_devcore.db"
    conn = init_db(db_file)
    ts = TaskService(conn)

    t = ts.add_task("Test Task Engine", mode="coding", steps=2, project_id="test_proj")
    assert t["id"].startswith("T-")
    assert t["title"] == "test task engine"

    next_t = ts.next_task("test_proj")
    assert next_t["id"] == t["id"]
    assert next_t["status"] == "in_progress"

    step_t = ts.step_task(t["id"], project_id="test_proj")
    assert step_t["steps_done"] == 1

    comp_t = ts.complete_task(t["id"], project_id="test_proj")
    assert comp_t["status"] == "done"
    conn.close()


def test_skill_service(tmp_path):
    db_file = tmp_path / "test_devcore.db"
    conn = init_db(db_file)
    ss = SkillService(conn)

    ss.register_skill("unit_test_skill", "active", {"version": "1.0"})
    skills = ss.list_skills()
    assert any(s["name"] == "unit_test_skill" for s in skills)
    conn.close()


def test_knowledge_graph(tmp_path):
    db_file = tmp_path / "test_devcore.db"
    conn = init_db(db_file)
    kg = KnowledgeGraph(conn)

    kg.add_node("n1", "file", "File 1")
    kg.add_node("n2", "file", "File 2")
    kg.add_edge("n1", "n2", "imports")

    stats = kg.get_stats()
    assert stats["nodes"] == 2
    assert stats["edges"] == 1

    impact = kg.impact_analysis("n1")
    assert impact["blast_radius_count"] == 2
    conn.close()


def test_plugin_service(tmp_path):
    db_file = tmp_path / "test_devcore.db"
    conn = init_db(db_file)
    ps = PluginService(conn)

    ps.register_plugin("test_plugin", "test_plugin", "1.0.0", True)
    plugins = ps.list_plugins()
    assert any(p["name"] == "test_plugin" for p in plugins)
    
    ps.toggle_plugin("test_plugin", False)
    updated = ps.list_plugins()
    target = [p for p in updated if p["name"] == "test_plugin"][0]
    assert target["enabled"] == 0
    conn.close()


def test_diagnostic_engine(tmp_path):
    data_dir = tmp_path / "DEV_CORE_DATA"
    diag = DiagnosticEngine(data_dir)
    res = diag.run_diagnostics()
    assert "overall_status" in res
    assert len(res["checks"]) >= 5
