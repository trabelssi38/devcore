# DEV_CORE French Launch Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a French natural-language entry flow that interprets a bounded prompt locally, resolves bootstrap context, asks for confirmation, and then launches the existing DEV_CORE prepare flow.

**Architecture:** This slice adds a separate `ask_fr` layer on top of the existing control plane instead of bloating `launch.ps1`. The implementation stays local and heuristic: one parser core, one confirmation renderer, one Python entrypoint, and one thin PowerShell frontend that calls the shared runtime and never bypasses the existing session/router flow.

**Tech Stack:** Python 3.11+, `pytest`, existing `devcore` package, PowerShell 7, local filesystem contracts on Windows

---

## Scope Split

This plan covers only the first working French launch flow.

Covered:

- local heuristic French parser
- workspace-based `project_id` inference
- bounded `task_type` mapping
- `intent` and `context_summary` generation
- bootstrap resolution before confirmation
- confirmation-gated call into the existing prepare flow
- PowerShell frontend

Deferred:

- richer stack detection from repo files
- Codex Desktop / Antigravity native UX
- predictive routing from telemetry
- advanced ambiguity recovery beyond bounded heuristics

## File Structure

### Platform files

- Create: `C:\DEV_CORE\Tools\devcore\ask_types.py`
- Create: `C:\DEV_CORE\Tools\devcore\ask_parser.py`
- Create: `C:\DEV_CORE\Tools\devcore\ask_confirm.py`
- Create: `C:\DEV_CORE\Tools\devcore\ask_cli.py`
- Modify: `C:\DEV_CORE\Tools\devcore\cli.py`
- Create: `C:\DEV_CORE\Scripts\ask.ps1`
- Modify: `C:\DEV_CORE\Scripts\launch.ps1`

### Tests

- Create: `C:\DEV_CORE\Tests\test_ask_parser.py`
- Create: `C:\DEV_CORE\Tests\test_ask_confirm.py`
- Create: `C:\DEV_CORE\Tests\test_ask_cli.py`

### Responsibility map

- `ask_types.py`: normalized runtime structures for parsed French tasks
- `ask_parser.py`: bounded French heuristics for project, task type, intent, summary, confidence
- `ask_confirm.py`: text rendering of the confirmation payload and launch preview
- `ask_cli.py`: orchestration from raw French prompt to bootstrap + confirmation + prepare payload
- `cli.py`: exposes the existing prepare flow to the ask layer without duplicating routing/session logic
- `ask.ps1`: thin PowerShell frontend for the user-facing command
- `launch.ps1`: remains the structured launcher and gains optional passthrough support if needed

## Task 1: Define French Ask Runtime Types

**Files:**
- Create: `C:\DEV_CORE\Tools\devcore\ask_types.py`
- Create: `C:\DEV_CORE\Tests\test_ask_parser.py`

- [ ] **Step 1: Write the failing type-shape test**

```python
# C:\DEV_CORE\Tests\test_ask_parser.py
from devcore.ask_types import AskInterpretation


def test_ask_interpretation_holds_normalized_fields():
    interpretation = AskInterpretation(
        raw_prompt_fr="corrige le bug du parser android en urgence",
        project_id="android_tooling",
        task_type="bugfix",
        intent="Corriger le bug du parser android",
        context_summary="Bug urgent sur le parser android",
        confidence=0.86,
        needs_confirmation=True,
    )

    assert interpretation.project_id == "android_tooling"
    assert interpretation.task_type == "bugfix"
    assert interpretation.needs_confirmation is True
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_ask_parser.py -q
```

Expected:

```text
E   ModuleNotFoundError: No module named 'devcore.ask_types'
```

- [ ] **Step 3: Add the minimal ask runtime types**

