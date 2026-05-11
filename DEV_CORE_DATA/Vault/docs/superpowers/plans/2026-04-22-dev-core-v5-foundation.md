# DEV_CORE v5 Foundation Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first working vertical slice of DEV_CORE v5: file-based handoffs, explainable routing, recoverable session folders, memory review drafts, and engine-specific prompt packaging on a Windows workstation.

**Architecture:** This plan implements the stable core first: `paths -> schemas -> router -> sessions -> memory queue -> adapters -> launcher entrypoint`. It deliberately excludes the dashboard, advanced watchers, and deep analytics so the first slice remains small, testable, and useful on its own.

**Tech Stack:** PowerShell 7, Python 3.11+, `pytest`, `jsonschema`, Markdown, JSON, local filesystem on Windows

---

## Scope Split

The approved design spans multiple independent subsystems. This plan covers only **Slice 1: Core control plane**.

Separate follow-up plans should handle:

- dashboard and observability UI
- real Windows watchers and event automation
- advanced memory scoring and self-healing
- richer Claude/Gemini/Codex desktop automation

## File Structure

### Platform files

- Create: `C:\DEV_CORE\pyproject.toml`
- Create: `C:\DEV_CORE\Tools\devcore\__init__.py`
- Create: `C:\DEV_CORE\Tools\devcore\paths.py`
- Create: `C:\DEV_CORE\Tools\devcore\contracts.py`
- Create: `C:\DEV_CORE\Tools\devcore\router.py`
- Create: `C:\DEV_CORE\Tools\devcore\session.py`
- Create: `C:\DEV_CORE\Tools\devcore\memory.py`
- Create: `C:\DEV_CORE\Tools\devcore\cli.py`
- Create: `C:\DEV_CORE\Tools\devcore\adapters\__init__.py`
- Create: `C:\DEV_CORE\Tools\devcore\adapters\base.py`
- Create: `C:\DEV_CORE\Tools\devcore\adapters\claude.py`
- Create: `C:\DEV_CORE\Tools\devcore\adapters\codex.py`
- Create: `C:\DEV_CORE\Tools\devcore\adapters\gemini.py`
- Create: `C:\DEV_CORE\Schemas\handoff.schema.json`
- Create: `C:\DEV_CORE\Schemas\receipt.schema.json`
- Create: `C:\DEV_CORE\Schemas\router-decision.schema.json`
- Modify: `C:\DEV_CORE\Scripts\launch.ps1`
- Modify: `C:\DEV_CORE\Scripts\sync_obsidian_memory.ps1`
- Modify: `C:\DEV_CORE\Config\BOOT.md`
- Modify: `C:\DEV_CORE\Config\ROUTER.md`

### Tests

- Create: `C:\DEV_CORE\Tests\test_paths.py`
- Create: `C:\DEV_CORE\Tests\test_contracts.py`
- Create: `C:\DEV_CORE\Tests\test_router.py`
- Create: `C:\DEV_CORE\Tests\test_session_memory.py`
- Create: `C:\DEV_CORE\Tests\test_adapters.py`
- Create: `C:\DEV_CORE\Tests\test_cli_smoke.py`

### Responsibility map

- `paths.py`: canonical Windows paths and bootstrap directories
- `contracts.py`: JSON schema loading and validation helpers
- `router.py`: explainable engine recommendation with fallback
- `session.py`: recoverable on-disk session workspace
- `memory.py`: memory draft generation, review queue, Qdrant refresh queue
- `adapters/*`: engine-specific prompt packaging without hidden execution
- `cli.py`: single `prepare` entrypoint for semi-automatic handoffs
- `launch.ps1`: thin PowerShell wrapper around `python -m devcore.cli`
- `sync_obsidian_memory.ps1`: move approved drafts into the vault and enqueue refresh

### Directory assumptions

This plan assumes these roots already exist and are the only canonical roots:

- `C:\DEV_CORE`
- `C:\DEV_CORE_DATA\Vault`
- `C:\DEV_CORE_DATA\Sessions`
- `C:\DEV_CORE_DATA\Memory`

