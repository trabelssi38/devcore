# DEV_CORE Declarative Bootstrap Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first working slice of the declarative `BOOT.md` system so DEV_CORE can parse bootstrap directives, detect session context, resolve matching load blocks, and emit a deterministic bootstrap trace.

**Architecture:** This slice adds a small bootstrap runtime inside `devcore` rather than scattering logic across scripts. The implementation is intentionally narrow: parse a bounded Markdown directive set, detect current session context, resolve matching blocks with priorities and deduplication, and expose the result through a Python entrypoint that can later be integrated into `launch.ps1` and future ask/FR flows.

**Tech Stack:** Python 3.11+, `pytest`, existing `devcore` package, Markdown parsing with simple line-based heuristics, PowerShell only for thin integration

---

## Scope Split

This plan covers only the bootstrap runtime foundation.

Deferred to later plans:

- natural-language French prompt parser integration
- automatic loading into Codex Desktop / Antigravity surfaces
- advanced vault summarization or retrieval ranking
- UI/dashboard exposure of bootstrap trace

## File Structure

### Platform files

- Modify: `C:\DEV_CORE\Config\BOOT.md`
- Create: `C:\DEV_CORE\Tools\devcore\bootstrap_types.py`
- Create: `C:\DEV_CORE\Tools\devcore\bootstrap_parser.py`
- Create: `C:\DEV_CORE\Tools\devcore\bootstrap_context.py`
- Create: `C:\DEV_CORE\Tools\devcore\bootstrap_resolver.py`
- Create: `C:\DEV_CORE\Tools\devcore\bootstrap_cli.py`
- Modify: `C:\DEV_CORE\Tools\devcore\cli.py`

### Tests

- Create: `C:\DEV_CORE\Tests\test_bootstrap_parser.py`
- Create: `C:\DEV_CORE\Tests\test_bootstrap_context.py`
- Create: `C:\DEV_CORE\Tests\test_bootstrap_resolver.py`
- Create: `C:\DEV_CORE\Tests\test_bootstrap_cli.py`

### Responsibility map

- `bootstrap_types.py`: dataclasses and normalized runtime structures
- `bootstrap_parser.py`: parse the bounded directive grammar from `BOOT.md`
- `bootstrap_context.py`: detect project, stack, moment, and optional task type from current session inputs
- `bootstrap_resolver.py`: match blocks, apply priorities, deduplicate files, and build trace output
- `bootstrap_cli.py`: expose a narrow command for inspecting bootstrap resolution
- `cli.py`: optional handoff point so the existing DEV_CORE flow can consume resolved bootstrap data later without duplicating logic
- `BOOT.md`: first real declarative bootstrap spec replacing the current prose-only placeholder

## Task 1: Define Bootstrap Runtime Types

**Files:**
- Create: `C:\DEV_CORE\Tools\devcore\bootstrap_types.py`
- Create: `C:\DEV_CORE\Tests\test_bootstrap_parser.py`

- [ ] **Step 1: Write the failing type-shape test**

```python
# C:\DEV_CORE\Tests\test_bootstrap_parser.py
from devcore.bootstrap_types import BootstrapBlock, BootstrapDirective


def test_bootstrap_block_holds_directives_and_conditions():
    directive = BootstrapDirective(kind="load", value="00_Global/AGENTS.md")
    block = BootstrapBlock(
        section="Core",
        when={},
        priority=100,
        directives=[directive],
    )

    assert block.section == "Core"
    assert block.priority == 100
    assert block.directives[0].kind == "load"
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_bootstrap_parser.py -q
```

Expected:

```text
E   ModuleNotFoundError: No module named 'devcore.bootstrap_types'
```

- [ ] **Step 3: Add the minimal bootstrap type module**

