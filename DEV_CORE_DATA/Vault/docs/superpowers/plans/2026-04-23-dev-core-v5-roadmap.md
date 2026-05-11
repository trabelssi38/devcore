# DEV_CORE v5 Roadmap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decompose the final DEV_CORE v5 architecture into realistic implementation slices that can be shipped incrementally on one Windows workstation.

**Architecture:** This roadmap treats DEV_CORE v5 as a layered system that should be built from the control plane outward. The sequence is deliberate: first stabilize the runtime core, then improve context quality and routing telemetry, then add memory sync and specialized profiles, and only after that add bounded autonomy.

**Tech Stack:** PowerShell 7, Python 3.11+, Markdown, JSON, local filesystem contracts on Windows, Obsidian vault, Qdrant, local desktop AI surfaces

---

## Scope Split

The final architecture spans multiple subsystems that should not be implemented as one giant plan.

This roadmap defines the implementation order for:

1. `Control Plane Core`
2. `Bootstrap-Driven Context`
3. `Natural-Language Task Capture`
4. `Router Telemetry And Prompt Scoring`
5. `Memory Sync And Qdrant Refresh`
6. `Specialized Agent Profiles`
7. `Bounded Auto-Maintenance`
8. `Controlled Autonomy`

This roadmap is a master sequencing plan.

Each slice after the already-written ones should produce its own detailed implementation plan before code execution.

## Existing Plans Already Available

These plans already exist and should be treated as the starting baseline:

- `C:\DEV_CORE_DATA\Vault\docs\superpowers\plans\2026-04-22-dev-core-v5-foundation.md`
- `C:\DEV_CORE_DATA\Vault\docs\superpowers\plans\2026-04-23-dev-core-declarative-bootstrap-foundation.md`

The roadmap below assumes:

- the foundation slice is implemented on `C:\DEV_CORE`
- the declarative bootstrap slice is implemented next or is in progress

## File Structure

### Canonical roadmap and plan files

- Create: `C:\DEV_CORE_DATA\Vault\docs\superpowers\plans\2026-04-23-dev-core-v5-roadmap.md`
- Reuse: `C:\DEV_CORE_DATA\Vault\docs\superpowers\plans\2026-04-22-dev-core-v5-foundation.md`
- Reuse: `C:\DEV_CORE_DATA\Vault\docs\superpowers\plans\2026-04-23-dev-core-declarative-bootstrap-foundation.md`

### Future plan files to write from this roadmap

- Create later: `C:\DEV_CORE_DATA\Vault\docs\superpowers\plans\2026-04-23-dev-core-fr-launch-flow.md`
- Create later: `C:\DEV_CORE_DATA\Vault\docs\superpowers\plans\2026-04-23-dev-core-router-telemetry-and-scoring.md`
- Create later: `C:\DEV_CORE_DATA\Vault\docs\superpowers\plans\2026-04-23-dev-core-memory-sync-qdrant.md`
- Create later: `C:\DEV_CORE_DATA\Vault\docs\superpowers\plans\2026-04-23-dev-core-agent-profiles.md`
- Create later: `C:\DEV_CORE_DATA\Vault\docs\superpowers\plans\2026-04-23-dev-core-auto-maintenance.md`
- Create later: `C:\DEV_CORE_DATA\Vault\docs\superpowers\plans\2026-04-23-dev-core-controlled-autonomy.md`

### Responsibility map

- `v5 foundation` plan: stable runtime core
- `bootstrap foundation` plan: deterministic context bootstrap
- `fr launch flow` plan: natural-language French input to structured launch
- `router telemetry and scoring` plan: learning-layer foundation
- `memory sync qdrant` plan: memory fabric hardening
- `agent profiles` plan: persistent specialized operating profiles
- `auto-maintenance` plan: bounded maintenance workflows
- `controlled autonomy` plan: suggestion-driven autonomy with safeguards

## Task 1: Lock The Baseline Implementation Order

**Files:**
- Reuse: `C:\DEV_CORE_DATA\Vault\docs\superpowers\plans\2026-04-22-dev-core-v5-foundation.md`
- Reuse: `C:\DEV_CORE_DATA\Vault\docs\superpowers\plans\2026-04-23-dev-core-declarative-bootstrap-foundation.md`

- [ ] **Step 1: Treat the foundation slice as the only required starting point**

