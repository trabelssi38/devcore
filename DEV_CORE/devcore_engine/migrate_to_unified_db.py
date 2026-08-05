"""
migrate_to_unified_db.py -- Idempotent Migration Script for DEV_CORE
Migrates data from file-based persistent stores into devcore.db
"""

from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

import csv
import json
import os
import re
import sqlite3
from typing import Any, Dict, List, Optional

from devcore_engine.db import connect_db, get_data_root, init_db



class DevCoreMigrator:
    def __init__(self, data_root: Optional[Path] = None):
        self.data_root = data_root or get_data_root()
        self.db_path = self.data_root / "devcore.db"
        self.conn = connect_db(self.db_path)
        # Disable foreign keys temporarily for initial bulk import
        self.conn.execute("PRAGMA foreign_keys = OFF;")

    def run_all(self) -> Dict[str, int]:
        stats = {}
        stats["projects"] = self.migrate_projects()
        stats["tasks"] = self.migrate_tasks()
        stats["events"] = self.migrate_bus_events()
        stats["memory"] = self.migrate_memory_entries()
        stats["knowledge_graph"] = self.migrate_knowledge_graph()
        stats["vault_notes"] = self.migrate_vault_notes()
        stats["workflows"] = self.migrate_workflows()
        stats["plugins"] = self.migrate_plugins_registry()
        stats["skills"] = self.migrate_skills_runtime()
        stats["metrics"] = self.migrate_metrics()
        stats["config"] = self.migrate_configs()
        # Re-enable foreign keys
        self.conn.execute("PRAGMA foreign_keys = ON;")
        return stats

    def migrate_projects(self) -> int:
        count = 0
        projects_config = self.data_root.parent / "DEV_CORE" / "Config" / "projects.json"
        if projects_config.exists():
            try:
                data = json.loads(projects_config.read_text(encoding="utf-8-sig"))
                projects = data if isinstance(data, list) else data.get("projects", [])
                for proj in projects:
                    proj_id = proj.get("id") or proj.get("name")
                    if proj_id:
                        self.conn.execute(
                            """
                            INSERT INTO projects (id, name, root_path, status, metadata)
                            VALUES (?, ?, ?, ?, ?)
                            ON CONFLICT(id) DO UPDATE SET
                                name=excluded.name,
                                root_path=excluded.root_path,
                                updated_at=datetime('now');
                            """,
                            (
                                proj_id,
                                proj.get("name", proj_id),
                                proj.get("root_path", "C:/devcore"),
                                proj.get("status", "active"),
                                json.dumps(proj.get("metadata", {})),
                            ),
                        )
                        count += 1
            except Exception as e:
                print(f"[WARN] Error migrating projects: {e}")
        
        # Ensure default project exists
        self.conn.execute(
            """
            INSERT INTO projects (id, name, root_path, status)
            VALUES ('devcore', 'devcore', 'C:/devcore', 'active')
            ON CONFLICT(id) DO NOTHING;
            """
        )
        self.conn.commit()
        return count + 1

    def migrate_tasks(self) -> int:
        count = 0
        memory_dir = self.data_root / "Memory"
        if not memory_dir.exists():
            return count

        for task_file in memory_dir.rglob("tasks.json"):
            project_name = task_file.parent.name
            if project_name == "Memory":
                project_name = "devcore"
            try:
                board = json.loads(task_file.read_text(encoding="utf-8-sig"))
                tasks_list = board.get("tasks", []) if isinstance(board, dict) else []
                for t in tasks_list:
                    task_id = t.get("id")
                    if not task_id:
                        continue
                    
                    self.conn.execute(
                        """
                        INSERT INTO tasks (
                            id, project_id, title, mode, status,
                            steps_done, steps_total, depends_on, worktree, metadata,
                            started_at, completed_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(id) DO UPDATE SET
                            title=excluded.title,
                            mode=excluded.mode,
                            status=excluded.status,
                            steps_done=excluded.steps_done,
                            steps_total=excluded.steps_total,
                            updated_at=datetime('now');
                        """,
                        (
                            task_id,
                            project_name,
                            t.get("title", f"Task {task_id}"),
                            t.get("mode", "coding"),
                            t.get("status", "todo"),
                            int(t.get("steps_done", 0)),
                            int(t.get("steps_total", 1)),
                            t.get("depends_on"),
                            t.get("worktree"),
                            json.dumps(t.get("metadata", {})),
                            t.get("started_at"),
                            t.get("completed_at"),
                        ),
                    )
                    count += 1
            except Exception as e:
                print(f"[WARN] Error migrating tasks from {task_file}: {e}")

        self.conn.commit()
        return count

    def migrate_bus_events(self) -> int:
        count = 0
        events_dir = self.data_root / "Bus" / "events"
        if not events_dir.exists():
            return count

        for jsonl_file in events_dir.glob("*.jsonl"):
            try:
                lines = jsonl_file.read_text(encoding="utf-8-sig").splitlines()
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    event = json.loads(line)
                    evt_id = event.get("id")
                    if not evt_id:
                        continue
                    
                    self.conn.execute(
                        """
                        INSERT INTO bus_events (
                            id, source, event_type, project, task_id, correlation_id, payload, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, COALESCE(?, datetime('now')))
                        ON CONFLICT(id) DO NOTHING;
                        """,
                        (
                            evt_id,
                            event.get("source", "devcore"),
                            event.get("event_type", "generic"),
                            event.get("project", "devcore"),
                            event.get("task_id"),
                            event.get("correlation_id"),
                            json.dumps(event.get("payload", {})),
                            event.get("timestamp") or event.get("created_at"),
                        ),
                    )
                    count += 1
            except Exception as e:
                print(f"[WARN] Error migrating bus events from {jsonl_file}: {e}")

        self.conn.commit()
        return count

    def migrate_memory_entries(self) -> int:
        count = 0
        memory_dir = self.data_root / "Memory"
        if not memory_dir.exists():
            return count

        memory_files = {
            "MEMORY": memory_dir / "MEMORY.md",
            "DECISIONS": memory_dir / "DECISIONS.md",
            "LESSONS": memory_dir / "LESSONS.md",
            "PATTERNS": memory_dir / "PATTERNS.md",
            "PERSONA": memory_dir / "persona.md",
        }

        for name, path in memory_files.items():
            if path.exists():
                content = path.read_text(encoding="utf-8-sig")
                self.conn.execute(
                    """
                    INSERT INTO memory_entries (name, task_type, content, updated_at)
                    VALUES (?, 'devcore', ?, datetime('now'))
                    ON CONFLICT(name, task_type) DO UPDATE SET
                        content=excluded.content,
                        updated_at=datetime('now');
                    """,
                    (name, content),
                )
                count += 1

        scenarios_dir = memory_dir / "Scenarios"
        if scenarios_dir.exists():
            for sc_file in scenarios_dir.glob("*.md"):
                task_type = sc_file.stem
                content = sc_file.read_text(encoding="utf-8-sig")
                self.conn.execute(
                    """
                    INSERT INTO memory_entries (name, task_type, content, updated_at)
                    VALUES ('SCENARIO', ?, ?, datetime('now'))
                    ON CONFLICT(name, task_type) DO UPDATE SET
                        content=excluded.content,
                        updated_at=datetime('now');
                    """,
                    (task_type, content),
                )
                count += 1

        self.conn.commit()
        return count

    def migrate_knowledge_graph(self) -> int:
        count = 0
        kg_dir = self.data_root / "Knowledge"
        if not kg_dir.exists():
            return count

        for graph_file in kg_dir.glob("*.json"):
            try:
                graph = json.loads(graph_file.read_text(encoding="utf-8-sig"))
                nodes = graph.get("nodes", {})
                edges = graph.get("edges", {})

                # Nodes
                node_list = nodes.values() if isinstance(nodes, dict) else nodes
                for n in node_list:
                    nid = n.get("id")
                    if not nid:
                        continue
                    self.conn.execute(
                        """
                        INSERT INTO kg_nodes (id, type, label, properties)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(id) DO UPDATE SET
                            label=excluded.label,
                            properties=excluded.properties;
                        """,
                        (
                            nid,
                            n.get("type", "unknown"),
                            n.get("label", nid),
                            json.dumps(n.get("properties", {})),
                        ),
                    )
                    count += 1

                # Edges
                edge_list = edges.values() if isinstance(edges, dict) else edges
                for e in edge_list:
                    from_node = e.get("from") or e.get("from_node")
                    to_node = e.get("to") or e.get("to_node")
                    if from_node and to_node:
                        self.conn.execute(
                            """
                            INSERT INTO kg_edges (from_node, to_node, type, properties)
                            VALUES (?, ?, ?, ?);
                            """,
                            (
                                from_node,
                                to_node,
                                e.get("type", "relates_to"),
                                json.dumps(e.get("properties", {})),
                            ),
                        )
                        count += 1
            except Exception as exc:
                print(f"[WARN] Error migrating knowledge graph {graph_file}: {exc}")

        self.conn.commit()
        return count

    def migrate_vault_notes(self) -> int:
        count = 0
        vault_dir = self.data_root / "Vault"
        if not vault_dir.exists():
            return count

        for md_file in vault_dir.rglob("*.md"):
            try:
                rel_path = md_file.relative_to(vault_dir).as_posix()
                content = md_file.read_text(encoding="utf-8-sig")
                
                # Parse title from frontmatter if exists
                title = md_file.stem
                tags = []
                match = re.search(r"^---\s*\ntitle:\s*(.*?)\n(?:tags:\s*\[(.*?)\])?", content, re.MULTILINE)
                if match:
                    if match.group(1):
                        title = match.group(1).strip()
                    if match.group(2):
                        tags = [t.strip() for t in match.group(2).split(",") if t.strip()]

                self.conn.execute(
                    """
                    INSERT INTO vault_notes (path, title, tags, content, updated_at)
                    VALUES (?, ?, ?, ?, datetime('now'))
                    ON CONFLICT(path) DO UPDATE SET
                        title=excluded.title,
                        tags=excluded.tags,
                        content=excluded.content,
                        updated_at=datetime('now');
                    """,
                    (rel_path, title, json.dumps(tags), content),
                )
                count += 1
            except Exception as exc:
                print(f"[WARN] Error migrating vault note {md_file}: {exc}")

        self.conn.commit()
        return count

    def migrate_workflows(self) -> int:
        count = 0
        wf_dir = self.data_root / "Workflows"
        if not wf_dir.exists():
            return count

        for wf_file in wf_dir.glob("*.json"):
            try:
                wf_id = wf_file.stem
                state_json = wf_file.read_text(encoding="utf-8-sig")
                self.conn.execute(
                    """
                    INSERT INTO workflow_states (id, state, updated_at)
                    VALUES (?, ?, datetime('now'))
                    ON CONFLICT(id) DO UPDATE SET
                        state=excluded.state,
                        updated_at=datetime('now');
                    """,
                    (wf_id, state_json),
                )
                count += 1
            except Exception as exc:
                print(f"[WARN] Error migrating workflow {wf_file}: {exc}")

        self.conn.commit()
        return count

    def migrate_plugins_registry(self) -> int:
        count = 0
        reg_file = self.data_root / "Plugins" / "plugins_registry.json"
        if reg_file.exists():
            try:
                registry = json.loads(reg_file.read_text(encoding="utf-8-sig"))
                plugins = registry if isinstance(registry, list) else registry.get("plugins", [])
                for p in plugins:
                    pid = p.get("id") or p.get("name")
                    if not pid:
                        continue
                    self.conn.execute(
                        """
                        INSERT INTO plugins_registry (id, name, version, enabled, metadata)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(id) DO UPDATE SET
                            version=excluded.version,
                            enabled=excluded.enabled,
                            metadata=excluded.metadata;
                        """,
                        (
                            pid,
                            p.get("name", pid),
                            p.get("version", "1.0.0"),
                            1 if p.get("enabled", True) else 0,
                            json.dumps(p.get("metadata", {})),
                        ),
                    )
                    count += 1
            except Exception as exc:
                print(f"[WARN] Error migrating plugins registry: {exc}")

        self.conn.commit()
        return count

    def migrate_skills_runtime(self) -> int:
        count = 0
        skills_file = self.data_root / "Skills" / "skills_runtime.json"
        if skills_file.exists():
            try:
                data = json.loads(skills_file.read_text(encoding="utf-8-sig"))
                skills = data if isinstance(data, list) else data.get("skills", [])
                for s in skills:
                    sid = s.get("id") or s.get("name")
                    if not sid:
                        continue
                    self.conn.execute(
                        """
                        INSERT INTO skills_runtime (id, name, status, metadata, updated_at)
                        VALUES (?, ?, ?, ?, datetime('now'))
                        ON CONFLICT(id) DO UPDATE SET
                            status=excluded.status,
                            metadata=excluded.metadata,
                            updated_at=datetime('now');
                        """,
                        (
                            sid,
                            s.get("name", sid),
                            s.get("status", "discovered"),
                            json.dumps(s.get("metadata", {})),
                        ),
                    )
                    count += 1
            except Exception as exc:
                print(f"[WARN] Error migrating skills runtime: {exc}")

        self.conn.commit()
        return count

    def migrate_metrics(self) -> int:
        count = 0
        kpi_file = self.data_root / "Metrics" / "kpi.csv"
        if kpi_file.exists():
            try:
                with open(kpi_file, mode="r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        self.conn.execute(
                            """
                            INSERT INTO metrics (source, project, metric_type, value, unit, payload, recorded_at)
                            VALUES (?, ?, ?, ?, ?, ?, COALESCE(?, datetime('now')));
                            """,
                            (
                                row.get("source", "legacy"),
                                row.get("project", "devcore"),
                                row.get("metric_type", "kpi"),
                                float(row.get("value", 0.0)),
                                row.get("unit", "count"),
                                row.get("payload", "{}"),
                                row.get("timestamp") or row.get("recorded_at"),
                            ),
                        )
                        count += 1
            except Exception as exc:
                print(f"[WARN] Error migrating kpi.csv: {exc}")

        self.conn.commit()
        return count

    def migrate_configs(self) -> int:
        count = 0
        config_dir = self.data_root.parent / "DEV_CORE" / "Config"
        if not config_dir.exists():
            return count

        # List of non-sensitive config files to store in DB
        db_configs = ["embedding.json", "harness_profiles.json", "intent_patterns.json", "model_pricing.json", "network.json", "routing_profiles.json", "settings.json"]
        for cfg_name in db_configs:
            cfg_path = config_dir / cfg_name
            if cfg_path.exists():
                try:
                    content = cfg_path.read_text(encoding="utf-8")
                    key_name = cfg_path.stem
                    self.conn.execute(
                        """
                        INSERT INTO config (key, value, format, updated_at)
                        VALUES (?, ?, 'json', datetime('now'))
                        ON CONFLICT(key) DO UPDATE SET
                            value=excluded.value,
                            updated_at=datetime('now');
                        """,
                        (key_name, content),
                    )
                    count += 1
                except Exception as exc:
                    print(f"[WARN] Error migrating config {cfg_name}: {exc}")

        self.conn.commit()
        return count


if __name__ == "__main__":
    print("Starting DEV_CORE data migration to devcore.db...")
    migrator = DevCoreMigrator()
    res = migrator.run_all()
    print("Migration complete! Statistics:")
    for category, cnt in res.items():
        print(f"  - {category}: {cnt} items migrated")
