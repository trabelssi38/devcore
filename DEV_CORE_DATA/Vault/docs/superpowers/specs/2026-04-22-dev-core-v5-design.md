# DEV_CORE v5 Design

Date: 2026-04-22
Status: Draft validated in conversation
Scope: North star architecture for a personal AI operating system on one Windows workstation

## 1. Intent

DEV_CORE v5 is a personal AI operating system for Windows built around three primary capabilities:

- intelligent routing across `Claude`, `Codex`, and `Gemini`
- durable memory with `Obsidian` as source of truth and `Qdrant` as derived retrieval index
- lightweight JSON handoffs with minimal manual copy-paste

This is not an enterprise multi-user platform. It is a high-power personal system designed to coordinate multiple AI engines, preserve useful work across sessions, and reduce token waste through structured retrieval and memory extraction.

## 2. Product Position

DEV_CORE v5 is:

- a local-first Windows control system
- desktop and CLI oriented before any API-native integration
- semi-automatic rather than fully autonomous
- file-contract driven rather than process-state driven
- memory-centric rather than transcript-centric

DEV_CORE v5 is not:

- a fully invisible orchestrator
- an API-first platform
- a vector database product
- a dashboard-first system
- a company-grade multi-user governance stack

## 3. Non-Negotiable Principles

1. `Obsidian` is the canonical knowledge base.
2. `Qdrant` is derived, rebuildable, and never the source of truth.
3. No engine is the permanent center of execution.
4. Every important execution state must be visible on disk.
5. Handoffs must stay lightweight and explainable.
6. Memory is extracted after work; raw transcripts are not the default retained artifact.
7. High-value inter-engine actions remain human-confirmed.

## 4. Logical Architecture

### 4.1 Top-Level Flow

`Launcher -> Router -> Handoff Bus -> Engine Adapter -> Memory Fabric`

### 4.2 Core Components

#### Launcher

Single user entry layer for:

- task capture
- project selection or detection
- resume previous session
- review pending memory items
- approve handoff recommendations

The launcher is the operating surface, not the brain.

#### Portfolio Router

Decision engine that recommends the best target engine per task. It has no permanent engine default.

The router evaluates:

- task type
- complexity
- context volume
- need for code modification versus reasoning
- prior effectiveness for similar tasks
- expected token pressure

Its job is recommendation and preparation, not opaque execution.

#### Handoff Bus

File-based bus for structured handoffs between the DEV_CORE control plane and local AI surfaces.

It provides:

- standard JSON contracts
- durable draft and sent states
- auditability
- restart-safe recovery
- adapter isolation

#### Engine Adapters

Per-engine integration layer for `Claude`, `Codex`, and `Gemini`.

Adapters translate generic handoff contracts into engine-specific interaction surfaces such as:

- desktop app workflows
- CLI prompts
- watched folder patterns
- local session packaging

The router must depend on adapters, never on engine-specific behavior directly.

#### Memory Fabric

Post-session memory processing pipeline that:

- extracts reusable knowledge from completed work
- proposes memory candidates for user validation
- writes approved knowledge into Obsidian
- refreshes Qdrant embeddings from approved memory artifacts

This is the long-term compounding mechanism of the system.

## 5. Daily Runtime Loop

### 5.1 Task Capture

Input sources may include:

- launcher actions
- terminal work
- Obsidian notes
- project files

The captured task should remain short and stable.

### 5.2 Context Build

Before any heavy prompt construction, DEV_CORE performs retrieval-first context assembly:

- project-scoped notes from Obsidian
- previous summaries
- decisions and known constraints
- focused references from code or documents

This layer exists primarily to reduce token waste.

### 5.3 Routing Decision

The router selects the best-fit engine and prepares a lightweight handoff JSON. The user validates before send.

This preserves trust and prevents low-visibility cross-engine mistakes.

### 5.4 Execution Session

The selected engine performs the work. DEV_CORE stores only the metadata and artifacts required for:

- traceability
- resume support
- memory extraction
- later retrieval

### 5.5 Memory Extraction

At session end, DEV_CORE proposes:

- decisions
- lessons learned
- winning prompt patterns
- reusable constraints
- next steps

The system should not default to storing raw transcripts.

### 5.6 Commit to Memory

Approved memory is written to Obsidian first, then indexed into Qdrant.

This guarantees:

- human-readable durable knowledge
- rebuildable retrieval state
- reduced drift between truth and index

## 6. Physical Topology

### 6.1 Platform Root

```text
C:\DEV_CORE
+-- Launcher
+-- Router
+-- Bus
|   +-- inbox
|   +-- outbox
|   +-- drafts
|   +-- receipts
|   `-- archive
+-- Adapters
|   +-- Claude
|   +-- Codex
|   `-- Gemini
+-- MemorySync
+-- Dashboard
+-- Config
+-- Schemas
`-- Scripts
```

### 6.2 Persistent Data Root

```text
C:\DEV_CORE_DATA
+-- Vault
+-- Qdrant
+-- Sessions
+-- Logs
+-- Snapshots
`-- Cache
```

### 6.3 Physical Separation Rule

- `C:\DEV_CORE` contains the active platform logic
- `C:\DEV_CORE_DATA` contains durable data and rebuildable state

