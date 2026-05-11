# DEV_CORE v5 Final Architecture

Date: 2026-04-23
Status: Final architecture baseline validated in conversation
Scope: Target architecture for a personal local-first AI operating system on one Windows workstation
Supersedes: `2026-04-22-dev-core-v5-design.md` as the cleaner reference architecture

## 1. Intent

DEV_CORE v5 is a personal AI operating system for Windows designed to orchestrate multiple AI engines with:

- durable human-readable memory
- explainable routing
- structured handoffs
- selective context loading
- controlled autonomy

Its purpose is not to accumulate transcripts or automate everything blindly. Its purpose is to compound useful knowledge, reduce token waste, and coordinate the right engine for the right task with visible state and recoverable workflows.

## 2. Positioning

DEV_CORE v5 is:

- local-first
- Windows-native in operations
- file-contract driven
- memory-centric
- semi-automatic first
- extensible toward advanced autonomy

DEV_CORE v5 is not:

- a multi-user enterprise SaaS
- a dashboard-led product
- a hidden fully autonomous orchestrator
- a replacement for human knowledge organization

## 3. Architectural Principle

The architecture is organized in five layers:

1. `Execution Surfaces`
2. `Control Plane`
3. `Memory Fabric`
4. `Learning Layer`
5. `Controlled Autonomy`

The design rule is simple:

`execution happens at the edges, truth lives in memory, coordination lives in the control plane, adaptation lives in learning, and autonomy stays bounded`

## 4. Top-Level Flow

```text
User / Natural Language Task
        |
        v
Execution Surfaces
        |
        v
Control Plane <-> Memory Fabric

Learning Layer
  ^
  |
  +---- scores, telemetry, adaptation signals

Controlled Autonomy
  ^
  |
  +---- bounded suggestions, maintenance, prefill actions
```

Operationally, the main loop is:

`task capture -> bootstrap -> context build -> route -> handoff -> execution -> memory extraction -> memory commit -> scoring -> future adaptation`

This is not a strictly linear runtime stack.

`Learning Layer` and `Controlled Autonomy` are feedback layers that observe and improve the operating loop rather than mandatory stages on every request path.

## 5. Layer 1: Execution Surfaces

Execution surfaces are the user-facing or engine-facing points where work is initiated or performed.

### Components

- `Codex`
- `Antigravity`
- `Obsidian`
- `Launcher / CLI`

### Responsibilities

- accept task entry
- display prepared prompts or handoffs
- execute work in their native environment
- expose outputs back to DEV_CORE through durable artifacts

### Design Rule

Execution surfaces do not own truth and do not define system policy.

They are operating surfaces, not the system brain.

## 6. Layer 2: Control Plane

The control plane is the operational core of DEV_CORE.

### Components

- `Bootstrap Resolver`
- `Context Builder`
- `Router`
- `Handoff Bus`
- `Session Manager`
- `Maintenance Engine`

### Responsibilities

#### Bootstrap Resolver

- interpret declarative `BOOT.md`
- load the smallest stable core
- load conditional context by `project`, `stack`, and `moment`
- produce a deterministic bootstrap trace

#### Context Builder

- assemble minimal useful context before prompt construction
- consume bootstrap output, memory retrieval, and task-local references
- prefer memory-first loading over broad transcript loading
- trim context to relevance ceilings

#### Router

- recommend the best engine for the task
- score by task type, context size, reasoning depth, code intensity, and prior effectiveness
- remain explainable and auditable

#### Handoff Bus

- persist JSON handoff contracts
- separate drafts, receipts, archive, and recoverable states
- enable human review before high-value transmissions

#### Session Manager

- create session folders
- track session state
- support resume and restart-safe recovery

#### Maintenance Engine

- run bounded cleanup and review workflows
- manage memory review queues
- coordinate sync and operational housekeeping

### Design Rule

All critical operational state must be visible on disk.

## 7. Layer 3: Memory Fabric

The memory fabric is the durable knowledge system plus its derived retrieval structures.

### Components

- `Obsidian Canonical Memory`
- `Prompt Library`
- `Skills Library`
- `Basic Memory`
- `Session Summaries`
- `Qdrant Index`
- `Sync Engine`

### Canonical vs Derived vs Ephemeral

#### Canonical

