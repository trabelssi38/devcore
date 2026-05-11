# DEV_CORE Router Telemetry And Scoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first learning-layer slice for DEV_CORE by durably recording router decisions, execution outcomes, and prompt-scoring signals without changing canonical memory.

**Architecture:** This slice extends the existing control plane rather than replacing it. The implementation adds a telemetry store under `C:\DEV_CORE_DATA\Logs`, writes append-only JSONL artifacts for prepare and outcome events, computes lightweight prompt and engine scores from those events, and exposes narrow helpers that future predictive routing can consume without rewriting current router or session contracts.

**Tech Stack:** Python 3.11+, `pytest`, JSON, JSONL, existing `devcore` package, local filesystem contracts on Windows

---

## Scope Split

This plan covers only the first working telemetry and scoring foundation.

Covered:

- append-only router decision log
- append-only session outcome log
- narrow telemetry helper APIs
- prompt score aggregation
- engine effectiveness aggregation
- persistence under the canonical logs root

Deferred:

- predictive router consumption
- UI/dashboard visualizations
- Obsidian memory promotion from telemetry
- automated scoring-based engine overrides

## File Structure

### Platform files

- Modify: `C:\DEV_CORE\Tools\devcore\paths.py`
- Create: `C:\DEV_CORE\Tools\devcore\telemetry.py`
- Create: `C:\DEV_CORE\Tools\devcore\scoring.py`
- Modify: `C:\DEV_CORE\Tools\devcore\session.py`
- Modify: `C:\DEV_CORE\Tools\devcore\cli.py`

### Tests

- Create: `C:\DEV_CORE\Tests\test_telemetry.py`
- Create: `C:\DEV_CORE\Tests\test_scoring.py`
- Modify: `C:\DEV_CORE\Tests\test_cli_smoke.py`

### Responsibility map

- `paths.py`: canonical log roots for router telemetry and scoring artifacts
- `telemetry.py`: append-only event writers and read helpers
- `scoring.py`: score aggregation from telemetry events
- `session.py`: optional session outcome write helper
- `cli.py`: emit prepare telemetry during existing prepare flow
- `test_telemetry.py`: persistence and payload-shape coverage
- `test_scoring.py`: deterministic score aggregation coverage
- `test_cli_smoke.py`: verify prepare flow now writes telemetry

## Task 1: Extend Canonical Paths For Learning-Layer Logs

**Files:**
- Modify: `C:\DEV_CORE\Tools\devcore\paths.py`
- Create: `C:\DEV_CORE\Tests\test_telemetry.py`

- [ ] **Step 1: Write the failing telemetry path bootstrap test**

```python
# C:\DEV_CORE\Tests\test_telemetry.py
from pathlib import Path

from devcore.paths import get_paths


def test_get_paths_exposes_router_and_scoring_log_roots(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVCORE_PLATFORM_ROOT", str(tmp_path / "platform"))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(tmp_path / "data"))

    paths = get_paths()

    assert paths.router_log_root == Path(tmp_path / "data" / "Logs" / "router")
    assert paths.scoring_log_root == Path(tmp_path / "data" / "Logs" / "scoring")
    assert paths.router_log_root.is_dir()
    assert paths.scoring_log_root.is_dir()
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_telemetry.py -q
```

Expected:

```text
E   AttributeError: 'DevCorePaths' object has no attribute 'router_log_root'
```

- [ ] **Step 3: Add the minimal log roots to the path model**

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
    qdrant_refresh_queue: Path
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
    memory_review_pending = (
        vault_root / "05_AI" / "DEV_CORE" / "Memory Review" / "pending"
    )
    memory_review_approved = (
        vault_root / "05_AI" / "DEV_CORE" / "Memory Review" / "approved"
    )

    for directory in (
        bus_root / "drafts",
        bus_root / "receipts",
        bus_root / "archive",
        session_root,
        memory_root,
        memory_review_pending,
        memory_review_approved,
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
        qdrant_refresh_queue=qdrant_refresh_queue,
        schema_root=schema_root,
        router_log_root=router_log_root,
        scoring_log_root=scoring_log_root,
    )
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_telemetry.py -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Commit**

```powershell
git -C C:\DEV_CORE add Tools\devcore\paths.py Tests\test_telemetry.py
git -C C:\DEV_CORE commit -m "feat: add canonical telemetry log roots"
```