## Task 1: Bootstrap The Python Workspace And Canonical Paths

**Files:**
- Create: `C:\DEV_CORE\pyproject.toml`
- Create: `C:\DEV_CORE\Tools\devcore\__init__.py`
- Create: `C:\DEV_CORE\Tools\devcore\paths.py`
- Test: `C:\DEV_CORE\Tests\test_paths.py`

- [ ] **Step 1: Initialize git in `C:\DEV_CORE` if it is not already a repository**

Run:

```powershell
git -C C:\DEV_CORE rev-parse --is-inside-work-tree
```

Expected:

```text
true
```

If you get a fatal error instead, run:

```powershell
git -C C:\DEV_CORE init
git -C C:\DEV_CORE branch -M main
```

- [ ] **Step 2: Write the failing path bootstrap test**

```python
# C:\DEV_CORE\Tests\test_paths.py
from pathlib import Path

from devcore.paths import get_paths


def test_get_paths_creates_required_directories(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVCORE_PLATFORM_ROOT", str(tmp_path / "platform"))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(tmp_path / "data"))

    paths = get_paths()

    assert paths.platform_root == Path(tmp_path / "platform")
    assert paths.data_root == Path(tmp_path / "data")
    assert (paths.bus_root / "drafts").is_dir()
    assert (paths.bus_root / "receipts").is_dir()
    assert paths.session_root.is_dir()
    assert paths.memory_review_pending.is_dir()
    assert paths.memory_review_approved.is_dir()
```

- [ ] **Step 3: Run the test to verify it fails**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_paths.py -q
```

Expected:

```text
E   ModuleNotFoundError: No module named 'devcore'
```

- [ ] **Step 4: Write the minimal package bootstrap and path resolver**

```toml
# C:\DEV_CORE\pyproject.toml
[project]
name = "devcore"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "jsonschema>=4.23.0",
  "pytest>=8.3.0",
]

[tool.pytest.ini_options]
pythonpath = ["Tools"]
testpaths = ["Tests"]
```

```python
# C:\DEV_CORE\Tools\devcore\__init__.py
__all__ = [
    "paths",
]
```

```python
# C:\DEV_CORE\Tools\devcore\paths.py
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DevCorePaths:
    platform_root: Path
    data_root: Path
    bus_root: Path
    session_root: Path
    vault_root: Path
    memory_root: Path
    memory_review_pending: Path
    memory_review_approved: Path
    qdrant_refresh_queue: Path
    schema_root: Path


def _env_path(name: str, default: str) -> Path:
    return Path(os.environ.get(name, default))


def get_paths() -> DevCorePaths:
    platform_root = _env_path("DEVCORE_PLATFORM_ROOT", r"C:\DEV_CORE")
    data_root = _env_path("DEVCORE_DATA_ROOT", r"C:\DEV_CORE_DATA")
    bus_root = platform_root / "Bus"
    session_root = data_root / "Sessions"
    vault_root = data_root / "Vault"
    memory_root = data_root / "Memory"
    memory_review_pending = vault_root / "05_AI" / "DEV_CORE" / "Memory Review" / "pending"
    memory_review_approved = vault_root / "05_AI" / "DEV_CORE" / "Memory Review" / "approved"
    schema_root = platform_root / "Schemas"

    required_dirs = [
        bus_root / "drafts",
        bus_root / "receipts",
        bus_root / "archive",
        session_root,
        memory_root,
        memory_review_pending,
        memory_review_approved,
        schema_root,
    ]
    for path in required_dirs:
        path.mkdir(parents=True, exist_ok=True)

    return DevCorePaths(
        platform_root=platform_root,
        data_root=data_root,
        bus_root=bus_root,
        session_root=session_root,
        vault_root=vault_root,
        memory_root=memory_root,
        memory_review_pending=memory_review_pending,
        memory_review_approved=memory_review_approved,
        qdrant_refresh_queue=memory_root / "qdrant-refresh.jsonl",
        schema_root=schema_root,
    )
```

- [ ] **Step 5: Run the test again and commit**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_paths.py -q
git add pyproject.toml Tools\devcore\__init__.py Tools\devcore\paths.py Tests\test_paths.py
git commit -m "feat: bootstrap devcore path model"
```