This separation improves resilience, backup policy clarity, and maintenance.

## 7. File Contracts

### 7.1 Handoff Contract

Minimal required fields:

```json
{
  "handoff_id": "hf_2026_04_22_001",
  "project_id": "android_tooling",
  "task_type": "bugfix",
  "target_engine": "codex",
  "intent": "Corriger la regression du parser",
  "context_refs": [
    "obsidian://08_Bugs/parser-crash.md",
    "file://C:/DEV_CORE_DATA/Projects/android_tool/src/parser.kt"
  ],
  "context_summary": "Crash reproductible sur inputs vides",
  "constraints": [
    "patch minimal",
    "ne pas casser API publique"
  ],
  "expected_output": "patch + explication courte + risques",
  "prepared_at": "2026-04-22T20:00:00Z"
}
```

Design rule: this must remain a portable work order, not a full transcript dump.

### 7.2 Receipt Contract

Minimal required fields:

```json
{
  "handoff_id": "hf_2026_04_22_001",
  "engine": "codex",
  "status": "completed",
  "artifact_refs": [
    "file://C:/DEV_CORE_DATA/Sessions/hf_2026_04_22_001/answer.md"
  ],
  "memory_candidates": [
    "Cause racine: null check manquant",
    "Prompt efficace: demander patch minimal + risques"
  ],
  "next_action": "review_and_commit"
}
```

The receipt proposes memory. It does not directly define truth.

### 7.3 Session Folder Contract

```text
C:\DEV_CORE_DATA\Sessions\hf_2026_04_22_001
+-- request.json
+-- router-decision.json
+-- adapter-payload.json
+-- response.md
+-- receipt.json
`-- memory-draft.md
```

Each significant task should have a recoverable session directory.

## 8. Memory Model

### 8.1 Canonical Memory

Obsidian stores:

- decisions
- architecture notes
- bug learnings
- winning prompts
- project summaries
- reusable execution patterns

### 8.2 Derived Retrieval

Qdrant stores embeddings and retrieval metadata derived from approved Obsidian content and curated session artifacts.

Qdrant can be rebuilt. Obsidian cannot be treated as disposable.

### 8.3 Memory Quality Rule

Only store artifacts that are:

- reusable
- stable enough to matter later
- understandable without the full original conversation

## 9. Control Plane

### 9.1 Required Control Objects

- router decision log
- session registry
- memory review queue

### 9.2 Session States

Recommended states:

- `draft`
- `ready`
- `sent`
- `returned`
- `archived`

The states must be explicit and durable on disk.

### 9.3 Safety Rules

- no important inter-engine handoff without explicit human confirmation
- invalid JSON contracts do not send
- low-confidence retrieval must trigger context enrichment, not context bloat
- poor-quality responses should not become memory by default

## 10. Failure Handling

### 10.1 Engine Unavailable

The router recommends an alternative engine with an explicit fallback rationale.

### 10.2 Incomplete Handoff

Schema validation prevents send. The item remains in `draft`.

### 10.3 Weak Output

The receipt may be flagged low-value and bypass durable memory creation unless manually promoted.

### 10.4 Interrupted Session

The session directory enables restart or manual recovery without rebuilding the entire task from scratch.

## 11. Dashboard, Watchers, and Analytics

These are support layers, not the core of the system.

### 11.1 Dashboard

The dashboard exists to show:

- pending handoffs
- blocked sessions
- memory review backlog
- recent engine usage
- recovery needs

### 11.2 Watchers

Windows watchers should:

- detect relevant file or folder changes
- propose next actions
- help adapters or memory sync react faster

They should not silently redefine memory truth or launch critical autonomous actions without confirmation.

### 11.3 Analytics

Useful metrics include:

- reusable handoff rate
- approved memory rate
- engine effectiveness by task class
- retrieval usefulness
- cognitive overhead avoided

Avoid vanity metrics that do not change behavior.

## 12. Routing Heuristics

The router should remain explainable. Recommended scoring inputs:

- task category
- code-edit intensity
- architecture or reasoning depth
- context breadth
- turnaround urgency
- prior engine success on similar work

Output should include:

- recommended engine
- confidence level
- short rationale
- optional fallback engine

## 13. Why This Design Fits The Chosen Target

This design matches the intended v5 because it is:

- personal rather than organizational
- durable rather than flashy
- local-first rather than integration-heavy
- semi-automatic rather than dangerously autonomous
- memory-compounding rather than transcript-accumulating

The core of the system is not the dashboard, the watchers, or the vector store. The core is:

1. reliable routing
2. stable handoff contracts
3. durable validated memory

## 14. Recommended Next Planning Slice

If this design is approved, the next implementation planning step should decompose v5 into a realistic sequence. The first implementation plan should likely cover:

1. bus schemas and session directory model
2. router decision engine and scoring rules
3. memory extraction and Obsidian commit flow
4. Qdrant indexing pipeline
5. one adapter end-to-end before multi-engine expansion

## 15. Constraints Noted During Design

- current vault is not a git repository, so no design commit was created here
- the architecture intentionally excludes fully autonomous invisible cross-engine execution
- the design assumes Windows as the operating environment and local desktop or CLI surfaces as the primary execution targets
