# DEV_CORE French Natural Prompt Parser Design

Date: 2026-04-22
Status: Draft validated in conversation
Scope: French natural-language entry layer for DEV_CORE on Windows

## 1. Intent

This feature adds a French natural-language front door to DEV_CORE.

The user should be able to type a prompt such as:

`corrige le bug du parser Android en urgence, patch minimal`

and have DEV_CORE:

1. interpret the prompt locally with bounded heuristics
2. extract a structured task proposal
3. ask for confirmation
4. launch the existing DEV_CORE flow through `launch.ps1`

The goal is not to replace DEV_CORE routing or execution. The goal is to remove the need to manually write structured arguments.

## 2. Design Position

This is a local, heuristic, bounded parser.

It is:

- local-first
- deterministic enough to debug
- smart on phrasing
- conservative on meaning
- confirmation-based before execution

It is not:

- LLM-assisted
- free-form semantic reasoning
- an autonomous launcher
- a replacement for the DEV_CORE router

## 3. Core Principle

The parser must be:

- intelligent on form
- bounded on interpretation

It should convert French natural phrasing into DEV_CORE launch parameters without inventing hidden intent or making unsafe assumptions.

## 4. Fields In Scope

The parser should infer automatically, when the signal is sufficiently strong:

- `project_id`
- `task_type`
- `intent`
- `context_summary`

The parser should not infer silently:

- routing outcome
- engine choice
- invisible launch approval

These remain downstream responsibilities of DEV_CORE after confirmation.

## 5. Project Detection Strategy

`project_id` should be inferred primarily from the current workspace context.

Priority order:

1. current working directory
2. current repository name
3. current folder naming

The parser should not use a manually curated alias dictionary as the primary source.

This means the parser will work best when launched from the target project directory or from a shell tied to that repository.

## 6. Parser Responsibilities

### 6.1 Project Identification

Detect the current project from workspace context and normalize it into a DEV_CORE-compatible `project_id`.

### 6.2 Task Type Classification

Map natural-language signals into a closed task taxonomy such as:

- `bugfix`
- `review`
- `architecture`
- `migration`
- `automation`
- `refactor`

### 6.3 Intent Construction

Rewrite the user prompt into a clean, actionable task statement.

Examples:

- `Corriger le bug du parser Android`
- `Analyser la structure de l'API Python`

### 6.4 Context Summary Construction

Generate a short summary of the situation, preserving only what is useful for a handoff:

- problem nature
- severity if explicit
- execution constraints if explicit

## 7. Recommended Interpretation Order

The parser should evaluate the prompt in this order:

1. inspect workspace context
2. extract linguistic action signals
3. map to bounded DEV_CORE fields
4. compute confidence
5. require confirmation before launch

This ordering prevents the parser from overfitting on wording while ignoring the actual current project context.

## 8. Heuristics

### 8.1 Task Type Mapping

Recommended mappings:

- `corrige`, `bug`, `erreur`, `crash` -> `bugfix`
- `revue`, `review`, `audit` -> `review`
- `archi`, `architecture`, `design` -> `architecture`
- `migration`, `convertir`, `bulk` -> `migration`
- `automatiser`, `script`, `batch` -> `automation`
- `refactor`, `nettoyer`, `simplifier` -> `refactor`

### 8.2 Intent Generation

Intent should preserve:

- main verb
- main object

Intent should not preserve:

- unnecessary prompt filler
- duplicated urgency markers
- conversational noise

### 8.3 Context Summary Generation

The summary should preserve:

- short description of the issue or goal
- severity when explicit
- notable constraint such as `patch minimal`

The summary should stay short enough to remain useful for handoff.

## 9. Confidence And Ambiguity

The parser must track confidence.

If confidence is low, ambiguous, or contradictory, it should not silently proceed as if it fully understands the request.

Expected behavior:

- propose interpreted fields
- request confirmation
- surface ambiguity rather than hide it

Examples of ambiguity:

- no clear project context
- extremely vague prompt
- contradictory signals such as minor fix plus full migration language

## 10. Confirmation Rule

The confirmed design choice is:

- parse automatically
- show the structured interpretation
- require confirmation before calling `launch.ps1`

This is the non-negotiable safety layer.

The parser should never launch silently from natural language input alone.

## 11. Runtime Flow

Recommended flow:

`French prompt -> local parser -> structured proposal -> user confirmation -> launch.ps1 -> normal DEV_CORE routing`

This keeps the parser separate from downstream orchestration.

## 12. Entry Point Design

The recommended architecture is:

- one shared parser core
- multiple frontends

Recommended frontends:

- `ask.ps1 "<prompt en francais>"`
- `python -m devcore.ask_fr "<prompt en francais>"`

Future UI surfaces such as Codex Desktop or Antigravity should call this shared local entrypoint rather than reimplement the parsing logic independently.

## 13. Separation Of Concerns

The parser layer should be separate from `launch.ps1`.

Recommended role split:

- `ask_fr` understands French natural language
- `launch.ps1` executes the existing structured DEV_CORE pipeline

This separation improves:

- maintainability
- debuggability
- testability
- portability across interfaces

## 14. Surface Behavior

### 14.1 PowerShell

Primary target surface.

This should be the cleanest and most direct usage mode.

### 14.2 Codex Desktop

The user should keep opening the real target repository, not necessarily `C:\DEV_CORE`.

The parser should be callable through the same local command flow, ideally from the integrated terminal or equivalent local launch path.

### 14.3 Antigravity

Same principle as Codex Desktop:

- no separate parser logic
- call the same local parser entrypoint

## 15. Example Output Contract

Example parser output before launch:

```json
{
  "raw_prompt_fr": "corrige le bug du parser Android en urgence, patch minimal",
  "project_id": "android_tooling",
  "task_type": "bugfix",
  "intent": "Corriger le bug du parser Android",
  "context_summary": "Bug urgent sur le parser Android avec attente de patch minimal",
  "confidence": 0.86,
  "needs_confirmation": true
}
```

This object should not itself perform execution.

It is the confirmation payload for the user-facing frontend.

## 16. Example Confirmation UX

Example:

```text
Prompt:
"corrige le bug du parser Android en urgence, patch minimal"

Interpretation:
- project_id: android_tooling
- task_type: bugfix
- intent: Corriger le bug du parser Android
- context_summary: Bug urgent sur le parser Android avec attente de patch minimal

Commande:
launch.ps1 -ProjectId android_tooling -TaskType bugfix -Intent "Corriger le bug du parser Android" -ContextSummary "Bug urgent sur le parser Android avec attente de patch minimal"

Confirmer le lancement ? [Y/n]
```

## 17. Non-Goals

This feature does not include:

- model-based interpretation
- direct engine selection
- autonomous execution without confirmation
- project alias registry as primary project lookup
- replacing the router

## 18. Recommended Implementation Slice

The first implementation slice should include:

1. parser core module for French prompt interpretation
2. workspace-based project detection
3. bounded task-type mapping
4. confirmation payload rendering
5. PowerShell frontend that calls `launch.ps1` after confirmation

Codex Desktop and Antigravity integration should reuse the same core later.

## 19. Constraints Noted During Design

- the parser must work best from the real project workspace
- DEV_CORE remains the control plane, not the primary repo to open for all tasks
- confirmation before execution is mandatory