## Task 2: Persist Prepare Telemetry As Append-Only JSONL

**Files:**
- Modify: `C:\DEV_CORE\Tests\test_telemetry.py`
- Create: `C:\DEV_CORE\Tools\devcore\telemetry.py`
- Modify: `C:\DEV_CORE\Tools\devcore\cli.py`

- [ ] **Step 1: Extend telemetry tests with a prepare event writer**

```python
# append to C:\DEV_CORE\Tests\test_telemetry.py
import json

from devcore.telemetry import log_prepare_event


def test_log_prepare_event_appends_router_decision_jsonl(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVCORE_PLATFORM_ROOT", str(tmp_path / "platform"))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(tmp_path / "data"))

    log_path = log_prepare_event(
        {
            "handoff_id": "hf_android_tooling_bugfix",
            "project_id": "android_tooling",
            "task_type": "bugfix",
            "engine": "codex",
            "fallback": "claude",
            "confidence": 0.57,
            "reason": "task_type=bugfix, urgency=normal, volume=small",
            "prompt_pattern": "patch + explanation + risks",
        }
    )

    lines = log_path.read_text(encoding="utf-8").splitlines()
    payload = json.loads(lines[0])

    assert log_path.name == "prepare-events.jsonl"
    assert payload["engine"] == "codex"
    assert payload["task_type"] == "bugfix"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_telemetry.py -q
```

Expected:

```text
E   ModuleNotFoundError: No module named 'devcore.telemetry'
```

- [ ] **Step 3: Implement the append-only prepare event writer**

```python
# C:\DEV_CORE\Tools\devcore\telemetry.py
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from devcore.paths import get_paths


def _append_jsonl(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")
    return path


def log_prepare_event(event: dict) -> Path:
    payload = {
        **event,
        "event_type": "prepare",
        "logged_at": datetime.now(timezone.utc).isoformat(),
    }
    return _append_jsonl(get_paths().router_log_root / "prepare-events.jsonl", payload)
```

```python
# append inside C:\DEV_CORE\Tools\devcore\cli.py
from devcore.telemetry import log_prepare_event
```

```python
# replace return assembly area inside build_prepare_payload in C:\DEV_CORE\Tools\devcore\cli.py
    prepare_event = {
        "handoff_id": handoff_id,
        "project_id": project_id,
        "task_type": task_type,
        "engine": decision["engine"],
        "fallback": decision["fallback"],
        "confidence": decision["confidence"],
        "reason": decision["reason"],
        "prompt_pattern": expected_output,
    }
    log_prepare_event(prepare_event)
    return {
        "handoff_id": handoff_id,
        "engine": decision["engine"],
        "session_dir": str(session_dir),
        "prompt_path": adapter_payload["prompt_path"],
    }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_telemetry.py -q
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Commit**

```powershell
git -C C:\DEV_CORE add Tools\devcore\telemetry.py Tools\devcore\cli.py Tests\test_telemetry.py
git -C C:\DEV_CORE commit -m "feat: log router prepare telemetry"
```

## Task 3: Record Session Outcomes Without Touching Canonical Memory

**Files:**
- Modify: `C:\DEV_CORE\Tests\test_telemetry.py`
- Modify: `C:\DEV_CORE\Tools\devcore\session.py`
- Modify: `C:\DEV_CORE\Tools\devcore\telemetry.py`

- [ ] **Step 1: Extend telemetry tests with an outcome event**

```python
# append to C:\DEV_CORE\Tests\test_telemetry.py
from devcore.telemetry import log_outcome_event


def test_log_outcome_event_appends_session_result(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVCORE_PLATFORM_ROOT", str(tmp_path / "platform"))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(tmp_path / "data"))

    log_path = log_outcome_event(
        {
            "handoff_id": "hf_android_tooling_bugfix",
            "task_type": "bugfix",
            "engine": "codex",
            "status": "completed",
            "rework": False,
            "prompt_pattern": "patch + explanation + risks",
        }
    )

    payload = json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])
    assert log_path.name == "outcome-events.jsonl"
    assert payload["status"] == "completed"
    assert payload["rework"] is False
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_telemetry.py -q
```

Expected:

```text
E   ImportError: cannot import name 'log_outcome_event'
```

- [ ] **Step 3: Add the outcome event writer and a narrow session helper**

```python
# append to C:\DEV_CORE\Tools\devcore\telemetry.py
def log_outcome_event(event: dict) -> Path:
    payload = {
        **event,
        "event_type": "outcome",
        "logged_at": datetime.now(timezone.utc).isoformat(),
    }
    return _append_jsonl(get_paths().router_log_root / "outcome-events.jsonl", payload)
