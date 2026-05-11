# DEV_CORE Memory Sync And Qdrant Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the DEV_CORE Memory Fabric by making approved memory promotion, Obsidian canonical storage, and Qdrant refresh queueing deterministic and testable.

**Architecture:** This slice keeps `Obsidian` as the canonical source of truth and treats `Qdrant` as a derived rebuildable index. The implementation adds a narrow memory sync module that promotes reviewed notes, appends structured refresh jobs, writes rebuild manifests, and updates the existing PowerShell script to use the same Python-backed logic instead of duplicating path rules.

**Tech Stack:** Python 3.11+, `pytest`, Markdown, JSONL, PowerShell 7, existing `devcore` package, local filesystem contracts on Windows

---

## Scope Split

This plan covers only the first reliable memory sync and Qdrant refresh foundation.

Covered:

- approved memory note promotion
- canonical Obsidian target paths
- structured Qdrant refresh queue jobs
- rebuild manifest generation
- PowerShell sync wrapper alignment
- tests for sync and queue behavior

Deferred:

- real Qdrant HTTP/API indexing
- embeddings generation
- semantic retrieval ranking
- dashboard exposure
- automatic memory promotion without review

## File Structure

### Platform files

- Modify: `C:\DEV_CORE\Tools\devcore\paths.py`
- Modify: `C:\DEV_CORE\Tools\devcore\memory.py`
- Create: `C:\DEV_CORE\Tools\devcore\memory_sync.py`
- Create: `C:\DEV_CORE\Tools\devcore\qdrant_queue.py`
- Modify: `C:\DEV_CORE\Scripts\sync_obsidian_memory.ps1`

### Tests

- Create: `C:\DEV_CORE\Tests\test_memory_sync.py`
- Create: `C:\DEV_CORE\Tests\test_qdrant_queue.py`
- Modify: `C:\DEV_CORE\Tests\test_session_memory.py`

### Responsibility map

- `paths.py`: expose canonical memory notes root and Qdrant manifest path
- `memory.py`: keep memory draft creation and delegate structured queue writes
- `memory_sync.py`: promote reviewed notes into approved/canonical Obsidian memory
- `qdrant_queue.py`: append refresh jobs and write rebuild manifests
- `sync_obsidian_memory.ps1`: thin wrapper around the Python sync implementation
- `test_memory_sync.py`: promotion and canonical Obsidian behavior
- `test_qdrant_queue.py`: queue and rebuild manifest behavior
- `test_session_memory.py`: existing draft behavior remains compatible

## Task 1: Add Canonical Memory Fabric Paths

**Files:**
- Modify: `C:\DEV_CORE\Tools\devcore\paths.py`
- Create: `C:\DEV_CORE\Tests\test_memory_sync.py`

- [ ] **Step 1: Write the failing path test**

```python
# C:\DEV_CORE\Tests\test_memory_sync.py
from pathlib import Path

from devcore.paths import get_paths


def test_get_paths_exposes_canonical_memory_and_qdrant_manifest(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVCORE_PLATFORM_ROOT", str(tmp_path / "platform"))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(tmp_path / "data"))

    paths = get_paths()

    assert paths.canonical_memory_root == Path(tmp_path / "data" / "Vault" / "05_AI" / "DEV_CORE" / "Memory")
    assert paths.qdrant_rebuild_manifest == Path(tmp_path / "data" / "Memory" / "qdrant-rebuild-manifest.json")
    assert paths.canonical_memory_root.is_dir()
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_memory_sync.py -q
```

Expected:

```text
E   AttributeError: 'DevCorePaths' object has no attribute 'canonical_memory_root'
```

- [ ] **Step 3: Extend the path model**

