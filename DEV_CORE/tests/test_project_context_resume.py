from datetime import date
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from devcore_engine.services.project_context import (
    ContextBudgetExceeded, encode_context, load_project_context,
)


def decision(identity, status="effective", required=False, replaces=None, tags=None):
    return {"id": identity, "status": status, "required": required, "date": "2026-10-03",
            "decision": "Local pilot" if identity == "local" else "Optional worker architecture",
            "rationale": "Qualified direction", "validation": "User-approved plan",
            "sources": ["plan.md"], "tags": tags or [], "replaces": replaces or []}


def fixture_context(tmp_path):
    card = tmp_path / "card.md"
    card.write_text("# Project alpha\nDéploiement local ; accès réseau à qualifier.\n", encoding="utf-8")
    old = decision("cloud", "superseded")
    old["decision"] = "Use cloud immediately"
    manifest = {"schema_version": 1, "project": "alpha", "reviewed_at": "2026-10-03",
                "card": "card.md", "card_sha256": hashlib.sha256(card.read_bytes()).hexdigest(),
                "decisions": [old, decision("local", required=True, replaces=["cloud"]),
                              decision("dbos", "proposed", tags=["worker", "reprise"])]}
    path = tmp_path / "context.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path, manifest


def test_required_context_and_replacement_with_no_writes(tmp_path):
    path, _ = fixture_context(tmp_path)
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    result = load_project_context(tmp_path, "alpha", today=date(2026, 10, 3))
    assert [d["id"] for d in result["decisions"]] == ["local"]
    assert "Use cloud immediately" not in encode_context(result)
    assert result["excluded_superseded"] == ["cloud"]
    assert result["omitted"] == [{"id": "dbos", "reason": "not_relevant"}]
    assert result["measurement"]["used"] == len((encode_context(result) + "\n").encode())
    assert result["measurement"]["model_tokens_measured"] is False
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before


def test_optional_decision_relevance_and_exact_budget(tmp_path):
    fixture_context(tmp_path)
    required = load_project_context(tmp_path, "alpha", budget_bytes=10000, today=date(2026, 10, 3))
    budget = required["measurement"]["used"] + 15
    limited = load_project_context(tmp_path, "alpha", budget_bytes=budget, query="worker", today=date(2026, 10, 3))
    assert limited["measurement"]["used"] <= budget
    assert limited["omitted"] == [{"id": "dbos", "reason": "budget"}]
    complete = load_project_context(tmp_path, "alpha", query="worker", today=date(2026, 10, 3))
    assert complete["decisions"][-1]["status"] == "proposed"
    with pytest.raises(ContextBudgetExceeded, match="no partial"):
        load_project_context(tmp_path, "alpha", budget_bytes=256)


def test_project_path_and_broken_replacements_fail_closed(tmp_path):
    path, manifest = fixture_context(tmp_path)
    with pytest.raises(ValueError, match="mismatch"):
        load_project_context(tmp_path, "beta")
    manifest["card"] = "../outside.md"
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="outside"):
        load_project_context(tmp_path, "alpha")
    manifest["card"] = "card.md"
    manifest["decisions"][1]["replaces"] = []
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="requires a replacement"):
        load_project_context(tmp_path, "alpha")


def test_modified_card_and_expired_review_are_visible(tmp_path):
    fixture_context(tmp_path)
    (tmp_path / "card.md").write_text("Changed card")
    result = load_project_context(tmp_path, "alpha", today=date(2026, 10, 12))
    assert result["warnings"] == ["card_changed_since_review", "context_review_expired"]


def test_a_proposal_cannot_replace_an_effective_direction(tmp_path):
    path, manifest = fixture_context(tmp_path)
    manifest["decisions"][1]["status"] = "proposed"
    manifest["decisions"][1]["required"] = False
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="end in an effective"):
        load_project_context(tmp_path, "alpha")


def test_symlink_cannot_escape_selected_directory(tmp_path):
    path, manifest = fixture_context(tmp_path)
    outside = tmp_path.parent / (tmp_path.name + "-outside.md")
    outside.write_text("Outside project")
    link = tmp_path / "link.md"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlink privilege not available")
    manifest["card"] = "link.md"
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="outside"):
        load_project_context(tmp_path, "alpha")


def test_cli_outputs_exact_measured_utf8_and_errors_without_context(tmp_path):
    fixture_context(tmp_path)
    script = Path(__file__).resolve().parents[1] / "Scripts" / "resume_project_context.py"
    command = [sys.executable, str(script), "--directory", str(tmp_path), "--project", "alpha"]
    result = subprocess.run(command, capture_output=True, env=os.environ.copy(), check=True)
    output = json.loads(result.stdout)
    assert output["measurement"]["used"] == len(result.stdout)
    failed = subprocess.run(command + ["--budget-bytes", "256"], capture_output=True)
    assert failed.returncode == 2
    assert failed.stdout == b""