Baseline sequence:

1. `v5 foundation`
2. `declarative bootstrap foundation`

Reason:

- foundation establishes paths, contracts, router, sessions, memory review, adapters, and launcher
- bootstrap adds deterministic context loading on top of the stable core

- [ ] **Step 2: Verify both slices align with the final architecture**

Required architecture coverage after these two slices:

- `Bootstrap Resolver`
- `Router`
- `Handoff Bus`
- `Session Manager`
- `Memory Review Queue`
- `Semi-automatic prompt packaging`

Expected result:

```text
The control plane core is operational before any learning or autonomy feature is added.
```

- [ ] **Step 3: Treat all later work as additive, not foundational**

Do not start:

- predictive routing
- autonomous maintenance
- agent profiles
- self-learning memory

until the first two slices are verified stable on disk and in tests.

- [ ] **Step 4: Commit roadmap understanding into working practice**

Execution rule:

```text
No v5 feature may bypass the existing control plane core.
Every later slice must integrate through bootstrap, router, sessions, or memory review contracts.
```

- [ ] **Step 5: Mark baseline order as fixed**

Expected result:

```text
Phase 0 complete:
- foundation first
- bootstrap second
- all later phases build on those contracts
```

## Task 2: Phase 1 - Bootstrap-Driven Launch Flow

**Files:**
- Create later: `C:\DEV_CORE_DATA\Vault\docs\superpowers\plans\2026-04-23-dev-core-fr-launch-flow.md`
- Target areas: `C:\DEV_CORE\Scripts\launch.ps1`, `C:\DEV_CORE\Tools\devcore\cli.py`, new FR parsing modules, bootstrap integration modules

- [ ] **Step 1: Define the outcome of this slice**

This slice must let the user write a natural-language task in French and have DEV_CORE:

1. interpret it locally
2. infer `project_id`, `intent`, `context_summary`, and `task_type`
3. resolve bootstrap context
4. show a confirmation payload
5. launch the existing prepare flow

- [ ] **Step 2: Keep the parser bounded**

Hard constraints:

- local and heuristic
- advanced but bounded understanding
- no hidden external AI dependency
- no silent send

- [ ] **Step 3: Define why this comes before telemetry**

Reason:

- it improves day-to-day usability immediately
- it converts architecture into an actual operator surface
- it exercises bootstrap and router using realistic user input

- [ ] **Step 4: Define acceptance criteria**

This phase is done when:

- French task capture works from one entrypoint
- confirmation remains mandatory
- launch output still produces durable session artifacts
- bootstrap trace is inspectable during launch

- [ ] **Step 5: Write the dedicated implementation plan next**

Plan to write:

`C:\DEV_CORE_DATA\Vault\docs\superpowers\plans\2026-04-23-dev-core-fr-launch-flow.md`

## Task 3: Phase 2 - Router Telemetry And Prompt Scoring

**Files:**
- Create later: `C:\DEV_CORE_DATA\Vault\docs\superpowers\plans\2026-04-23-dev-core-router-telemetry-and-scoring.md`
- Target areas: router logs, scoring files, telemetry storage, review surfaces

- [ ] **Step 1: Define the outcome of this slice**

This slice must create the first real `Learning Layer` foundation without changing canonical truth.

It should track:

- task family
- chosen engine
- fallback
- confidence
- outcome status
- rework signal
- useful prompt pattern

- [ ] **Step 2: Keep telemetry operational, not canonical**

Rules:

- telemetry informs routing
- telemetry never rewrites Obsidian
- telemetry is stored as logs or score artifacts, not as durable truth notes

- [ ] **Step 3: Define why this follows the FR launch flow**

Reason:

- telemetry is more valuable once real launch usage exists
- better user entry means better signal collection
- scoring should observe real flows, not synthetic ones

- [ ] **Step 4: Define acceptance criteria**

This phase is done when:

- router decisions are logged durably
- outcomes can be linked back to task family
- prompt patterns can be scored
- a future predictive router can consume the data without schema rewrite

- [ ] **Step 5: Write the dedicated implementation plan**

Plan to write:

`C:\DEV_CORE_DATA\Vault\docs\superpowers\plans\2026-04-23-dev-core-router-telemetry-and-scoring.md`

