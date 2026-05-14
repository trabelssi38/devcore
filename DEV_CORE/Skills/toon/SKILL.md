# TOON Skill -- DEV_CORE v6.1
# Token-Oriented Object Notation pour reduction tokens 30-60%

## Overview

TOON (Token-Oriented Object Notation) est un format compact pour LLM prompts.
- Spec: https://toonformat.dev/
- NPM: `@toon-format/toon`

## Installation

```bash
npm install @toon-format/toon -g
```

## Syntaxe TOON

```toon
# Objects (YAML-like)
context:
  task: Spec + Plan implementation
  mode: reasoning
  budget: 32k

# Arrays tabulaires (CSV-like)
tasks[3]{id,title,status}:
  T-01,Spec + Plan,done
  T-02,Implementation TDD,active
  T-03,Tests bulk,todo
```

## Conversion

```bash
# JSON -> TOON
toon encode --input data.json --output data.toon

# TOON -> JSON
toon decode --input data.toon --output data.json
```

## Integration DEV_CORE

### 1. Tasks (tasks.json -> tasks.toon)

```powershell
# Convertir tasks.json en TOON
$json = Get-Content "$DEV_CORE_DATA\Memory\tasks.json" -Raw | ConvertFrom-Json
$toon = toon encode (($json | ConvertTo-Json -Depth 10))
Set-Content "$DEV_CORE_DATA\Memory\tasks.toon" $toon
```

### 2. Session Context TOON

```toon
session:
  active_task: T-02
  mode: coding
  budget: 8k
  project: cea_dashboard
  steps_done: 2
  steps_total: 5
```

### 3. Qdrant payloads

Stocker les decisions en TOON pour economiser des tokens sur les queries.

## Quand utiliser TOON vs JSON

| Cas | Format |
|-----|--------|
| Arrays uniformes (>5 items) | TOON |
| Donnees tabulaires | TOON |
| Config deeply nested | JSON |
| API responses | JSON |
| Memory/Decisions | TOON |
| Session context | TOON |
| LLM prompts input | TOON |

## Commands

```bash
dc toon encode <file>    # JSON -> TOON
dc toon decode <file>    # TOON -> JSON
dc toon convert-tasks   # tasks.json -> tasks.toon
dc toon session          # Affiche session en TOON
```