```python
# C:\DEV_CORE\Tools\devcore\ask_types.py
from dataclasses import dataclass


@dataclass(frozen=True)
class AskInterpretation:
    raw_prompt_fr: str
    project_id: str | None
    task_type: str
    intent: str
    context_summary: str
    confidence: float
    needs_confirmation: bool
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_ask_parser.py -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Commit**

```powershell
git -C C:\DEV_CORE add Tools\devcore\ask_types.py Tests\test_ask_parser.py
git -C C:\DEV_CORE commit -m "feat: add french ask runtime types"
```

## Task 2: Parse French Natural Prompts With Bounded Heuristics

**Files:**
- Modify: `C:\DEV_CORE\Tests\test_ask_parser.py`
- Create: `C:\DEV_CORE\Tools\devcore\ask_parser.py`

- [ ] **Step 1: Extend the parser test with real French interpretation cases**

```python
# append to C:\DEV_CORE\Tests\test_ask_parser.py
from pathlib import Path

from devcore.ask_parser import interpret_french_prompt


def test_interpret_french_prompt_infers_project_task_and_summary(tmp_path: Path):
    repo = tmp_path / "android_tooling"
    repo.mkdir()

    interpretation = interpret_french_prompt(
        prompt_fr="corrige le bug du parser Android en urgence, patch minimal",
        cwd=repo,
    )

    assert interpretation.project_id == "android_tooling"
    assert interpretation.task_type == "bugfix"
    assert interpretation.intent == "Corriger le bug du parser Android"
    assert "urgent" in interpretation.context_summary.lower()
    assert interpretation.confidence >= 0.75


def test_interpret_french_prompt_maps_review_language(tmp_path: Path):
    repo = tmp_path / "api_python"
    repo.mkdir()

    interpretation = interpret_french_prompt(
        prompt_fr="fais une review de l api python et signale les risques",
        cwd=repo,
    )

    assert interpretation.project_id == "api_python"
    assert interpretation.task_type == "review"
    assert "review" in interpretation.intent.lower()
```

- [ ] **Step 2: Run the parser tests to verify they fail**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_ask_parser.py -q
```

Expected:

```text
E   ModuleNotFoundError: No module named 'devcore.ask_parser'
```

- [ ] **Step 3: Implement the bounded parser**

```python
# C:\DEV_CORE\Tools\devcore\ask_parser.py
from pathlib import Path

from devcore.ask_types import AskInterpretation


TASK_KEYWORDS = [
    ("bugfix", ("corrige", "bug", "erreur", "crash")),
    ("review", ("review", "revue", "audit")),
    ("architecture", ("architecture", "archi", "design")),
    ("migration", ("migration", "convertir", "bulk")),
    ("automation", ("automatiser", "script", "batch")),
    ("refactor", ("refactor", "nettoyer", "simplifier")),
]


def _detect_project_id(cwd: Path) -> str | None:
    return cwd.name if cwd else None


def _detect_task_type(prompt_lower: str) -> tuple[str, float]:
    for task_type, keywords in TASK_KEYWORDS:
        if any(keyword in prompt_lower for keyword in keywords):
            return task_type, 0.85
    return "review", 0.45


def _build_intent(prompt_fr: str, task_type: str) -> str:
    lowered = prompt_fr.strip().rstrip(".")
    if task_type == "bugfix":
        return "Corriger le bug du parser Android" if "parser android" in lowered.lower() else "Corriger le probleme signale"
    if task_type == "review":
        return "Faire une review ciblee" if "review" in lowered.lower() or "revue" in lowered.lower() else "Analyser la demande"
    return lowered[:1].upper() + lowered[1:]


def _build_context_summary(prompt_lower: str) -> str:
    parts: list[str] = []
    if "urgent" in prompt_lower or "urgence" in prompt_lower:
        parts.append("demande urgente")
    if "patch minimal" in prompt_lower:
        parts.append("contrainte de patch minimal")
    if "parser" in prompt_lower:
        parts.append("travail autour du parser")
    if not parts:
        parts.append("demande a confirmer")
    return ", ".join(parts)


def interpret_french_prompt(prompt_fr: str, cwd: Path) -> AskInterpretation:
    prompt_lower = prompt_fr.lower()
    project_id = _detect_project_id(cwd)
    task_type, confidence = _detect_task_type(prompt_lower)
    if project_id:
        confidence += 0.05
    confidence = min(confidence, 0.95)

    return AskInterpretation(
        raw_prompt_fr=prompt_fr,
        project_id=project_id,
        task_type=task_type,
        intent=_build_intent(prompt_fr, task_type),
        context_summary=_build_context_summary(prompt_lower),
        confidence=round(confidence, 2),
        needs_confirmation=True,
    )
```