Expected:

```text
1 passed
```

## Task 2: Define JSON Contracts And Schema Validation

**Files:**
- Create: `C:\DEV_CORE\Schemas\handoff.schema.json`
- Create: `C:\DEV_CORE\Schemas\receipt.schema.json`
- Create: `C:\DEV_CORE\Schemas\router-decision.schema.json`
- Create: `C:\DEV_CORE\Tools\devcore\contracts.py`
- Test: `C:\DEV_CORE\Tests\test_contracts.py`

- [ ] **Step 1: Write the failing schema validation tests**

```python
# C:\DEV_CORE\Tests\test_contracts.py
import pytest

from devcore.contracts import validate_contract


def test_valid_handoff_contract_passes():
    payload = {
        "handoff_id": "hf_test_001",
        "project_id": "android_tooling",
        "task_type": "bugfix",
        "target_engine": "codex",
        "intent": "Fix parser regression",
        "context_refs": ["obsidian://08_Bugs/parser-crash.md"],
        "context_summary": "Crash on empty input",
        "constraints": ["patch minimal"],
        "expected_output": "patch + explanation + risks",
        "prepared_at": "2026-04-22T20:00:00Z",
    }

    validate_contract("handoff", payload)


def test_invalid_handoff_contract_raises_value_error():
    with pytest.raises(ValueError):
        validate_contract("handoff", {"handoff_id": "hf_missing_fields"})
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_contracts.py -q
```

Expected:

```text
E   ModuleNotFoundError: No module named 'devcore.contracts'
```

- [ ] **Step 3: Add the schemas and validator**

```json
// C:\DEV_CORE\Schemas\handoff.schema.json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": [
    "handoff_id",
    "project_id",
    "task_type",
    "target_engine",
    "intent",
    "context_refs",
    "context_summary",
    "constraints",
    "expected_output",
    "prepared_at"
  ],
  "properties": {
    "handoff_id": { "type": "string", "minLength": 1 },
    "project_id": { "type": "string", "minLength": 1 },
    "task_type": { "type": "string", "minLength": 1 },
    "target_engine": { "enum": ["claude", "codex", "gemini"] },
    "intent": { "type": "string", "minLength": 1 },
    "context_refs": { "type": "array", "items": { "type": "string" } },
    "context_summary": { "type": "string", "minLength": 1 },
    "constraints": { "type": "array", "items": { "type": "string" } },
    "expected_output": { "type": "string", "minLength": 1 },
    "prepared_at": { "type": "string", "minLength": 1 }
  },
  "additionalProperties": false
}
```

```json
// C:\DEV_CORE\Schemas\receipt.schema.json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": [
    "handoff_id",
    "engine",
    "status",
    "artifact_refs",
    "memory_candidates",
    "next_action"
  ],
  "properties": {
    "handoff_id": { "type": "string", "minLength": 1 },
    "engine": { "enum": ["claude", "codex", "gemini"] },
    "status": { "enum": ["completed", "low-value", "failed"] },
    "artifact_refs": { "type": "array", "items": { "type": "string" } },
    "memory_candidates": { "type": "array", "items": { "type": "string" } },
    "next_action": { "type": "string", "minLength": 1 }
  },
  "additionalProperties": false
}
```

```json
// C:\DEV_CORE\Schemas\router-decision.schema.json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["engine", "confidence", "fallback", "reason"],
  "properties": {
    "engine": { "enum": ["claude", "codex", "gemini"] },
    "confidence": { "type": "number", "minimum": 0, "maximum": 1 },
    "fallback": { "enum": ["claude", "codex", "gemini"] },
    "reason": { "type": "string", "minLength": 1 }
  },
  "additionalProperties": false
}
```

