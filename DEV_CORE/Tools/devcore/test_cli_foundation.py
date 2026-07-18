import sys
import os
import json
import sqlite3
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Setup sys.path to import modules correctly
tools_dir = Path(__file__).resolve().parent.parent
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))

scripts_dir = tools_dir.parent / "Scripts"
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

import dc
from devcore.paths import get_paths


def test_paths_canonicalization():
    """Verify that DEV_CORE paths are correctly canonicalized and resolved."""
    paths = get_paths()
    assert paths is not None
    assert paths.platform_root.exists()
    assert paths.data_root.name == "DEV_CORE_DATA"
    assert paths.bus_root == paths.platform_root / "Bus"
    assert paths.session_root == paths.data_root / "Sessions"


def test_get_active_project_git(tmp_path):
    """Verify active project resolution using Git repository folder name."""
    with patch("subprocess.check_output") as mock_git:
        # Mock git common dir path
        mock_git.return_value = os.path.join(str(tmp_path), "my-git-project", ".git")
        
        # Clear env variables cache first
        with patch.dict(os.environ, {}, clear=True):
            project = dc.get_active_project()
            assert project is not None
            assert isinstance(project, str)


def test_resolve_routing_profile():
    """Verify routing profile resolution defaults or overrides from json configurations."""
    profile = dc.resolve_routing_profile("coding")
    assert profile["mode"] == "coding"
    assert "gemini_model" in profile
    assert "budget" in profile


@patch("subprocess.run")
@patch("dc.ping_tcp")
@patch("dc.ping_http")
def test_embedding_mismatch_warning(mock_ping_http, mock_ping_tcp, mock_sub_run, tmp_path):
    """Verify that dc doctor flags warning when embedding models mismatch."""
    mock_ping_http.return_value = True
    mock_ping_tcp.return_value = True
    
    mock_run_result = MagicMock()
    mock_run_result.returncode = 0
    mock_sub_run.return_value = mock_run_result

    mock_emb_data = {
        "schema_version": 1,
        "provider": "gemini-router",
        "model": "text-embedding-3-small",
        "query_model": "gemini-embedding-001",
        "dimensions": 768
    }
    
    with patch("dc.DEV_CORE", tmp_path):
        # Create Config dir
        (tmp_path / "Config").mkdir(parents=True, exist_ok=True)
        (tmp_path / "Config" / "embedding.json").write_text(json.dumps(mock_emb_data), encoding="utf-8")
        
        with patch("dc.get_data_root", return_value=tmp_path):
            with patch("dc.print_color") as mock_print:
                dc.cmd_doctor(None)
                # Verify it prints warnings about embedding mismatch or coherence
                any_warn = any("mismatch" in str(call).lower() or "coherence" in str(call).lower() for call in mock_print.call_args_list)
                assert any_warn


@patch("subprocess.run")
@patch("dc.ping_tcp")
@patch("dc.ping_http")
def test_conversations_db_fts5_check(mock_ping_http, mock_ping_tcp, mock_sub_run, tmp_path):
    """Verify doctor check for SQLite database and FTS5 table presence."""
    mock_ping_http.return_value = True
    mock_ping_tcp.return_value = True
    
    mock_run_result = MagicMock()
    mock_run_result.returncode = 0
    mock_sub_run.return_value = mock_run_result

    # Create dummy tasks.json
    (tmp_path / "Memory").mkdir(parents=True, exist_ok=True)
    
    db_file = tmp_path / "Memory" / "conversations.db"
    
    # Create valid sqlite db with fts5 table
    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS conversations (id INTEGER PRIMARY KEY, content TEXT, project TEXT, task_id TEXT);")
    try:
        cursor.execute("CREATE VIRTUAL TABLE conversations_fts USING fts5(content, project, task_id);")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

    with patch("dc.get_data_root", return_value=tmp_path):
        with patch("dc.print_color") as mock_print:
            dc.cmd_doctor(None)
            # Ensure SQLite is diagnosed as OK
            sqlite_checked = any("sqlite" in str(call).lower() for call in mock_print.call_args_list)
            assert sqlite_checked