- `Obsidian`

This is the durable human-readable source of truth.

#### Derived

- `Qdrant`
- `Session Summaries`
- retrieval metadata

These can be rebuilt and must never override canonical memory.

#### Ephemeral

- `Basic Memory`
- live session context
- short-lived working summaries

These exist to support the current task, not to define durable truth.

### Responsibilities

#### Obsidian Canonical Memory

Stores:

- decisions
- lessons learned
- architecture notes
- winning prompts
- project snapshots
- weekly reviews
- reusable constraints

#### Prompt Library

Stores reusable prompts that are stable enough to be replayed or adapted later.

It is a knowledge asset, not a runtime surface.

#### Skills Library

Stores specialized operational guidance and reusable execution patterns by domain.

#### Basic Memory

Stores short-lived per-session context, useful working notes, and immediate continuity artifacts.

#### Session Summaries

Store compact digests of completed work.

They are useful for recall and retrieval, but they are not canonical truth.

They should be generated after execution and before long-term memory promotion so they can support review without bypassing human validation.

#### Qdrant Index

Stores embeddings and retrieval metadata derived from approved memory and curated artifacts.

Qdrant must remain rebuildable from higher-trust sources.

#### Sync Engine

- sync approved memory into retrieval structures
- enrich vault structure from validated outputs
- keep derived state aligned with canonical memory

## 8. Layer 4: Learning Layer

The learning layer observes system performance and improves future routing and memory behavior.

### Components

- `Prompt Scoring`
- `Engine Effectiveness Scoring`
- `Task Pattern Detection`
- `Memory Quality Scoring`
- `Predictive Routing`

### Responsibilities

#### Prompt Scoring

- identify prompts that produce high-quality outcomes
- rank prompt patterns by task family

#### Engine Effectiveness Scoring

- compare engine effectiveness by task type
- compare cost, quality, speed, and rework

#### Task Pattern Detection

- observe recurring task classes
- detect active project tendencies
- identify repeatable execution opportunities

#### Memory Quality Scoring

- detect high-value durable memory candidates
- down-rank noisy or low-reuse artifacts

#### Predictive Routing

- recommend likely-best engines before full routing
- adapt recommendations from prior outcomes
- remain bounded by explainable heuristics

### Output Rule

The learning layer writes telemetry, scores, and recommendations.

It does not write canonical truth directly.

### Design Rule

Learning exists to improve selectivity, not to increase noise.

The system should become more precise over time, not more verbose.

## 9. Layer 5: Controlled Autonomy

This layer adds bounded system initiative.

### Components

- `Auto-maintenance`
- `Suggested Handoffs`
- `Suggested Routing`
- `Memory Self-Healing`
- `Guided Self-Learning`

### Responsibilities

#### Auto-maintenance

- clean stale summaries
- refresh indexes
- keep review queues healthy
- detect broken operational states

#### Suggested Handoffs

- prepare handoffs automatically
- prefill target engine, context summary, and references
- require confirmation before send when impact is meaningful

#### Suggested Routing

- propose likely engine and fallback
- optimize operator speed without hiding rationale

#### Memory Self-Healing

- detect duplicates
- detect broken links
- detect stale low-value artifacts
- propose repair actions

#### Guided Self-Learning

- update heuristics from observed outcomes
- improve suggestions without changing canonical memory automatically

### Design Rule

Autonomy is allowed on preparation and maintenance.

Human confirmation remains required for impactful cross-engine actions and truth-changing memory commits.

### Explicit Non-Goals

- no silent engine switching in the middle of a task
- no automatic promotion into canonical memory
- no destructive maintenance without explicit approval

## 10. Source Of Truth Model

DEV_CORE v5 requires a strict source-of-truth hierarchy.

### Truth Table

- `Obsidian` = durable human truth
- `Prompt Library` = curated reusable knowledge
- `Skills` = specialized operational knowledge
- `Basic Memory` = session context
- `Summaries` = temporary digest
- `Qdrant` = derived search index
- `Router Telemetry` = operational truth about system effectiveness

### Rule

If two layers disagree, the higher-trust layer wins:

`Obsidian > curated libraries > router telemetry > summaries/basic memory > Qdrant`

`Router Telemetry` informs operational decisions such as routing and scoring, but it does not override canonical human knowledge.