```python
# C:\DEV_CORE\Tools\devcore\contracts.py
import json

from jsonschema import Draft202012Validator

from devcore.paths import get_paths


def _load_schema(name: str) -> dict:
    schema_path = get_paths().schema_root / f"{name}.schema.json"
    return json.loads(schema_path.read_text(encoding="utf-8"))


def validate_contract(name: str, payload: dict) -> None:
    validator = Draft202012Validator(_load_schema(name))
    errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.path))
    if errors:
        messages = "; ".join(error.message for error in errors)
        raise ValueError(messages)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_contracts.py -q
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Commit**

```powershell
git -C C:\DEV_CORE add Schemas\handoff.schema.json Schemas\receipt.schema.json Schemas\router-decision.schema.json Tools\devcore\contracts.py Tests\test_contracts.py
git -C C:\DEV_CORE commit -m "feat: add handoff and receipt schema validation"
```

## Task 3: Implement An Explainable Router

**Files:**
- Create: `C:\DEV_CORE\Tools\devcore\router.py`
- Modify: `C:\DEV_CORE\Config\ROUTER.md`
- Test: `C:\DEV_CORE\Tests\test_router.py`

- [ ] **Step 1: Write the failing router tests**

```python
# C:\DEV_CORE\Tests\test_router.py
from devcore.router import recommend_engine


def test_bugfix_routes_to_codex():
    decision = recommend_engine(task_type="bugfix", urgency="normal", volume="small")
    assert decision["engine"] == "codex"
    assert decision["fallback"] == "claude"


def test_urgent_architecture_routes_to_claude():
    decision = recommend_engine(task_type="architecture", urgency="urgent", volume="medium")
    assert decision["engine"] == "claude"


def test_bulk_migration_routes_to_gemini():
    decision = recommend_engine(task_type="migration", urgency="normal", volume="large")
    assert decision["engine"] == "gemini"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_router.py -q
```

Expected:

```text
E   ModuleNotFoundError: No module named 'devcore.router'
```

- [ ] **Step 3: Implement the minimal scoring router and update the human-readable rules**

```python
# C:\DEV_CORE\Tools\devcore\router.py
from devcore.contracts import validate_contract


def recommend_engine(task_type: str, urgency: str, volume: str) -> dict:
    scores = {"claude": 0, "codex": 0, "gemini": 0}

    if task_type in {"bugfix", "refactor", "coding"}:
        scores["codex"] += 3
    if task_type in {"architecture", "incident", "review"}:
        scores["claude"] += 3
    if task_type in {"migration", "bulk", "automation"}:
        scores["gemini"] += 3

    if urgency == "urgent":
        scores["claude"] += 2
    if volume == "large":
        scores["gemini"] += 2
    if volume == "small":
        scores["codex"] += 1

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    engine = ranked[0][0]
    fallback = ranked[1][0]
    decision = {
        "engine": engine,
        "confidence": round(ranked[0][1] / max(sum(scores.values()), 1), 2),
        "fallback": fallback,
        "reason": f"task_type={task_type}, urgency={urgency}, volume={volume}",
    }
    validate_contract("router-decision", decision)
    return decision
```

```text
# C:\DEV_CORE\Config\ROUTER.md
Urgent architecture or incident -> Claude
Fast coding, bugfix, minimal patch -> Codex
Large migration, bulk transformation, mass automation -> Gemini
Always emit fallback and confidence
Never send automatically without user confirmation
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_router.py -q
```

Expected:

```text
3 passed
```

- [ ] **Step 5: Commit**

```powershell
git -C C:\DEV_CORE add Tools\devcore\router.py Config\ROUTER.md Tests\test_router.py
git -C C:\DEV_CORE commit -m "feat: add explainable engine router"
```

## Task 4: Create Recoverable Session Folders And Memory Review Drafts

**Files:**
- Create: `C:\DEV_CORE\Tools\devcore\session.py`
- Create: `C:\DEV_CORE\Tools\devcore\memory.py`
- Modify: `C:\DEV_CORE\Scripts\sync_obsidian_memory.ps1`
- Test: `C:\DEV_CORE\Tests\test_session_memory.py`

- [ ] **Step 1: Write the failing session and memory tests**

```python
# C:\DEV_CORE\Tests\test_session_memory.py
import json

from devcore.memory import build_memory_draft
from devcore.session import create_session