## Task 4: Phase 3 - Memory Sync And Qdrant Refresh

**Files:**
- Create later: `C:\DEV_CORE_DATA\Vault\docs\superpowers\plans\2026-04-23-dev-core-memory-sync-qdrant.md`
- Target areas: memory sync scripts, Qdrant refresh worker, vault mapping, summary promotion rules

- [ ] **Step 1: Define the outcome of this slice**

This slice must make the `Memory Fabric` reliable rather than aspirational.

It should support:

- approved memory promotion into Obsidian structures
- Qdrant refresh from approved sources
- rebuildable index behavior
- explicit handling of summaries vs canonical notes

- [ ] **Step 2: Preserve the source-of-truth hierarchy**

Rules:

- Obsidian remains canonical
- summaries remain temporary
- Qdrant remains derived
- sync failures must not corrupt canonical notes

- [ ] **Step 3: Define why this comes after telemetry**

Reason:

- memory quality improves when router outcomes and useful prompt data already exist
- scoring signals can help prioritize what is worth storing

- [ ] **Step 4: Define acceptance criteria**

This phase is done when:

- approved notes are synced predictably
- Qdrant can be refreshed from approved artifacts
- index rebuild path is documented and testable
- memory promotion remains human-reviewed

- [ ] **Step 5: Write the dedicated implementation plan**

Plan to write:

`C:\DEV_CORE_DATA\Vault\docs\superpowers\plans\2026-04-23-dev-core-memory-sync-qdrant.md`

## Task 5: Phase 4 - Specialized Agent Profiles

**Files:**
- Create later: `C:\DEV_CORE_DATA\Vault\docs\superpowers\plans\2026-04-23-dev-core-agent-profiles.md`
- Target areas: profile schema, profile storage, launcher integration, routing hooks

- [ ] **Step 1: Define the outcome of this slice**

This slice must introduce specialized persistent operating profiles such as:

- Backend
- Frontend
- Mobile
- Data
- Release
- Research

- [ ] **Step 2: Keep profiles bounded**

Profiles may contain:

- preferences
- templates
- checklists
- winning prompts
- domain-specific patterns

Profiles must not become:

- hidden autonomous agents
- uncontrolled memory accumulators
- alternate truth stores

- [ ] **Step 3: Define why this follows memory sync**

Reason:

- profiles should load from stable curated memory and prompts
- without a stable memory fabric, profiles become noisy and untrustworthy

- [ ] **Step 4: Define acceptance criteria**

This phase is done when:

- profile selection is explicit
- profile data is durable and inspectable
- profile influence on bootstrap or routing is visible
- profiles remain subordinate to canonical memory and router rules

- [ ] **Step 5: Write the dedicated implementation plan**

Plan to write:

`C:\DEV_CORE_DATA\Vault\docs\superpowers\plans\2026-04-23-dev-core-agent-profiles.md`

## Task 6: Phase 5 - Bounded Auto-Maintenance

**Files:**
- Create later: `C:\DEV_CORE_DATA\Vault\docs\superpowers\plans\2026-04-23-dev-core-auto-maintenance.md`
- Target areas: maintenance scripts, queue inspection, stale artifact cleanup, repair suggestions

- [ ] **Step 1: Define the outcome of this slice**

This slice must automate low-risk maintenance only.

Examples:

- stale summary cleanup
- queue health checks
- missing link detection
- pending review backlog surfacing
- Qdrant refresh health checks

- [ ] **Step 2: Keep actions reversible**

Rules:

- prefer proposals and logs over silent deletion
- destructive cleanup requires explicit approval
- all maintenance actions must write durable logs

- [ ] **Step 3: Define why this follows agent profiles**

Reason:

- maintenance should understand the stabilized storage model
- by this point the system has enough durable structure to maintain

- [ ] **Step 4: Define acceptance criteria**

This phase is done when:

- maintenance checks can run safely
- suggested repairs are inspectable
- logs show what was checked and what was changed
- no canonical memory is modified without approval

- [ ] **Step 5: Write the dedicated implementation plan**

Plan to write:

`C:\DEV_CORE_DATA\Vault\docs\superpowers\plans\2026-04-23-dev-core-auto-maintenance.md`

## Task 7: Phase 6 - Controlled Autonomy