```python
# C:\DEV_CORE\Tools\devcore\paths.py
from __future__ import annotations

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
    canonical_memory_root: Path
    qdrant_refresh_queue: Path
    qdrant_rebuild_manifest: Path
    schema_root: Path
    router_log_root: Path
    scoring_log_root: Path


def _canonicalize_root(path_value: str) -> Path:
    return Path(os.path.abspath(os.path.normpath(os.path.expanduser(path_value))))


def get_paths() -> DevCorePaths:
    platform_root = _canonicalize_root(
        os.environ.get("DEVCORE_PLATFORM_ROOT", r"C:\DEV_CORE")
    )
    data_root = _canonicalize_root(
        os.environ.get("DEVCORE_DATA_ROOT", r"C:\DEV_CORE_DATA")
    )

    bus_root = platform_root / "Bus"
    session_root = data_root / "Sessions"
    vault_root = data_root / "Vault"
    memory_root = data_root / "Memory"
    schema_root = platform_root / "Schemas"
    logs_root = data_root / "Logs"
    router_log_root = logs_root / "router"
    scoring_log_root = logs_root / "scoring"
    qdrant_refresh_queue = memory_root / "qdrant-refresh.jsonl"
    qdrant_rebuild_manifest = memory_root / "qdrant-rebuild-manifest.json"
    memory_review_pending = (
        vault_root / "05_AI" / "DEV_CORE" / "Memory Review" / "pending"
    )
    memory_review_approved = (
        vault_root / "05_AI" / "DEV_CORE" / "Memory Review" / "approved"
    )
    canonical_memory_root = vault_root / "05_AI" / "DEV_CORE" / "Memory"

    for directory in (
        bus_root / "drafts",
        bus_root / "receipts",
        bus_root / "archive",
        session_root,
        memory_root,
        memory_review_pending,
        memory_review_approved,
        canonical_memory_root,
        schema_root,
        router_log_root,
        scoring_log_root,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    return DevCorePaths(
        platform_root=platform_root,
        data_root=data_root,
        bus_root=bus_root,
        session_root=session_root,
        vault_root=vault_root,
        memory_root=memory_root,
        memory_review_pending=memory_review_pending,
        memory_review_approved=memory_review_approved,
        canonical_memory_root=canonical_memory_root,
        qdrant_refresh_queue=qdrant_refresh_queue,
        qdrant_rebuild_manifest=qdrant_rebuild_manifest,
        schema_root=schema_root,
        router_log_root=router_log_root,
        scoring_log_root=scoring_log_root,
    )
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_memory_sync.py -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Commit**

```powershell
git -C C:\DEV_CORE add Tools\devcore\paths.py Tests\test_memory_sync.py
git -C C:\DEV_CORE commit -m "feat: add canonical memory fabric paths"
```

## Task 2: Promote Approved Memory Into Canonical Obsidian Notes

**Files:**
- Modify: `C:\DEV_CORE\Tests\test_memory_sync.py`
- Create: `C:\DEV_CORE\Tools\devcore\memory_sync.py`

- [ ] **Step 1: Extend the memory sync test with approved-note promotion**

```python
# append to C:\DEV_CORE\Tests\test_memory_sync.py
from devcore.memory_sync import promote_approved_memory