def test_create_session_writes_request_json(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVCORE_PLATFORM_ROOT", str(tmp_path / "platform"))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(tmp_path / "data"))

    handoff = {
        "handoff_id": "hf_test_002",
        "project_id": "api_python",
        "task_type": "bugfix",
        "target_engine": "codex",
        "intent": "Fix parser regression",
        "context_refs": ["obsidian://08_Bugs/parser.md"],
        "context_summary": "Crash on empty input",
        "constraints": ["patch minimal"],
        "expected_output": "patch + explanation + risks",
        "prepared_at": "2026-04-22T20:00:00Z",
    }

    session_dir = create_session(handoff)
    saved = json.loads((session_dir / "request.json").read_text(encoding="utf-8"))

    assert saved["handoff_id"] == "hf_test_002"


def test_build_memory_draft_creates_pending_review_note(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVCORE_PLATFORM_ROOT", str(tmp_path / "platform"))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(tmp_path / "data"))

    receipt = {
        "handoff_id": "hf_test_002",
        "engine": "codex",
        "status": "completed",
        "artifact_refs": ["file://C:/DEV_CORE_DATA/Sessions/hf_test_002/response.md"],
        "memory_candidates": ["Root cause: missing null guard"],
        "next_action": "review_and_commit",
    }

    draft_path = build_memory_draft(receipt)
    review_path = tmp_path / "data" / "Vault" / "05_AI" / "DEV_CORE" / "Memory Review" / "pending" / "hf_test_002.md"

    assert draft_path.name == "memory-draft.md"
    assert "Root cause: missing null guard" in draft_path.read_text(encoding="utf-8")
    assert review_path.is_file()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_session_memory.py -q
```

Expected:

```text
E   ModuleNotFoundError: No module named 'devcore.memory'
```

- [ ] **Step 3: Implement session persistence and memory review draft creation**

```python
# C:\DEV_CORE\Tools\devcore\session.py
import json

from devcore.contracts import validate_contract
from devcore.paths import get_paths


def create_session(handoff: dict):
    validate_contract("handoff", handoff)
    paths = get_paths()
    session_dir = paths.session_root / handoff["handoff_id"]
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "request.json").write_text(
        json.dumps(handoff, indent=2),
        encoding="utf-8",
    )
    return session_dir


def write_router_decision(session_dir, decision: dict) -> None:
    (session_dir / "router-decision.json").write_text(
        json.dumps(decision, indent=2),
        encoding="utf-8",
    )


def write_receipt(session_dir, receipt: dict) -> None:
    validate_contract("receipt", receipt)
    (session_dir / "receipt.json").write_text(
        json.dumps(receipt, indent=2),
        encoding="utf-8",
    )
```

```python
# C:\DEV_CORE\Tools\devcore\memory.py
import json

from devcore.contracts import validate_contract
from devcore.paths import get_paths


def build_memory_draft(receipt: dict):
    validate_contract("receipt", receipt)
    paths = get_paths()
    content = "\n".join(
        [
            f"# Memory Review - {receipt['handoff_id']}",
            "",
            f"- Engine: {receipt['engine']}",
            f"- Status: {receipt['status']}",
            "",
            "## Candidates",
            *[f"- {item}" for item in receipt["memory_candidates"]],
        ]
    )
    session_dir = paths.session_root / receipt["handoff_id"]
    draft_path = session_dir / "memory-draft.md"
    review_path = paths.memory_review_pending / f"{receipt['handoff_id']}.md"
    draft_path.write_text(content, encoding="utf-8")
    review_path.write_text(content, encoding="utf-8")
    return draft_path


def enqueue_qdrant_refresh(note_path: str) -> None:
    paths = get_paths()
    paths.qdrant_refresh_queue.parent.mkdir(parents=True, exist_ok=True)
    with paths.qdrant_refresh_queue.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"note_path": note_path}) + "\n")
```

```powershell
# C:\DEV_CORE\Scripts\sync_obsidian_memory.ps1
param(
    [Parameter(Mandatory = $true)]
    [string]$SessionId
)