```

```python
# append to C:\DEV_CORE\Tools\devcore\session.py
import json

from devcore.telemetry import log_outcome_event
```

```python
# append to C:\DEV_CORE\Tools\devcore\session.py
def write_outcome(session_dir, outcome: dict) -> None:
    (session_dir / "outcome.json").write_text(
        json.dumps(outcome, indent=2),
        encoding="utf-8",
    )
    log_outcome_event(outcome)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_telemetry.py -q
```

Expected:

```text
3 passed
```

- [ ] **Step 5: Commit**

```powershell
git -C C:\DEV_CORE add Tools\devcore\telemetry.py Tools\devcore\session.py Tests\test_telemetry.py
git -C C:\DEV_CORE commit -m "feat: add session outcome telemetry"
```

## Task 4: Aggregate Prompt And Engine Scores Deterministically

**Files:**
- Create: `C:\DEV_CORE\Tools\devcore\scoring.py`
- Create: `C:\DEV_CORE\Tests\test_scoring.py`

- [ ] **Step 1: Write the failing scoring tests**

```python
# C:\DEV_CORE\Tests\test_scoring.py
from devcore.scoring import score_engine_effectiveness, score_prompt_patterns


def test_score_engine_effectiveness_counts_completed_outcomes():
    events = [
        {"engine": "codex", "status": "completed", "rework": False},
        {"engine": "codex", "status": "completed", "rework": True},
        {"engine": "claude", "status": "failed", "rework": False},
    ]

    scores = score_engine_effectiveness(events)

    assert scores["codex"]["completed"] == 2
    assert scores["codex"]["rework_rate"] == 0.5
    assert scores["claude"]["failed"] == 1


def test_score_prompt_patterns_groups_by_prompt_pattern():
    events = [
        {"prompt_pattern": "patch + explanation + risks", "status": "completed"},
        {"prompt_pattern": "patch + explanation + risks", "status": "completed"},
        {"prompt_pattern": "analyse + risques", "status": "failed"},
    ]

    scores = score_prompt_patterns(events)

    assert scores["patch + explanation + risks"]["uses"] == 2
    assert scores["patch + explanation + risks"]["completed"] == 2
    assert scores["analyse + risques"]["failed"] == 1
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_scoring.py -q
```

Expected:

```text
E   ModuleNotFoundError: No module named 'devcore.scoring'
```

- [ ] **Step 3: Implement deterministic score aggregation**

```python
# C:\DEV_CORE\Tools\devcore\scoring.py
def score_engine_effectiveness(events: list[dict]) -> dict:
    scores: dict[str, dict] = {}
    for event in events:
        engine = event["engine"]
        bucket = scores.setdefault(
            engine,
            {"completed": 0, "failed": 0, "rework_count": 0, "rework_rate": 0.0},
        )
        if event.get("status") == "completed":
            bucket["completed"] += 1
        if event.get("status") == "failed":
            bucket["failed"] += 1
        if event.get("rework"):
            bucket["rework_count"] += 1

    for bucket in scores.values():
        total_completed = bucket["completed"]
        bucket["rework_rate"] = (
            bucket["rework_count"] / total_completed if total_completed else 0.0
        )
    return scores


def score_prompt_patterns(events: list[dict]) -> dict:
    scores: dict[str, dict] = {}
    for event in events:
        pattern = event["prompt_pattern"]
        bucket = scores.setdefault(
            pattern,
            {"uses": 0, "completed": 0, "failed": 0},
        )
        bucket["uses"] += 1
        if event.get("status") == "completed":
            bucket["completed"] += 1
        if event.get("status") == "failed":
            bucket["failed"] += 1
    return scores
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_scoring.py -q
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Commit**

```powershell
git -C C:\DEV_CORE add Tools\devcore\scoring.py Tests\test_scoring.py
git -C C:\DEV_CORE commit -m "feat: add deterministic telemetry scoring"
```

## Task 5: Persist Score Snapshots And Verify End-To-End Prepare Logging