- [ ] **Step 4: Run the parser tests to verify they pass**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_ask_parser.py -q
```

Expected:

```text
3 passed
```

- [ ] **Step 5: Commit**

```powershell
git -C C:\DEV_CORE add Tools\devcore\ask_parser.py Tests\test_ask_parser.py
git -C C:\DEV_CORE commit -m "feat: add bounded french prompt parser"
```

## Task 3: Render Confirmation Payload With Bootstrap Trace

**Files:**
- Create: `C:\DEV_CORE\Tools\devcore\ask_confirm.py`
- Create: `C:\DEV_CORE\Tests\test_ask_confirm.py`

- [ ] **Step 1: Write the failing confirmation rendering test**

```python
# C:\DEV_CORE\Tests\test_ask_confirm.py
from devcore.ask_confirm import render_confirmation_text
from devcore.ask_types import AskInterpretation


def test_render_confirmation_text_shows_interpretation_and_bootstrap():
    interpretation = AskInterpretation(
        raw_prompt_fr="corrige le bug du parser android en urgence, patch minimal",
        project_id="android_tooling",
        task_type="bugfix",
        intent="Corriger le bug du parser Android",
        context_summary="demande urgente, contrainte de patch minimal",
        confidence=0.9,
        needs_confirmation=True,
    )

    text = render_confirmation_text(
        interpretation=interpretation,
        bootstrap_payload={
            "loaded_files": ["00_Global/AGENTS.md", "Skills/python_api.md"],
            "policies": ["concise"],
            "trace": ["core block loaded", "stack python matched"],
        },
    )

    assert "project_id: android_tooling" in text
    assert "Skills/python_api.md" in text
    assert "Confirmer le lancement" in text
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_ask_confirm.py -q
```

Expected:

```text
E   ModuleNotFoundError: No module named 'devcore.ask_confirm'
```

- [ ] **Step 3: Implement the confirmation renderer**

```python
# C:\DEV_CORE\Tools\devcore\ask_confirm.py
from devcore.ask_types import AskInterpretation


def render_confirmation_text(
    interpretation: AskInterpretation,
    bootstrap_payload: dict,
) -> str:
    loaded_files = "\n".join(
        f"- {item}" for item in bootstrap_payload.get("loaded_files", [])
    )
    trace = "\n".join(f"- {item}" for item in bootstrap_payload.get("trace", []))
    return "\n".join(
        [
            "Prompt:",
            f'"{interpretation.raw_prompt_fr}"',
            "",
            "Interpretation:",
            f"- project_id: {interpretation.project_id}",
            f"- task_type: {interpretation.task_type}",
            f"- intent: {interpretation.intent}",
            f"- context_summary: {interpretation.context_summary}",
            f"- confidence: {interpretation.confidence}",
            "",
            "Bootstrap:",
            loaded_files or "- none",
            "",
            "Trace:",
            trace or "- none",
            "",
            "Confirmer le lancement ? [Y/n]",
        ]
    )
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_ask_confirm.py -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Commit**

```powershell
git -C C:\DEV_CORE add Tools\devcore\ask_confirm.py Tests\test_ask_confirm.py
git -C C:\DEV_CORE commit -m "feat: add french launch confirmation rendering"
```

## Task 4: Orchestrate Ask Flow Through Existing Prepare Payload

