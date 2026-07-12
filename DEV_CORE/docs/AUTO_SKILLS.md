# DEV_CORE Auto-Skills Implementation

Auto-Skills is the controlled pipeline that turns repeated DEV_CORE events into reviewable skill candidates. It does not directly promote generated skills to active production skills without an explicit `dc skills promote` command.

## Runtime Model

- Static skill definitions live under `DEV_CORE\Skills`.
- The versioned static registry is `DEV_CORE\Skills\skills_registry.json`.
- Runtime usage state lives in `DEV_CORE_DATA\Skills\skills_runtime.json`.
- Generated candidates live in `DEV_CORE_DATA\Skills\Candidates\<skill-name>\SKILL.md`.
- Event evidence is read from `DEV_CORE_DATA\Bus\events\events-*.jsonl`.

This keeps generated and runtime data out of the static skill registry unless a candidate is intentionally registered or promoted.

## Services

| File | Responsibility |
|---|---|
| `DEV_CORE\Scripts\auto_skill_service.ps1` | Detect, list, promote, reject and report Auto-Skills state. |
| `DEV_CORE\Scripts\skill_lint.ps1` | Static gate for generated `SKILL.md` files. |
| `DEV_CORE\Scripts\skill_eval.ps1` | Evidence-based verification against Event Bus history. |
| `DEV_CORE\Scripts\Auto\auto_skills_detector.ps1` | Endday runtime scan for installed skills without mutating the static registry. |
| `DEV_CORE\Scripts\test_auto_skills_pipeline.ps1` | Smoke test for detection, lint, eval, promote, reject and `dc skills` dispatch. |

## CLI

```powershell
dc skills status
dc skills list
dc skills candidates
dc skills detect
dc skills lint <name>
dc skills eval <name>
dc skills promote <name>
dc skills reject <name>
```

The dispatcher routes these commands through `dc.ps1` to `auto_skill_service.ps1`, `skill_lint.ps1`, or `skill_eval.ps1`.

## Detection Flow

1. `auto_skill_service.ps1 -Action Detect` reads JSONL events from the Event Bus.
2. Events are grouped by `event_type` and `source`.
3. A group becomes a candidate when its occurrence count reaches the threshold, default `3`.
4. A candidate `SKILL.md` is generated under `DEV_CORE_DATA\Skills\Candidates`.
5. The static registry receives a disabled entry with `status = "candidate"`, `trust_level = "low"`, `auto_generated = true`, and evidence metadata.

## Gates

`skill_lint.ps1` validates:

- frontmatter exists;
- `name` and `description` are present;
- dangerous command patterns are absent;
- obvious secret literals are absent;
- recommended sections such as `Trigger`, `Workflow`, and `Safety` are present.

Agent Skills compatibility can be checked with:

```powershell
.\DEV_CORE\Scripts\skill_lint.ps1 -Path .\DEV_CORE\Skills\dev-methodology -AgentSpec
.\DEV_CORE\Scripts\skill_lint.ps1 -Path .\DEV_CORE\Skills\dev-methodology -StrictAgentSpec
```

`-AgentSpec` is advisory for legacy DEV_CORE skills. It reports compatibility gaps as warnings so existing internal skills with historical names such as `python_api` or `web_ui` do not break CI.

`-StrictAgentSpec` is blocking and should be used for new promoted skills intended to follow the external Agent Skills package convention:

- folder name must match frontmatter `name`;
- `name` must be lowercase alphanumeric with hyphens only, maximum 64 characters;
- `description` must be present and concise;
- `SKILL.md` should stay focused, with large details moved to `references/`, `scripts/`, or `assets/`;
- deep reference chains are discouraged to preserve progressive disclosure.

`skill_eval.ps1` validates:

- lint is not failing;
- matching Event Bus evidence still exists;
- `success_rate >= 0.75` promotes the candidate to `verified`.

## Promotion

Promotion is explicit:

```powershell
dc skills promote <name>
```

Promotion copies the verified candidate into `DEV_CORE\Skills\<name>\SKILL.md`, updates the registry entry to `status = "active"`, sets `enabled = true`, and raises `trust_level` to `medium`.

## Rejection

```powershell
dc skills reject <name>
```

Rejection keeps traceability in `skills_registry.json` while disabling the candidate with `status = "rejected"` and `enabled = false`.

## Safety Boundaries

- Generated skills are advisory until promotion.
- Detection is evidence-based and threshold-gated.
- Promotion requires lint and evaluation.
- Runtime fields such as `last_checked`, `last_used`, and `usage_count` stay in `DEV_CORE_DATA\Skills\skills_runtime.json`.
- The static registry remains versioned metadata, not a runtime counter store.