**Files:**
- Modify: `C:\DEV_CORE\Tests\test_scoring.py`
- Modify: `C:\DEV_CORE\Tests\test_cli_smoke.py`
- Modify: `C:\DEV_CORE\Tools\devcore\scoring.py`

- [ ] **Step 1: Extend scoring tests with score snapshot persistence**

```python
# append to C:\DEV_CORE\Tests\test_scoring.py
import json

from devcore.scoring import write_score_snapshots


def test_write_score_snapshots_persists_engine_and_prompt_scores(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVCORE_PLATFORM_ROOT", str(tmp_path / "platform"))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(tmp_path / "data"))

    paths = write_score_snapshots(
        engine_scores={"codex": {"completed": 2, "failed": 0, "rework_count": 1, "rework_rate": 0.5}},
        prompt_scores={"patch + explanation + risks": {"uses": 2, "completed": 2, "failed": 0}},
    )

    engine_payload = json.loads(paths["engine_scores"].read_text(encoding="utf-8"))
    prompt_payload = json.loads(paths["prompt_scores"].read_text(encoding="utf-8"))

    assert paths["engine_scores"].name == "engine-scores.json"
    assert engine_payload["codex"]["completed"] == 2
    assert prompt_payload["patch + explanation + risks"]["uses"] == 2
```

```python
# append to C:\DEV_CORE\Tests\test_cli_smoke.py
def test_build_prepare_payload_writes_prepare_telemetry(tmp_path, monkeypatch):
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

    telemetry_path = tmp_path / "data" / "Logs" / "router" / "prepare-events.jsonl"
    lines = telemetry_path.read_text(encoding="utf-8").splitlines()

    assert result["engine"] == "codex"
    assert len(lines) == 1
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_scoring.py Tests\test_cli_smoke.py -q
```

Expected:

```text
FAIL because write_score_snapshots does not exist yet
```

- [ ] **Step 3: Add score snapshot persistence**

```python
# append to C:\DEV_CORE\Tools\devcore\scoring.py
import json

from devcore.paths import get_paths


def write_score_snapshots(engine_scores: dict, prompt_scores: dict) -> dict:
    paths = get_paths()
    engine_path = paths.scoring_log_root / "engine-scores.json"
    prompt_path = paths.scoring_log_root / "prompt-scores.json"
    engine_path.write_text(json.dumps(engine_scores, indent=2), encoding="utf-8")
    prompt_path.write_text(json.dumps(prompt_scores, indent=2), encoding="utf-8")
    return {
        "engine_scores": engine_path,
        "prompt_scores": prompt_path,
    }
```

- [ ] **Step 4: Run the focused tests and full suite to verify they pass**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_scoring.py Tests\test_cli_smoke.py -q
python -m pytest Tests -q
```

Expected:

```text
All focused tests pass
All tests pass
```

- [ ] **Step 5: Commit**

```powershell
git -C C:\DEV_CORE add Tools\devcore\scoring.py Tests\test_scoring.py Tests\test_cli_smoke.py
git -C C:\DEV_CORE commit -m "feat: persist telemetry score snapshots"
```

## Definition Of Done

- prepare events are logged durably under `C:\DEV_CORE_DATA\Logs\router`
- outcome events can be logged without touching canonical memory
- engine and prompt scores can be derived deterministically from telemetry events
- score snapshots are persisted under `C:\DEV_CORE_DATA\Logs\scoring`
- the existing prepare flow writes telemetry without changing handoff contracts
- `python -m pytest Tests -q` passes from `C:\DEV_CORE`

## Follow-Up Plans Required

After this slice lands, separate plans should cover:

1. predictive router consumption of score snapshots
2. richer outcome capture linked to receipts and rework loops
3. dashboard views for routing effectiveness and prompt success
4. memory sync rules that selectively promote high-value telemetry insights

## Self-Review

### Spec Coverage

Covered:

- router decision logging
- outcome logging
- prompt scoring
- engine effectiveness scoring
- append-only operational telemetry
- no canonical memory mutation

Deferred:

- predictive routing
- UI exposure
- automatic engine adaptation
- memory promotion from scores

### Placeholder Scan

No implementation steps contain `TODO`, `TBD`, or placeholder action language.

### Type Consistency

Stable names are used consistently:

- `log_prepare_event`
- `log_outcome_event`
- `score_engine_effectiveness`
- `score_prompt_patterns`
- `write_score_snapshots`
- `prepare-events.jsonl`
- `outcome-events.jsonl`
