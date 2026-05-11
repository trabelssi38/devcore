# DEV_CORE Declarative Bootstrap Design

Date: 2026-04-23
Status: Draft validated in conversation
Scope: Declarative `BOOT.md` bootstrap system for DEV_CORE

## 1. Intent

This feature turns `Config/BOOT.md` from a simple note into a declarative bootstrap specification that DEV_CORE can interpret automatically.

The goal is to support a single stable entry prompt while loading the right rules, memory, and operational guidance according to:

- current project
- technical stack
- work moment such as daily planning context

This is meant to reduce repetition, stabilize behavior across sessions, and lower token waste.

## 2. Problem Being Solved

Without a bootstrap layer, each session tends to repeat:

- style rules
- token discipline
- context-loading behavior
- routing expectations
- project-specific constraints

A declarative bootstrap solves this by making the load policy explicit and machine-readable.

## 3. Design Position

The chosen design is:

- `BOOT.md` remains human-readable Markdown
- it contains a bounded set of declarative directives
- DEV_CORE interprets those directives automatically

This is not a free-form “read and guess” system.

The parser should only act on known bootstrap primitives.

## 4. Core Principle

The bootstrap should load:

- the smallest stable core
- the most relevant conditional context
- nothing else

The value comes from selective loading, not maximal loading.

## 5. Why Markdown Enriched

The selected format is enriched Markdown rather than YAML or JSON.

Reasons:

- readable by humans
- easy to edit directly
- remains a first-class operational document
- still structured enough for a bounded parser

## 6. Bootstrap Primitives

The runtime should support a small set of stable primitives.

### 6.1 `@load`

Loads a specific file.

Example:

```md
@load 00_Global/AGENTS.md
```

### 6.2 `@policy`

Activates a stable internal bootstrap policy.

Examples:

```md
@policy memory_first
@policy concise
@policy intelligent_routing
```

### 6.3 `@when`

Creates a conditional block that applies only when the current session matches the declared context.

Supported dimensions should include:

- `project`
- `stack`
- `moment`
- optionally later `task_type`

Examples:

```md
@when project=android_tooling
@when stack=python
@when moment=daily
```

### 6.4 `@priority`

Defines relative precedence between matching blocks.

This exists to keep resolution deterministic when multiple blocks match.

## 7. What The Bootstrap Must Not Become

The bootstrap must not become:

- a complex DSL
- a scripting language
- a free-form natural language parser
- a hidden full-vault preloader

Plain prose may exist in `BOOT.md`, but only recognized directives should control machine behavior.

## 8. Recommended BOOT Structure

Recommended top-level structure:

```md
# DEV_CORE Bootstrap

## Core
@load 00_Global/AGENTS.md
@load 00_Global/TOKEN_RULES.md
@policy concise
@policy memory_first

## Project Rules
@when project=android_tooling
@priority 80
@load Skills/android_release.md

## Stack Rules
@when stack=python
@priority 60
@load Skills/python_api.md

## Work Moment Rules
@when moment=daily
@priority 40
@load Daily/latest.md
```

## 9. Loadable Source Policy

The bootstrap should load from a constrained source set.

### 9.1 Allowed By Default

- short global rule files such as `AGENTS.md`
- short token discipline files such as `TOKEN_RULES.md`
- project-specific rules
- stack-specific rules
- a current-day note only when relevant

### 9.2 Not Allowed By Default

- full vault scans
- arbitrary historical daily notes
- large raw files with no summarization
- broad context “just in case”

## 10. Relevance Rules

### 10.1 Project Relevance

Project-specific blocks should load only when the current project is detected with sufficient confidence.

### 10.2 Stack Relevance

Stack blocks should load only when the repository or task signals a real technical match.

### 10.3 Moment Relevance

Daily or time-based blocks should load only when the task is about:

- planning
- blockers
- follow-up
- coaching
- daily review

Daily context should not load automatically for every engineering task.

## 11. Context Ceilings

Recommended ceilings:

- always one compact core block
- at most one project block
- at most one or two stack blocks
- at most one time-based block

The runtime should deduplicate and trim before assembling final context.

## 12. Runtime Engine Responsibilities

The bootstrap runtime should:

1. detect current session context
2. parse `BOOT.md`
3. resolve matching blocks
4. apply priorities
5. remove duplicates
6. produce a final ordered load list
7. record a trace of why blocks were loaded or skipped

## 13. Required Input Context

The runtime does not need full task state.

A minimal input object is sufficient:

```json
{
  "project": "android_tooling",
  "stack": ["android", "kotlin"],
  "moment": "daily",
  "task_type": "bugfix"
}
```

## 14. Resolution Order

Recommended resolution order:

1. core
2. project
3. stack
4. moment
5. deduplicate and trim

Reasoning:

- core is stable and always loaded
- project is more specific than stack
- stack is more specific than general time context
- moment should refine the session, not redefine its base

## 15. Determinism Rules

The same input context should always produce the same resolved bootstrap output.

This requires:

- stable directive syntax
- explicit priorities where overlap is possible
- deterministic fallback ordering

## 16. Error Handling

### 16.1 Missing File

If a referenced file is missing, the runtime should log the issue and continue rather than crashing the entire session.

### 16.2 Multiple Matching Blocks

If several same-level blocks match, the runtime should resolve them through:

1. explicit priority
2. deterministic source order

### 16.3 Context Overflow

If the candidate load set exceeds context ceilings, the runtime must stop adding lower-priority material.

## 17. Traceability

The runtime should expose a trace such as:

```text
Matched:
- Core
- project=android_tooling
- stack=android
- moment=daily

Skipped:
- stack=python
- project=api_python

Final load order:
1. 00_Global/AGENTS.md
2. 00_Global/TOKEN_RULES.md
3. Skills/android_release.md
4. Daily/latest.md
```

This is essential for debugging and trust.

## 18. Internal Output Shape

Recommended internal output:

```json
{
  "loaded_files": [
    "00_Global/AGENTS.md",
    "00_Global/TOKEN_RULES.md",
    "Skills/android_release.md",
    "Daily/latest.md"
  ],
  "policies": [
    "memory_first",
    "concise",
    "intelligent_routing"
  ],
  "trace": [
    "core block loaded",
    "project android_tooling matched",
    "stack android matched",
    "moment daily matched"
  ]
}
```

## 19. Operational Benefit

This bootstrap design gives DEV_CORE:

- stable session setup
- fewer repeated instructions
- more coherent routing behavior
- memory-first context loading
- lower token waste
- better observability of what was actually loaded

## 20. Non-Goals

This design does not include:

- full semantic reasoning over arbitrary Markdown prose
- automatic loading of broad vault history
- hidden autonomous behavior
- project alias registry as a mandatory bootstrap dependency

## 21. Recommended First Implementation Slice

The first implementation slice should cover:

1. parser for bootstrap directives inside `BOOT.md`
2. context detector for project / stack / moment
3. load resolver with priority ordering
4. deduplication and context ceiling enforcement
5. trace output for debugging

## 22. Constraints Noted During Design

- `BOOT.md` must stay readable enough for direct human editing
- the system must prefer selective loading over broad loading
- the bootstrap runtime must remain deterministic and explainable