$ErrorActionPreference = 'Stop'
$pending = "C:\DEV_CORE_DATA\Vault\05_AI\DEV_CORE\Memory Review\pending\$SessionId.md"
$approvedDir = "C:\DEV_CORE_DATA\Vault\05_AI\DEV_CORE\Memory Review\approved"
$queuePath = "C:\DEV_CORE_DATA\Memory\qdrant-refresh.jsonl"

New-Item -ItemType Directory -Force -Path $approvedDir | Out-Null
Move-Item -Path $pending -Destination (Join-Path $approvedDir "$SessionId.md") -Force
@{ note_path = (Join-Path $approvedDir "$SessionId.md") } | ConvertTo-Json -Compress | Add-Content -Path $queuePath
Write-Output "Approved memory synced for $SessionId"
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_session_memory.py -q
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Commit**

```powershell
git -C C:\DEV_CORE add Tools\devcore\session.py Tools\devcore\memory.py Scripts\sync_obsidian_memory.ps1 Tests\test_session_memory.py
git -C C:\DEV_CORE commit -m "feat: add session persistence and memory review queue"
```

## Task 5: Add Engine Adapters For Semi-Automatic Prompt Packaging

**Files:**
- Create: `C:\DEV_CORE\Tools\devcore\adapters\__init__.py`
- Create: `C:\DEV_CORE\Tools\devcore\adapters\base.py`
- Create: `C:\DEV_CORE\Tools\devcore\adapters\claude.py`
- Create: `C:\DEV_CORE\Tools\devcore\adapters\codex.py`
- Create: `C:\DEV_CORE\Tools\devcore\adapters\gemini.py`
- Test: `C:\DEV_CORE\Tests\test_adapters.py`

- [ ] **Step 1: Write the failing adapter tests**

```python
# C:\DEV_CORE\Tests\test_adapters.py
from pathlib import Path

from devcore.adapters.codex import CodexAdapter


def test_codex_adapter_writes_prompt_file(tmp_path):
    adapter = CodexAdapter()
    handoff = {
        "handoff_id": "hf_test_003",
        "intent": "Fix parser regression",
        "context_summary": "Crash on empty input",
        "constraints": ["patch minimal"],
        "expected_output": "patch + explanation + risks",
    }

    payload = adapter.prepare(tmp_path, handoff)

    assert Path(payload["prompt_path"]).is_file()
    assert "Fix parser regression" in Path(payload["prompt_path"]).read_text(encoding="utf-8")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_adapters.py -q
```

Expected:

```text
E   ModuleNotFoundError: No module named 'devcore.adapters'
```

- [ ] **Step 3: Implement the base adapter and three engine-specific packagers**

```python
# C:\DEV_CORE\Tools\devcore\adapters\__init__.py
from devcore.adapters.claude import ClaudeAdapter
from devcore.adapters.codex import CodexAdapter
from devcore.adapters.gemini import GeminiAdapter

__all__ = ["ClaudeAdapter", "CodexAdapter", "GeminiAdapter"]
```

```python
# C:\DEV_CORE\Tools\devcore\adapters\base.py
class BaseAdapter:
    engine_name = "base"

    def build_prompt(self, handoff: dict) -> str:
        constraints = "\n".join(f"- {item}" for item in handoff["constraints"])
        return "\n".join(
            [
                f"# Engine: {self.engine_name}",
                "",
                f"Intent: {handoff['intent']}",
                f"Context: {handoff['context_summary']}",
                "",
                "Constraints:",
                constraints,
                "",
                f"Expected output: {handoff['expected_output']}",
            ]
        )

    def prepare(self, session_dir, handoff: dict) -> dict:
        prompt_path = session_dir / f"{self.engine_name}-prompt.md"
        prompt_path.write_text(self.build_prompt(handoff), encoding="utf-8")
        return {
            "engine": self.engine_name,
            "prompt_path": str(prompt_path),
            "launch_hint": f'Open {prompt_path} in {self.engine_name}',
        }
```

```python
# C:\DEV_CORE\Tools\devcore\adapters\claude.py
from devcore.adapters.base import BaseAdapter


class ClaudeAdapter(BaseAdapter):
    engine_name = "claude"
```

