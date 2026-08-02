# Changelog - DEV_CORE

All notable changes to the **DEV_CORE** platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to Semantic Versioning.

---

## [10.0.0] - 2026-08-02

### Added
- **Supervision Headroom UI Status Badges**: Added explicit `OK (Session Libre)`, `ALERTE (Hors Tâche)`, and `OK` status indicators next to active sessions.
- **Dynamic Cockpit Elements**: Automatic indicator arrows (`▶` / `▼`) on Supervision Headroom and other `<details>` elements using CSS-only attribute selectors.
- **Portability & Isolated Querying**: Repowise health card queries now correctly isolate SQLite database statistics per project rather than leaking `devcore` metrics to other paths.

### Changed
- **Modular Python Refactoring**: Decoupled monolithic scripts into clean, single-responsibility Python packages to reduce cyclomatic complexity (CCN) to 1.0:
  - `gen_dashboard.py` split into [DEV_CORE/Scripts/dashboard/](file:///C:/devcore/DEV_CORE/Scripts/dashboard/).
  - `gemini_router.py` split into [DEV_CORE/Scripts/router/](file:///C:/devcore/DEV_CORE/Scripts/router/).
  - `server.py` MCP server split into [DEV_CORE/MCP/devcore-scripts/handlers/](file:///C:/devcore/DEV_CORE/MCP/devcore-scripts/handlers/) and [services/](file:///C:/devcore/DEV_CORE/MCP/devcore-scripts/services/).
- **Nesting Reduction**: Flattened deeply nested logic (nesting levels down to 3.0) in [task_prompt_analyzer.py](file:///C:/devcore/DEV_CORE/Scripts/Auto/task_prompt_analyzer.py).
- **Tuning Grid Layout**: Grid layout updated to `grid-template-columns: 330px 1fr 555px;` in [template.html](file:///C:/devcore/DEV_CORE/Dashboard/template.html) and [template_terminal.html](file:///C:/devcore/DEV_CORE/Dashboard/template_terminal.html).
- **Supervision Headroom Visibility**: Shifted the `#token-activity-report` container outside the tab panels so it is persistently visible regardless of the active tab.

### Fixed
- **NameError Crash in server.py**: Resolved critical `check_port is not defined` crash at startup.
- **NameError Crash in utils.py**: Added missing `import json` inside `load_project_paths()`.
- **Metrics Service Path Mismatch**: Adjusted `get_metrics_service_status()` path to fetch logs directly from `DEV_CORE_DATA/Logs/metrics` instead of checking the empty `Metrics` directory.

---

## [9.9.5] - 2026-07-28

### Added
- **Multi-Project Worktree Support**: Introduced multi-project loading logic in the dashboard to switch context profiles.
- **Identity & Membership**: Added schema definitions and API logic for managing project identities and credentials.

### Changed
- **Docker Compose Orchestration**: Refactored compose service configurations to leverage local volume mounts to dynamically propagate script updates to running container daemons.

---

## [9.9.0] - 2026-07-22

### Added
- **SSE Live Streaming**: Added Server-Sent Events (SSE) support in the FastAPI `dashboard_api` to stream events in real time without refreshing the client browser.
- **Event Bus v1**: Direct integration of real-time append-only event recording.

### Changed
- **Hermes / Repowise Loopback**: Integrated native scheduled cron execution within the Hermes daemon for periodic health evaluations.

---

## [9.8.0] - 2026-07-15

### Added
- **Diagnostics Gateway**: Gateway validation gate (`dc check`, `dc health`) to ensure system pre-conditions are met.
- **Learning Service v1**: Base repository for extracted lessons learned from workspace sessions.
- **Task & Memory Services**: Extracted central state mutations to decoupled service interfaces.

---

## [9.7.0] - 2026-07-10

### Added
- **French Grammar Auto-Correction**: Helper integration to normalize syntax errors inside french language task prompts.
- **Token Pricing Registry**: Dynamic cost tracker for LLM providers.

---

## [9.6.0] - 2026-07-05

### Added
- **Git Hooks Automation**: Automated scripts for `session_start`, `post-commit`, and `session_end`.
- **Qdrant Index Syncing**: Automatic synchronization of semantic code embeddings to Qdrant vector database.