def test_promote_approved_memory_moves_pending_note_to_approved_and_canonical(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVCORE_PLATFORM_ROOT", str(tmp_path / "platform"))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(tmp_path / "data"))
    paths = get_paths()
    pending = paths.memory_review_pending / "hf_test_001.md"
    pending.write_text("# Memory Review - hf_test_001\n\n## Candidates\n- Stable lesson", encoding="utf-8")

    result = promote_approved_memory("hf_test_001")

    assert result["approved_path"] == paths.memory_review_approved / "hf_test_001.md"
    assert result["canonical_path"] == paths.canonical_memory_root / "hf_test_001.md"
    assert result["approved_path"].is_file()
    assert result["canonical_path"].is_file()
    assert not pending.exists()
    assert "Stable lesson" in result["canonical_path"].read_text(encoding="utf-8")
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_memory_sync.py -q
```

Expected:

```text
E   ModuleNotFoundError: No module named 'devcore.memory_sync'
```

- [ ] **Step 3: Implement approved memory promotion**

```python
# C:\DEV_CORE\Tools\devcore\memory_sync.py
from pathlib import Path

from devcore.paths import get_paths


def promote_approved_memory(session_id: str) -> dict:
    paths = get_paths()
    pending_path = paths.memory_review_pending / f"{session_id}.md"
    approved_path = paths.memory_review_approved / f"{session_id}.md"
    canonical_path = paths.canonical_memory_root / f"{session_id}.md"

    if not pending_path.exists():
        raise FileNotFoundError(str(pending_path))

    content = pending_path.read_text(encoding="utf-8")
    approved_path.write_text(content, encoding="utf-8")
    canonical_path.write_text(content, encoding="utf-8")
    pending_path.unlink()

    return {
        "session_id": session_id,
        "approved_path": approved_path,
        "canonical_path": canonical_path,
    }
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_memory_sync.py -q
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Commit**

```powershell
git -C C:\DEV_CORE add Tools\devcore\memory_sync.py Tests\test_memory_sync.py
git -C C:\DEV_CORE commit -m "feat: promote approved memory into canonical vault"
```

## Task 3: Write Structured Qdrant Refresh Queue Jobs

**Files:**
- Create: `C:\DEV_CORE\Tests\test_qdrant_queue.py`
- Create: `C:\DEV_CORE\Tools\devcore\qdrant_queue.py`
- Modify: `C:\DEV_CORE\Tools\devcore\memory.py`

- [ ] **Step 1: Write the failing Qdrant queue test**

```python
# C:\DEV_CORE\Tests\test_qdrant_queue.py
import json

from devcore.qdrant_queue import enqueue_refresh_job


def test_enqueue_refresh_job_writes_structured_jsonl(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVCORE_PLATFORM_ROOT", str(tmp_path / "platform"))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(tmp_path / "data"))

    queue_path = enqueue_refresh_job(
        note_path="C:/DEV_CORE_DATA/Vault/05_AI/DEV_CORE/Memory/hf_test_001.md",
        source="memory_sync",
        reason="approved_memory",
    )

    payload = json.loads(queue_path.read_text(encoding="utf-8").splitlines()[0])

    assert queue_path.name == "qdrant-refresh.jsonl"
    assert payload["note_path"].endswith("hf_test_001.md")
    assert payload["source"] == "memory_sync"
    assert payload["reason"] == "approved_memory"
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_qdrant_queue.py -q
```

Expected:

```text
E   ModuleNotFoundError: No module named 'devcore.qdrant_queue'
```

- [ ] **Step 3: Implement the structured queue writer and delegate existing memory helper**

```python
# C:\DEV_CORE\Tools\devcore\qdrant_queue.py
import json
from datetime import datetime, timezone
from pathlib import Path

from devcore.paths import get_paths


def enqueue_refresh_job(note_path: str, source: str, reason: str) -> Path:
    payload = {
        "note_path": note_path,
        "source": source,
        "reason": reason,
        "queued_at": datetime.now(timezone.utc).isoformat(),
    }
    queue_path = get_paths().qdrant_refresh_queue
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    with queue_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")
    return queue_path
```

```python
# C:\DEV_CORE\Tools\devcore\memory.py
from devcore.contracts import validate_contract
from devcore.paths import get_paths
from devcore.qdrant_queue import enqueue_refresh_job


def enqueue_qdrant_refresh(note_path: str) -> None:
    enqueue_refresh_job(
        note_path=note_path,
        source="memory",
        reason="manual_refresh",
    )
```

- [ ] **Step 4: Run the queue and existing memory tests**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_qdrant_queue.py Tests\test_session_memory.py -q
```

Expected:

```text
All focused tests pass
```

- [ ] **Step 5: Commit**

```powershell
git -C C:\DEV_CORE add Tools\devcore\qdrant_queue.py Tools\devcore\memory.py Tests\test_qdrant_queue.py
git -C C:\DEV_CORE commit -m "feat: add structured qdrant refresh queue"
```

## Task 4: Queue Approved Memory For Qdrant And Write Rebuild Manifest

**Files:**
- Modify: `C:\DEV_CORE\Tests\test_memory_sync.py`
- Modify: `C:\DEV_CORE\Tests\test_qdrant_queue.py`
- Modify: `C:\DEV_CORE\Tools\devcore\memory_sync.py`
- Modify: `C:\DEV_CORE\Tools\devcore\qdrant_queue.py`

- [ ] **Step 1: Extend memory sync test to verify queueing after promotion**

```python
# append to C:\DEV_CORE\Tests\test_memory_sync.py
import json


def test_promote_approved_memory_queues_canonical_note_for_qdrant(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVCORE_PLATFORM_ROOT", str(tmp_path / "platform"))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(tmp_path / "data"))
    paths = get_paths()
    pending = paths.memory_review_pending / "hf_test_002.md"
    pending.write_text("# Memory Review - hf_test_002\n\n## Candidates\n- Searchable lesson", encoding="utf-8")

    result = promote_approved_memory("hf_test_002")

    payload = json.loads(paths.qdrant_refresh_queue.read_text(encoding="utf-8").splitlines()[0])
    assert payload["note_path"] == str(result["canonical_path"])
    assert payload["reason"] == "approved_memory"
```

```python
# append to C:\DEV_CORE\Tests\test_qdrant_queue.py
from devcore.qdrant_queue import write_rebuild_manifest


def test_write_rebuild_manifest_lists_canonical_memory_notes(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVCORE_PLATFORM_ROOT", str(tmp_path / "platform"))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(tmp_path / "data"))
    paths = get_paths()
    note = paths.canonical_memory_root / "hf_test_001.md"
    note.write_text("# Canonical Memory", encoding="utf-8")

    manifest_path = write_rebuild_manifest()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest_path == paths.qdrant_rebuild_manifest
    assert str(note) in payload["note_paths"]
```

- [ ] **Step 2: Run focused tests to verify they fail**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_memory_sync.py Tests\test_qdrant_queue.py -q
```

Expected:

```text
FAIL because promotion does not queue approved notes and write_rebuild_manifest does not exist
```

- [ ] **Step 3: Queue promoted canonical notes and add rebuild manifest writer**

```python
# C:\DEV_CORE\Tools\devcore\memory_sync.py
from devcore.qdrant_queue import enqueue_refresh_job


def promote_approved_memory(session_id: str) -> dict:
    paths = get_paths()
    pending_path = paths.memory_review_pending / f"{session_id}.md"
    approved_path = paths.memory_review_approved / f"{session_id}.md"
    canonical_path = paths.canonical_memory_root / f"{session_id}.md"

    if not pending_path.exists():
        raise FileNotFoundError(str(pending_path))

    content = pending_path.read_text(encoding="utf-8")
    approved_path.write_text(content, encoding="utf-8")
    canonical_path.write_text(content, encoding="utf-8")
    pending_path.unlink()
    enqueue_refresh_job(
        note_path=str(canonical_path),
        source="memory_sync",
        reason="approved_memory",
    )

    return {
        "session_id": session_id,
        "approved_path": approved_path,
        "canonical_path": canonical_path,
    }
```

```python
# append to C:\DEV_CORE\Tools\devcore\qdrant_queue.py
def write_rebuild_manifest() -> Path:
    paths = get_paths()
    note_paths = sorted(str(path) for path in paths.canonical_memory_root.glob("*.md"))
    payload = {
        "source_root": str(paths.canonical_memory_root),
        "note_paths": note_paths,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    paths.qdrant_rebuild_manifest.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )
    return paths.qdrant_rebuild_manifest
```

- [ ] **Step 4: Run focused tests and full suite**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_memory_sync.py Tests\test_qdrant_queue.py -q
python -m pytest Tests -q
```

Expected:

```text
All focused tests pass
All tests pass
```

- [ ] **Step 5: Commit**

```powershell
git -C C:\DEV_CORE add Tools\devcore\memory_sync.py Tools\devcore\qdrant_queue.py Tests\test_memory_sync.py Tests\test_qdrant_queue.py
git -C C:\DEV_CORE commit -m "feat: queue approved memory for qdrant refresh"
```

## Task 5: Align PowerShell Sync With Python Memory Sync

**Files:**
- Modify: `C:\DEV_CORE\Scripts\sync_obsidian_memory.ps1`
- Modify: `C:\DEV_CORE\Tests\test_memory_sync.py`

- [ ] **Step 1: Add a Python smoke helper test for the script-equivalent flow**

```python
# append to C:\DEV_CORE\Tests\test_memory_sync.py
def test_promote_approved_memory_returns_paths_for_script_output(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVCORE_PLATFORM_ROOT", str(tmp_path / "platform"))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(tmp_path / "data"))
    paths = get_paths()
    pending = paths.memory_review_pending / "hf_script_001.md"
    pending.write_text("# Memory Review - hf_script_001\n\n## Candidates\n- Script-safe lesson", encoding="utf-8")

    result = promote_approved_memory("hf_script_001")

    assert result["session_id"] == "hf_script_001"
    assert result["canonical_path"].name == "hf_script_001.md"
    assert paths.qdrant_refresh_queue.is_file()
```

- [ ] **Step 2: Run memory sync tests to verify current Python flow still passes**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_memory_sync.py -q
```

Expected:

```text
All memory sync tests pass
```

- [ ] **Step 3: Replace PowerShell path duplication with Python-backed sync**

```powershell
# C:\DEV_CORE\Scripts\sync_obsidian_memory.ps1
param(
    [Parameter(Mandatory = $true)]
    [string]$SessionId
)

$ErrorActionPreference = 'Stop'
$platformRoot = Split-Path $PSScriptRoot -Parent
Set-Location $platformRoot
$env:PYTHONPATH = (Join-Path $platformRoot "Tools")
$env:DEVCORE_SYNC_SESSION_ID = $SessionId

python -c "import json, os; from devcore.memory_sync import promote_approved_memory; result = promote_approved_memory(os.environ['DEVCORE_SYNC_SESSION_ID']); print(json.dumps({k: str(v) for k, v in result.items()}))"
```

- [ ] **Step 4: Run full suite and manual script smoke**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests -q
$env:DEVCORE_PLATFORM_ROOT = "C:\DEV_CORE"
$env:DEVCORE_DATA_ROOT = "$env:TEMP\devcore-memory-sync-smoke"
python -c "from devcore.paths import get_paths; p=get_paths(); (p.memory_review_pending / 'hf_script_smoke.md').write_text('# Memory Review - hf_script_smoke', encoding='utf-8')"
.\Scripts\sync_obsidian_memory.ps1 -SessionId hf_script_smoke
```

Expected:

```text
All tests pass
Script prints JSON containing session_id, approved_path, and canonical_path
```

- [ ] **Step 5: Commit**

```powershell
git -C C:\DEV_CORE add Scripts\sync_obsidian_memory.ps1 Tests\test_memory_sync.py
git -C C:\DEV_CORE commit -m "feat: align obsidian memory sync script with python runtime"
```

## Definition Of Done

- approved memory is promoted from pending review into approved review and canonical Obsidian memory
- Qdrant refresh queue entries are structured JSONL jobs
- promoted canonical notes are automatically queued for refresh
- a rebuild manifest can be generated from canonical memory notes
- `sync_obsidian_memory.ps1` delegates to the Python memory sync runtime
- `python -m pytest Tests -q` passes from `C:\DEV_CORE`

## Follow-Up Plans Required

After this slice lands, separate plans should cover:

1. real Qdrant indexing worker
2. embedding provider selection and configuration
3. retrieval ranking and context-builder integration
4. memory quality scoring integration with telemetry

## Self-Review

### Spec Coverage

Covered:

- Obsidian as canonical source
- Qdrant as derived rebuildable index
- approved memory promotion
- structured refresh queue
- rebuild manifest
- PowerShell wrapper alignment

Deferred:

- actual vector ingestion
- embedding generation
- semantic retrieval ranking
- autonomous memory promotion

### Placeholder Scan

No implementation steps contain `TODO`, `TBD`, or placeholder action language.

### Type Consistency

Stable names are used consistently:

- `promote_approved_memory`
- `enqueue_refresh_job`
- `write_rebuild_manifest`
- `canonical_memory_root`
- `qdrant_refresh_queue`
- `qdrant_rebuild_manifest`