```python
# C:\DEV_CORE\Tools\devcore\adapters\codex.py
from devcore.adapters.base import BaseAdapter


class CodexAdapter(BaseAdapter):
    engine_name = "codex"
```

```python
# C:\DEV_CORE\Tools\devcore\adapters\gemini.py
from devcore.adapters.base import BaseAdapter


class GeminiAdapter(BaseAdapter):
    engine_name = "gemini"
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_adapters.py -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Commit**

```powershell
git -C C:\DEV_CORE add Tools\devcore\adapters\__init__.py Tools\devcore\adapters\base.py Tools\devcore\adapters\claude.py Tools\devcore\adapters\codex.py Tools\devcore\adapters\gemini.py Tests\test_adapters.py
git -C C:\DEV_CORE commit -m "feat: add semi-automatic engine adapters"
```

## Task 6: Wire The CLI And PowerShell Entry Point End-To-End

**Files:**
- Create: `C:\DEV_CORE\Tools\devcore\cli.py`
- Modify: `C:\DEV_CORE\Scripts\launch.ps1`
- Modify: `C:\DEV_CORE\Config\BOOT.md`
- Test: `C:\DEV_CORE\Tests\test_cli_smoke.py`

- [ ] **Step 1: Write the failing end-to-end smoke test**

```python
# C:\DEV_CORE\Tests\test_cli_smoke.py
import json

from devcore.cli import build_prepare_payload