```python
# C:\DEV_CORE\Tools\devcore\bootstrap_types.py
from dataclasses import dataclass, field


@dataclass(frozen=True)
class BootstrapDirective:
    kind: str
    value: str


@dataclass(frozen=True)
class BootstrapBlock:
    section: str
    when: dict[str, str]
    priority: int
    directives: list[BootstrapDirective] = field(default_factory=list)


@dataclass(frozen=True)
class BootstrapContext:
    project: str | None
    stack: list[str]
    moment: str | None
    task_type: str | None


@dataclass(frozen=True)
class BootstrapResult:
    loaded_files: list[str]
    policies: list[str]
    trace: list[str]
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_bootstrap_parser.py -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Commit**

```powershell
git -C C:\DEV_CORE add Tools\devcore\bootstrap_types.py Tests\test_bootstrap_parser.py
git -C C:\DEV_CORE commit -m "feat: add bootstrap runtime types"
```

## Task 2: Parse Declarative BOOT.md Directives

**Files:**
- Modify: `C:\DEV_CORE\Config\BOOT.md`
- Modify: `C:\DEV_CORE\Tests\test_bootstrap_parser.py`
- Create: `C:\DEV_CORE\Tools\devcore\bootstrap_parser.py`

- [ ] **Step 1: Extend the parser test with a real BOOT fixture**

```python
# append to C:\DEV_CORE\Tests\test_bootstrap_parser.py
from pathlib import Path

from devcore.bootstrap_parser import parse_bootstrap_markdown


def test_parse_bootstrap_markdown_extracts_blocks(tmp_path):
    boot = tmp_path / "BOOT.md"
    boot.write_text(
        "\n".join(
            [
                "# DEV_CORE Bootstrap",
                "",
                "## Core",
                "@load 00_Global/AGENTS.md",
                "@load 00_Global/TOKEN_RULES.md",
                "@policy concise",
                "",
                "## Stack Rules",
                "@when stack=python",
                "@priority 60",
                "@load Skills/python_api.md",
            ]
        ),
        encoding="utf-8",
    )

    blocks = parse_bootstrap_markdown(boot)

    assert len(blocks) == 2
    assert blocks[0].section == "Core"
    assert blocks[0].directives[0].value == "00_Global/AGENTS.md"
    assert blocks[1].when == {"stack": "python"}
    assert blocks[1].priority == 60
```

- [ ] **Step 2: Run the parser test to verify it fails**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_bootstrap_parser.py -q
```

Expected:

```text
E   ModuleNotFoundError: No module named 'devcore.bootstrap_parser'
```

- [ ] **Step 3: Implement the parser and replace BOOT.md with the first declarative spec**

```python
# C:\DEV_CORE\Tools\devcore\bootstrap_parser.py
from pathlib import Path

from devcore.bootstrap_types import BootstrapBlock, BootstrapDirective


def parse_bootstrap_markdown(path: Path) -> list[BootstrapBlock]:
    lines = path.read_text(encoding="utf-8").splitlines()
    blocks: list[BootstrapBlock] = []
    current_section = "Default"
    current_when: dict[str, str] = {}
    current_priority = 50
    current_directives: list[BootstrapDirective] = []

    def flush() -> None:
        nonlocal current_when, current_priority, current_directives
        if current_directives:
            blocks.append(
                BootstrapBlock(
                    section=current_section,
                    when=current_when,
                    priority=current_priority,
                    directives=current_directives,
                )
            )
        current_when = {}
        current_priority = 50
        current_directives = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("## "):
            flush()
            current_section = line[3:].strip()
            continue
        if line.startswith("@when "):
            key, value = line[6:].split("=", 1)
            current_when = {key.strip(): value.strip()}
            continue
        if line.startswith("@priority "):
            current_priority = int(line[10:].strip())
            continue
        if line.startswith("@load "):
            current_directives.append(BootstrapDirective(kind="load", value=line[6:].strip()))
            continue
        if line.startswith("@policy "):
            current_directives.append(BootstrapDirective(kind="policy", value=line[8:].strip()))

    flush()
    return blocks
```