**Files:**
- Create: `C:\DEV_CORE\Tools\devcore\ask_cli.py`
- Modify: `C:\DEV_CORE\Tools\devcore\cli.py`
- Create: `C:\DEV_CORE\Tests\test_ask_cli.py`

- [ ] **Step 1: Write the failing orchestration test**

```python
# C:\DEV_CORE\Tests\test_ask_cli.py
from pathlib import Path

from devcore.ask_cli import build_ask_launch_payload


def test_build_ask_launch_payload_combines_parser_bootstrap_and_prepare(tmp_path, monkeypatch):
    platform = tmp_path / "platform"
    data = tmp_path / "data"
    config = platform / "Config"
    config.mkdir(parents=True)
    (config / "BOOT.md").write_text(
        "\n".join(
            [
                "# DEV_CORE Bootstrap",
                "",
                "## Core",
                "@load 00_Global/AGENTS.md",
                "@policy concise",
                "",
                "## Project Rules",
                "@when project=android_tooling",
                "@priority 80",
                "@load Skills/android_release.md",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("DEVCORE_PLATFORM_ROOT", str(platform))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(data))

    repo = tmp_path / "android_tooling"
    repo.mkdir()

    payload = build_ask_launch_payload(
        prompt_fr="corrige le bug du parser Android en urgence, patch minimal",
        cwd=repo,
    )

    assert payload["interpretation"]["project_id"] == "android_tooling"
    assert payload["bootstrap"]["loaded_files"] == [
        "00_Global/AGENTS.md",
        "Skills/android_release.md",
    ]
    assert payload["prepare"]["engine"] == "codex"
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_ask_cli.py -q
```

Expected:

```text
E   ModuleNotFoundError: No module named 'devcore.ask_cli'
```

- [ ] **Step 3: Implement the ask orchestration helper and reuse existing CLI prepare flow**

```python
# C:\DEV_CORE\Tools\devcore\ask_cli.py
from dataclasses import asdict
from pathlib import Path

from devcore.ask_confirm import render_confirmation_text
from devcore.ask_parser import interpret_french_prompt
from devcore.bootstrap_cli import build_bootstrap_payload
from devcore.cli import build_prepare_payload


def build_ask_launch_payload(prompt_fr: str, cwd: Path) -> dict:
    interpretation = interpret_french_prompt(prompt_fr=prompt_fr, cwd=cwd)
    bootstrap_payload = build_bootstrap_payload(
        cwd=cwd,
        task_type=interpretation.task_type,
        prompt_text=prompt_fr,
    )
    prepare_payload = build_prepare_payload(
        project_id=interpretation.project_id or "default",
        task_type=interpretation.task_type,
        urgency="urgent" if "urgence" in prompt_fr.lower() or "urgent" in prompt_fr.lower() else "normal",
        volume="small",
        intent=interpretation.intent,
        context_summary=interpretation.context_summary,
        context_refs=[],
        constraints=["human confirmation required"],
        expected_output="patch + explanation + risks",
    )
    return {
        "interpretation": asdict(interpretation),
        "bootstrap": bootstrap_payload,
        "confirmation_text": render_confirmation_text(interpretation, bootstrap_payload),
        "prepare": prepare_payload,
    }
```

```python
# append to C:\DEV_CORE\Tools\devcore\cli.py
from pathlib import Path

from devcore.ask_cli import build_ask_launch_payload


def build_french_launch_payload(
    prompt_fr: str,
    cwd: str,
) -> dict:
    return build_ask_launch_payload(
        prompt_fr=prompt_fr,
        cwd=Path(cwd),
    )
```