def test_build_prepare_payload_creates_router_decision_and_adapter_payload(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVCORE_PLATFORM_ROOT", str(tmp_path / "platform"))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(tmp_path / "data"))

    result = build_prepare_payload(
        project_id="android_tooling",
        task_type="bugfix",
        urgency="normal",
        volume="small",
        intent="Fix parser regression",
        context_summary="Crash on empty input",
        context_refs=["obsidian://08_Bugs/parser.md"],
        constraints=["patch minimal"],
        expected_output="patch + explanation + risks",
    )

    assert result["engine"] == "codex"
    assert result["session_dir"].endswith("hf_android_tooling_bugfix")
    decision = json.loads((tmp_path / "data" / "Sessions" / "hf_android_tooling_bugfix" / "router-decision.json").read_text(encoding="utf-8"))
    assert decision["engine"] == "codex"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_cli_smoke.py -q
```

Expected:

```text
E   ModuleNotFoundError: No module named 'devcore.cli'
```

- [ ] **Step 3: Implement the CLI prepare flow and thin launcher wrapper**

```python
# C:\DEV_CORE\Tools\devcore\cli.py
import argparse
import json

from devcore.adapters import ClaudeAdapter, CodexAdapter, GeminiAdapter
from devcore.router import recommend_engine
from devcore.session import create_session, write_router_decision


ADAPTERS = {
    "claude": ClaudeAdapter(),
    "codex": CodexAdapter(),
    "gemini": GeminiAdapter(),
}


def build_prepare_payload(
    project_id: str,
    task_type: str,
    urgency: str,
    volume: str,
    intent: str,
    context_summary: str,
    context_refs: list[str],
    constraints: list[str],
    expected_output: str,
) -> dict:
    handoff_id = f"hf_{project_id}_{task_type}"
    decision = recommend_engine(task_type=task_type, urgency=urgency, volume=volume)
    handoff = {
        "handoff_id": handoff_id,
        "project_id": project_id,
        "task_type": task_type,
        "target_engine": decision["engine"],
        "intent": intent,
        "context_refs": context_refs,
        "context_summary": context_summary,
        "constraints": constraints,
        "expected_output": expected_output,
        "prepared_at": "2026-04-22T20:00:00Z",
    }
    session_dir = create_session(handoff)
    write_router_decision(session_dir, decision)
    adapter_payload = ADAPTERS[decision["engine"]].prepare(session_dir, handoff)
    (session_dir / "adapter-payload.json").write_text(
        json.dumps(adapter_payload, indent=2),
        encoding="utf-8",
    )
    return {
        "handoff_id": handoff_id,
        "engine": decision["engine"],
        "session_dir": str(session_dir),
        "prompt_path": adapter_payload["prompt_path"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--task-type", required=True)
    parser.add_argument("--urgency", default="normal")
    parser.add_argument("--volume", default="small")
    parser.add_argument("--intent", required=True)
    parser.add_argument("--context-summary", required=True)
    parser.add_argument("--context-ref", action="append", default=[])
    parser.add_argument("--constraint", action="append", default=[])
    parser.add_argument("--expected-output", required=True)
    args = parser.parse_args()

    payload = build_prepare_payload(
        project_id=args.project_id,
        task_type=args.task_type,
        urgency=args.urgency,
        volume=args.volume,
        intent=args.intent,
        context_summary=args.context_summary,
        context_refs=args.context_ref,
        constraints=args.constraint,
        expected_output=args.expected_output,
    )
    print(json.dumps(payload))


if __name__ == "__main__":
    main()
```

```powershell
# C:\DEV_CORE\Scripts\launch.ps1
param(
    [string]$ProjectId = "default",
    [string]$TaskType = "bugfix",
    [string]$Urgency = "normal",
    [string]$Volume = "small",
    [Parameter(Mandatory = $true)]
    [string]$Intent,
    [Parameter(Mandatory = $true)]
    [string]$ContextSummary
)

$ErrorActionPreference = 'Stop'
Set-Location C:\DEV_CORE
$env:PYTHONPATH = "C:\DEV_CORE\Tools"

python -m devcore.cli `
  --project-id $ProjectId `
  --task-type $TaskType `
  --urgency $Urgency `
  --volume $Volume `
  --intent $Intent `
  --context-summary $ContextSummary `
  --constraint "human confirmation required" `
  --expected-output "patch + explanation + risks"
```

```text
# C:\DEV_CORE\Config\BOOT.md
Load canonical Windows paths from devcore.paths
Use the explainable router before any handoff
Prepare session folder and adapter payload on disk
Require human confirmation before sending to any engine
```

- [ ] **Step 4: Run all tests and one manual smoke command**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests -q
python -m devcore.cli --project-id android_tooling --task-type bugfix --intent "Fix parser regression" --context-summary "Crash on empty input" --context-ref "obsidian://08_Bugs/parser.md" --constraint "patch minimal" --expected-output "patch + explanation + risks"
```

Expected:

```text
10 passed
JSON output includes handoff_id, engine, session_dir, and prompt_path
```

- [ ] **Step 5: Commit**

```powershell
git -C C:\DEV_CORE add Tools\devcore\cli.py Scripts\launch.ps1 Config\BOOT.md Tests\test_cli_smoke.py
git -C C:\DEV_CORE commit -m "feat: wire end-to-end prepare flow"
```

## Definition Of Done For Slice 1

- `python -m pytest Tests -q` passes from `C:\DEV_CORE`
- `Scripts\launch.ps1` creates a recoverable session directory
- the session directory contains `request.json`, `router-decision.json`, and `adapter-payload.json`
- adapter prompt packaging exists for `Claude`, `Codex`, and `Gemini`
- memory review drafts can be approved into the vault and queued for Qdrant refresh
- no hidden send occurs; the user still confirms the final engine handoff

## Follow-Up Plans Required

After Slice 1 lands, write separate implementation plans for:

1. real dashboard and session observability
2. Windows event watchers and auto-reaction
3. Qdrant indexer worker and retrieval ranking
4. richer project-aware memory extraction and scoring

## Self-Review

### Spec Coverage

Covered in this plan:

- routing contracts
- no permanent central engine
- session durability
- memory review queue
- Obsidian-first workflow
- Qdrant refresh queue
- semi-automatic handoff preparation

Intentionally deferred:

- dashboard UI
- live watchers
- advanced analytics
- autonomous planning loops

### Placeholder Scan

No `TODO`, `TBD`, or deferred code placeholders are used inside implementation steps.

### Type Consistency

The plan uses the same stable names throughout:

- `handoff_id`
- `router-decision.json`
- `adapter-payload.json`
- `memory review`
- `qdrant-refresh.jsonl`