```md
# C:\DEV_CORE\Config\BOOT.md
# DEV_CORE Bootstrap

## Core
@load 00_Global/AGENTS.md
@load 00_Global/TOKEN_RULES.md
@policy concise
@policy memory_first
@policy intelligent_routing

## Project Rules
@when project=android_tooling
@priority 80
@load Skills/android_release.md

## Stack Rules
@when stack=python
@priority 60
@load Skills/python_api.md

## Stack Rules
@when stack=web
@priority 60
@load Skills/web_ui.md

## Work Moment Rules
@when moment=daily
@priority 40
@load Daily/latest.md
```

- [ ] **Step 4: Run the parser test to verify it passes**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_bootstrap_parser.py -q
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Commit**

```powershell
git -C C:\DEV_CORE add Config\BOOT.md Tools\devcore\bootstrap_parser.py Tests\test_bootstrap_parser.py
git -C C:\DEV_CORE commit -m "feat: add declarative bootstrap parser"
```

## Task 3: Detect Bootstrap Context

**Files:**
- Create: `C:\DEV_CORE\Tools\devcore\bootstrap_context.py`
- Create: `C:\DEV_CORE\Tests\test_bootstrap_context.py`

- [ ] **Step 1: Write the failing context detection tests**

```python
# C:\DEV_CORE\Tests\test_bootstrap_context.py
from pathlib import Path

from devcore.bootstrap_context import detect_bootstrap_context


def test_detect_bootstrap_context_uses_repo_name_for_project(tmp_path):
    repo = tmp_path / "android_tooling"
    repo.mkdir()

    context = detect_bootstrap_context(cwd=repo, task_type="bugfix")

    assert context.project == "android_tooling"
    assert context.task_type == "bugfix"


def test_detect_bootstrap_context_marks_daily_moment_for_planning_task(tmp_path):
    repo = tmp_path / "api_python"
    repo.mkdir()

    context = detect_bootstrap_context(
        cwd=repo,
        task_type="review",
        prompt_text="prepare my daily priorities and blockers",
    )

    assert context.moment == "daily"
```

- [ ] **Step 2: Run the context tests to verify they fail**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_bootstrap_context.py -q
```

Expected:

```text
E   ModuleNotFoundError: No module named 'devcore.bootstrap_context'
```

- [ ] **Step 3: Implement minimal context detection**

```python
# C:\DEV_CORE\Tools\devcore\bootstrap_context.py
from pathlib import Path

from devcore.bootstrap_types import BootstrapContext


def detect_bootstrap_context(
    cwd: Path,
    task_type: str | None = None,
    prompt_text: str = "",
) -> BootstrapContext:
    project = cwd.name if cwd else None

    stack: list[str] = []
    lowered = project.lower() if project else ""
    if "android" in lowered:
        stack.append("android")
    if "python" in lowered or "api" in lowered:
        stack.append("python")
    if "web" in lowered or "ui" in lowered:
        stack.append("web")

    moment = None
    prompt_lower = prompt_text.lower()
    if any(term in prompt_lower for term in ["daily", "priorities", "blockers", "today"]):
        moment = "daily"

    return BootstrapContext(
        project=project,
        stack=stack,
        moment=moment,
        task_type=task_type,
    )
```

- [ ] **Step 4: Run the context tests to verify they pass**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_bootstrap_context.py -q
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Commit**

```powershell
git -C C:\DEV_CORE add Tools\devcore\bootstrap_context.py Tests\test_bootstrap_context.py
git -C C:\DEV_CORE commit -m "feat: add bootstrap context detection"
```

## Task 4: Resolve Matching Blocks And Emit Trace

**Files:**
- Create: `C:\DEV_CORE\Tools\devcore\bootstrap_resolver.py`
- Create: `C:\DEV_CORE\Tests\test_bootstrap_resolver.py`

- [ ] **Step 1: Write the failing resolver tests**

```python
# C:\DEV_CORE\Tests\test_bootstrap_resolver.py
from devcore.bootstrap_resolver import resolve_bootstrap
from devcore.bootstrap_types import BootstrapBlock, BootstrapContext, BootstrapDirective