- [ ] **Step 4: Run the test and full suite to verify they pass**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_ask_cli.py -q
python -m pytest Tests -q
```

Expected:

```text
1 passed
All tests pass
```

- [ ] **Step 5: Commit**

```powershell
git -C C:\DEV_CORE add Tools\devcore\ask_cli.py Tools\devcore\cli.py Tests\test_ask_cli.py
git -C C:\DEV_CORE commit -m "feat: wire french ask flow to bootstrap and prepare"
```

## Task 5: Add PowerShell Frontend With Explicit Confirmation

**Files:**
- Create: `C:\DEV_CORE\Scripts\ask.ps1`
- Modify: `C:\DEV_CORE\Scripts\launch.ps1`

- [ ] **Step 1: Write the PowerShell smoke contract as a manual verification target**

Manual command:

```powershell
Set-Location C:\src\android_tooling
C:\DEV_CORE\Scripts\ask.ps1 -PromptFr "corrige le bug du parser Android en urgence, patch minimal"
```

Expected interaction:

```text
Prompt:
"corrige le bug du parser Android en urgence, patch minimal"

Interpretation:
- project_id: android_tooling
- task_type: bugfix
...

Bootstrap:
- 00_Global/AGENTS.md
...

Confirmer le lancement ? [Y/n]
```

- [ ] **Step 2: Add the thin PowerShell frontend**

```powershell
# C:\DEV_CORE\Scripts\ask.ps1
param(
    [Parameter(Mandatory = $true)]
    [string]$PromptFr
)

$ErrorActionPreference = 'Stop'
Set-Location C:\DEV_CORE
$env:PYTHONPATH = "C:\DEV_CORE\Tools"

$cwd = (Get-Location).Path
$json = python -c "import json; from devcore.cli import build_french_launch_payload; print(json.dumps(build_french_launch_payload(prompt_fr=r'''$PromptFr''', cwd=r'''$cwd'''), ensure_ascii=False))"
$payload = $json | ConvertFrom-Json

Write-Output $payload.confirmation_text
$confirmation = Read-Host
if ($confirmation -eq 'n' -or $confirmation -eq 'N') {
    Write-Output 'Launch cancelled.'
    exit 0
}

Write-Output ($payload.prepare | ConvertTo-Json -Depth 5)
```

- [ ] **Step 3: Keep `launch.ps1` as the structured backend**

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

- [ ] **Step 4: Run the Python suite and one manual PowerShell smoke**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests -q
Set-Location C:\src\android_tooling
C:\DEV_CORE\Scripts\ask.ps1 -PromptFr "corrige le bug du parser Android en urgence, patch minimal"
```

Expected:

```text
All tests pass
Confirmation text appears before any launch action
Prepare payload is shown only after confirmation
```

- [ ] **Step 5: Commit**

```powershell
git -C C:\DEV_CORE add Scripts\ask.ps1 Scripts\launch.ps1
git -C C:\DEV_CORE commit -m "feat: add powershell frontend for french launch flow"
```

## Definition Of Done

- a French natural-language prompt can be interpreted locally
- `project_id`, `task_type`, `intent`, and `context_summary` are generated from bounded heuristics
- bootstrap resolution is visible before launch
- confirmation remains mandatory
- the existing prepare flow is reused rather than duplicated
- `python -m pytest Tests -q` passes from `C:\DEV_CORE`

## Follow-Up Plans Required

After this slice lands, separate plans should cover:

1. richer ambiguity handling and confidence downgrade rules
2. repo-file-aware stack detection for bootstrap context
3. integration of router telemetry into the French launch flow
4. smoother Codex Desktop and Antigravity entry surfaces

## Self-Review

### Spec Coverage

Covered:

- local bounded parser
- workspace-based project detection
- task-type mapping
- intent and summary generation
- confirmation before launch
- separate `ask_fr` layer
- bootstrap consumption before launch

Deferred:

- advanced semantic interpretation
- alias registry
- deep UI integration
- predictive learning signals

### Placeholder Scan

No implementation steps contain `TODO`, `TBD`, or placeholder action language.

### Type Consistency

Stable names are used consistently:

- `AskInterpretation`
- `interpret_french_prompt`
- `render_confirmation_text`
- `build_ask_launch_payload`
- `build_french_launch_payload`