**Files:**
- Create later: `C:\DEV_CORE_DATA\Vault\docs\superpowers\plans\2026-04-23-dev-core-controlled-autonomy.md`
- Target areas: suggestion engine, confirmation UX, auto-prefill, bounded autonomy policies

- [ ] **Step 1: Define the outcome of this slice**

This slice must add bounded initiative without violating the architecture.

Allowed targets:

- suggested routing
- suggested handoffs
- auto-prefill of task metadata
- guided maintenance proposals

- [ ] **Step 2: Keep the non-goals explicit**

Not allowed:

- silent engine switching mid-task
- autonomous promotion to canonical memory
- destructive maintenance without approval
- invisible orchestration that bypasses disk-visible state

- [ ] **Step 3: Define why this is the final phase**

Reason:

- autonomy is only useful after routing, memory, telemetry, and profiles are already trustworthy
- otherwise the system automates weak decisions and multiplies noise

- [ ] **Step 4: Define acceptance criteria**

This phase is done when:

- suggestions are useful and inspectable
- confirmations gate impactful actions
- autonomy remains bounded by policy files and logs
- the system is faster without becoming opaque

- [ ] **Step 5: Write the dedicated implementation plan**

Plan to write:

`C:\DEV_CORE_DATA\Vault\docs\superpowers\plans\2026-04-23-dev-core-controlled-autonomy.md`

## Task 8: Delivery Sequence And Go/No-Go Gates

**Files:**
- This roadmap only

- [ ] **Step 1: Define the official execution sequence**

Execution order:

1. `2026-04-22-dev-core-v5-foundation.md`
2. `2026-04-23-dev-core-declarative-bootstrap-foundation.md`
3. `2026-04-23-dev-core-fr-launch-flow.md`
4. `2026-04-23-dev-core-router-telemetry-and-scoring.md`
5. `2026-04-23-dev-core-memory-sync-qdrant.md`
6. `2026-04-23-dev-core-agent-profiles.md`
7. `2026-04-23-dev-core-auto-maintenance.md`
8. `2026-04-23-dev-core-controlled-autonomy.md`

- [ ] **Step 2: Define the gate for entering each phase**

A phase can start only when:

- previous phase tests pass
- disk-visible artifacts are verified
- contract names are stable
- no unresolved architecture contradiction remains

- [ ] **Step 3: Define the go/no-go rule**

If a phase reveals a broken lower layer:

- stop
- fix the lower layer
- do not stack speculative features on top

- [ ] **Step 4: Define the release mindset**

Release rule:

```text
Ship small working layers.
Do not build learning or autonomy on an unstable core.
Prefer observable usefulness over architectural theater.
```

- [ ] **Step 5: Mark roadmap complete**

Expected result:

```text
DEV_CORE v5 now has an implementation sequence that respects architecture boundaries and reduces integration risk.
```

## Definition Of Done

- the roadmap defines a fixed execution order for v5
- each phase has a clear purpose, dependency order, and acceptance target
- the roadmap reuses existing plans instead of duplicating them
- later autonomy work is explicitly gated behind stable control plane and memory slices
- the roadmap is ready to spawn the next detailed implementation plan

## Follow-Up Plans Required

Write these plans in order:

1. `2026-04-23-dev-core-fr-launch-flow.md`
2. `2026-04-23-dev-core-router-telemetry-and-scoring.md`
3. `2026-04-23-dev-core-memory-sync-qdrant.md`
4. `2026-04-23-dev-core-agent-profiles.md`
5. `2026-04-23-dev-core-auto-maintenance.md`
6. `2026-04-23-dev-core-controlled-autonomy.md`

## Self-Review

### Spec Coverage

Covered by the roadmap:

- control plane first
- memory fabric hardening before autonomy
- learning layer after real runtime usage exists
- specialized agent profiles as bounded operating profiles
- controlled autonomy only after lower layers stabilize

Deferred into dedicated plans:

- exact code tasks for each future slice
- precise file-by-file implementation details for post-bootstrap phases

### Placeholder Scan

No `TODO`, `TBD`, or filler placeholders are used.

Future plan filenames are explicit and ordered.

### Type Consistency

The roadmap consistently uses the same architectural names:

- `Control Plane`
- `Memory Fabric`
- `Learning Layer`
- `Controlled Autonomy`
- `Router Telemetry`
- `Agent Profiles`