def test_resolve_bootstrap_loads_core_project_and_stack_blocks():
    blocks = [
        BootstrapBlock(
            section="Core",
            when={},
            priority=100,
            directives=[
                BootstrapDirective(kind="load", value="00_Global/AGENTS.md"),
                BootstrapDirective(kind="policy", value="concise"),
            ],
        ),
        BootstrapBlock(
            section="Project Rules",
            when={"project": "android_tooling"},
            priority=80,
            directives=[BootstrapDirective(kind="load", value="Skills/android_release.md")],
        ),
        BootstrapBlock(
            section="Stack Rules",
            when={"stack": "python"},
            priority=60,
            directives=[BootstrapDirective(kind="load", value="Skills/python_api.md")],
        ),
    ]
    context = BootstrapContext(
        project="android_tooling",
        stack=["python"],
        moment=None,
        task_type="bugfix",
    )

    result = resolve_bootstrap(blocks, context)

    assert result.loaded_files == [
        "00_Global/AGENTS.md",
        "Skills/android_release.md",
        "Skills/python_api.md",
    ]
    assert result.policies == ["concise"]
    assert any("project android_tooling matched" in item for item in result.trace)
```

- [ ] **Step 2: Run the resolver tests to verify they fail**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_bootstrap_resolver.py -q
```

Expected:

```text
E   ModuleNotFoundError: No module named 'devcore.bootstrap_resolver'
```

- [ ] **Step 3: Implement the resolver**

```python
# C:\DEV_CORE\Tools\devcore\bootstrap_resolver.py
from devcore.bootstrap_types import BootstrapBlock, BootstrapContext, BootstrapResult


def _matches(block: BootstrapBlock, context: BootstrapContext) -> bool:
    if not block.when:
        return True
    for key, value in block.when.items():
        if key == "project" and context.project != value:
            return False
        if key == "moment" and context.moment != value:
            return False
        if key == "task_type" and context.task_type != value:
            return False
        if key == "stack" and value not in context.stack:
            return False
    return True


def resolve_bootstrap(blocks: list[BootstrapBlock], context: BootstrapContext) -> BootstrapResult:
    ordered = sorted(blocks, key=lambda block: block.priority, reverse=True)
    loaded_files: list[str] = []
    policies: list[str] = []
    trace: list[str] = []

    for block in ordered:
        if not _matches(block, context):
            trace.append(f"skipped {block.section}")
            continue
        if block.when:
            for key, value in block.when.items():
                trace.append(f"{key} {value} matched")
        else:
            trace.append("core block loaded")
        for directive in block.directives:
            if directive.kind == "load" and directive.value not in loaded_files:
                loaded_files.append(directive.value)
            if directive.kind == "policy" and directive.value not in policies:
                policies.append(directive.value)

    return BootstrapResult(
        loaded_files=loaded_files,
        policies=policies,
        trace=trace,
    )
```

- [ ] **Step 4: Run the resolver tests to verify they pass**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_bootstrap_resolver.py -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Commit**

```powershell
git -C C:\DEV_CORE add Tools\devcore\bootstrap_resolver.py Tests\test_bootstrap_resolver.py
git -C C:\DEV_CORE commit -m "feat: add bootstrap resolver and trace"
```

## Task 5: Expose Bootstrap Resolution Through A CLI

**Files:**
- Create: `C:\DEV_CORE\Tools\devcore\bootstrap_cli.py`
- Create: `C:\DEV_CORE\Tests\test_bootstrap_cli.py`
- Modify: `C:\DEV_CORE\Tools\devcore\cli.py`

- [ ] **Step 1: Write the failing CLI smoke test**

```python
# C:\DEV_CORE\Tests\test_bootstrap_cli.py
from pathlib import Path

from devcore.bootstrap_cli import build_bootstrap_payload


def test_build_bootstrap_payload_resolves_boot_md(tmp_path, monkeypatch):
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
                "## Stack Rules",
                "@when stack=python",
                "@priority 60",
                "@load Skills/python_api.md",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("DEVCORE_PLATFORM_ROOT", str(platform))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(data))

    payload = build_bootstrap_payload(
        cwd=tmp_path / "api_python",
        task_type="review",
        prompt_text="review my python api",
    )

    assert payload["loaded_files"] == [
        "00_Global/AGENTS.md",
        "Skills/python_api.md",
    ]
    assert payload["policies"] == ["concise"]
```