## 11. Specialized Agents

Persistent specialized agents should be modeled as persistent operating profiles, not as always-running daemons.

### Example Profiles

- `Backend Agent`
- `Frontend Agent`
- `Mobile Agent`
- `Data Agent`
- `Release Agent`
- `Research Agent`

### Each Agent Profile Keeps

- preferences
- templates
- winning prompts
- useful histories
- checklists
- domain patterns

### Rule

Agents are reusable execution identities with bounded memory and behavior patterns.

They do not become independent hidden authorities.

## 12. Routing Model

Routing should combine immediate heuristics and learned signals.

### Immediate Inputs

- task type
- code-edit intensity
- reasoning complexity
- context volume
- urgency
- expected output shape

### Learned Inputs

- engine success rate on similar tasks
- prompt success patterns
- rework frequency
- prior task family outcomes

### Required Output

Every route should expose:

- recommended engine
- confidence
- short rationale
- fallback engine when useful
- rejected alternatives when helpful for trust and debugging

## 13. Memory Learning Model

The memory system should observe:

- frequent task categories
- engine performance by task family
- effective prompts
- recurring failure modes
- active projects

It may then adapt:

- default prompt recommendations
- router priors
- suggested engine ordering
- memory extraction emphasis

It must not silently rewrite canonical human knowledge.

Adaptation should require a minimum evidence threshold before changing routing priors or reusable recommendations.

## 14. Physical Topology

### Platform Root

```text
C:\DEV_CORE
+-- Launcher
+-- Router
+-- Bus
+-- Adapters
+-- MemorySync
+-- Dashboard
+-- Config
+-- Schemas
`-- Scripts
```

### Data Root

```text
C:\DEV_CORE_DATA
+-- Vault
+-- Qdrant
+-- Sessions
+-- Logs
+-- Snapshots
`-- Cache
```

### Separation Rule

- `C:\DEV_CORE` = active platform logic
- `C:\DEV_CORE_DATA` = persistent data, memory, sessions, indexes, logs

### Canonical Storage Mapping

Recommended durable locations:

- `C:\DEV_CORE_DATA\Vault` = canonical Obsidian knowledge
- `C:\DEV_CORE_DATA\Vault\Prompts` = curated prompt library
- `C:\DEV_CORE\Skills` = active operational skills library
- `C:\DEV_CORE_DATA\Memory` = short-lived working memory and maintenance state
- `C:\DEV_CORE_DATA\Sessions` = session folders and execution artifacts
- `C:\DEV_CORE_DATA\Qdrant` = derived vector index
- `C:\DEV_CORE_DATA\Logs\router` = routing telemetry and scoring logs
- `C:\DEV_CORE_DATA\Logs\maintenance` = maintenance and repair logs
- `C:\DEV_CORE_DATA\Vault\05_AI\DEV_CORE\Memory Review` = memory review queue

This mapping should be treated as canonical unless a later migration explicitly replaces it.

## 15. Non-Negotiable Rules

1. `Obsidian` is canonical.
2. `Qdrant` is derived and rebuildable.
3. The router must stay explainable.
4. The bootstrap must stay selective.
5. Handoffs must remain lightweight.
6. Raw transcripts are not the default durable artifact.
7. Memory promotion must prefer reviewed knowledge over raw accumulation.
8. Autonomy must stay bounded and visible.

## 16. Core Of The System

The real core of DEV_CORE v5 is:

- `Bootstrap`
- `Router`
- `Handoff Bus`
- `Session Manager`
- `Obsidian Commit Flow`
- `Qdrant Sync`
- `Scoring Loop`

Dashboard, watchers, and premium analytics are support layers, not the architectural center.

## 17. Final Definition

DEV_CORE v5 is:

`a personal local-first AI operating system for Windows that orchestrates multiple engines through explainable routing, structured handoffs, durable human-readable memory, derived retrieval, and controlled autonomy`

## 18. Recommended Next Design Slices

After this final architecture baseline, the next implementation or design slices should be:

1. French natural-language task capture to `launch.ps1`
2. Bootstrap-driven context assembly integrated into launch flow
3. prompt scoring and router telemetry model
4. memory sync and Qdrant refresh policy
5. specialized agent profile model
6. bounded auto-maintenance workflows