- [ ] **Step 2: Run the CLI test to verify it fails**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_bootstrap_cli.py -q
```

Expected:

```text
E   ModuleNotFoundError: No module named 'devcore.bootstrap_cli'
```

- [ ] **Step 3: Implement the bootstrap CLI helper and hook it into the package CLI**

```python
# C:\DEV_CORE\Tools\devcore\bootstrap_cli.py
from pathlib import Path

from devcore.bootstrap_context import detect_bootstrap_context
from devcore.bootstrap_parser import parse_bootstrap_markdown
from devcore.bootstrap_resolver import resolve_bootstrap
from devcore.paths import get_paths


def build_bootstrap_payload(
    cwd: Path,
    task_type: str | None = None,
    prompt_text: str = "",
) -> dict:
    boot_path = get_paths().platform_root / "Config" / "BOOT.md"
    blocks = parse_bootstrap_markdown(boot_path)
    context = detect_bootstrap_context(cwd=cwd, task_type=task_type, prompt_text=prompt_text)
    result = resolve_bootstrap(blocks, context)
    return {
        "loaded_files": result.loaded_files,
        "policies": result.policies,
        "trace": result.trace,
        "context": {
            "project": context.project,
            "stack": context.stack,
            "moment": context.moment,
            "task_type": context.task_type,
        },
    }
```

```python
# append to C:\DEV_CORE\Tools\devcore\cli.py
from pathlib import Path

from devcore.bootstrap_cli import build_bootstrap_payload


def build_bootstrap_only_payload(
    cwd: str,
    task_type: str | None = None,
    prompt_text: str = "",
) -> dict:
    return build_bootstrap_payload(
        cwd=Path(cwd),
        task_type=task_type,
        prompt_text=prompt_text,
    )
```

- [ ] **Step 4: Run the CLI test and the full suite**

Run:

```powershell
Set-Location C:\DEV_CORE
python -m pytest Tests\test_bootstrap_cli.py -q
python -m pytest Tests -q
```

Expected:

```text
1 passed
All tests pass
```

- [ ] **Step 5: Commit**

```powershell
git -C C:\DEV_CORE add Tools\devcore\bootstrap_cli.py Tools\devcore\cli.py Tests\test_bootstrap_cli.py
git -C C:\DEV_CORE commit -m "feat: expose declarative bootstrap resolution"
```

## Definition Of Done

- `Config/BOOT.md` is declarative and machine-readable
- DEV_CORE can parse `@load`, `@policy`, `@when`, and `@priority`
- DEV_CORE can detect minimal bootstrap context from the current repo/task
- DEV_CORE can resolve bootstrap blocks deterministically
- DEV_CORE produces `loaded_files`, `policies`, and `trace`
- `python -m pytest Tests -q` passes from `C:\DEV_CORE`

## Follow-Up Plans Required

After this slice lands, separate plans should cover:

1. integration of bootstrap resolution into `launch.ps1`
2. French natural-language ask flow consuming bootstrap results
3. richer stack detection from actual repo files instead of repo-name heuristics only
4. context ceiling enforcement against real file lengths rather than only logical selection

## Self-Review

### Spec Coverage

Covered:

- declarative `BOOT.md`
- bounded primitives
- context detector
- resolver
- trace output
- deterministic load order

Deferred:

- advanced integrations
- UI exposure
- natural language front-end
- richer retrieval logic

### Placeholder Scan

No implementation steps contain `TODO`, `TBD`, or placeholder action language.

### Type Consistency

Stable names are used consistently:

- `BootstrapDirective`
- `BootstrapBlock`
- `BootstrapContext`
- `BootstrapResult`
- `loaded_files`
- `policies`
- `trace`
