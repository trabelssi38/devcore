# DEV_CORE Pipeline — Agent Execution Rules (v10.0)

This is the unified source of truth for all AI agents working in this workspace.
Follow these rules strictly.

## 0. AUTO-BOOTSTRAP PROTOCOL ENFORCEMENT (Automatique)

Le Gemini Router (Port 20130) supervise la conformité du protocole :
- Si aucune tâche formelle n'est déclarée active dans `tasks.json`, une session éphémère (ex: `EPH-1721352000`) est automatiquement attribuée.
- Un message de rappel de protocole est réinjecté dans les réponses système toutes les 5 requêtes LLM tant qu'aucune tâche formelle n'est activée.
- Pour stopper les rappels et enregistrer formellement votre travail :
  ```powershell
  python C:\devcore\DEV_CORE\Scripts\task_service.ps1 -Action Next
  # ou via la CLI Python si disponible
  ```

---

## 1. FIRST ACTION — Session Setup

At the very beginning of the session, execute these commands in order:

1. **Launch Platform Services**:
   ```powershell
   powershell -ExecutionPolicy Bypass -NonInteractive -File "C:\devcore\DEV_CORE\Scripts\launch.ps1"
   ```
2. **Read Session Context**:
   Load and display the contents of the context file:
   ```powershell
   Get-Content "C:\devcore\DEV_CORE_DATA\Logs\scripts\session_context.txt" -ErrorAction SilentlyContinue
   ```
   *Note: This file contains the active task ID, mode, and token budget.*

---

## 2. DURING WORK — Task Compliance & Limits

### Token Budgets & Monitoring
All calls are automatically routed through **Headroom Proxy (Port 8787)** and the **Gemini Router (Port 20130)** for token compression and tracking.
- Do NOT bypass these local endpoints.
- If you exceed the task budget, a warning header `X-DevCore-Budget-Alert: True` will be sent, and an alert will be logged to `alerts.log`. Stay focused and keep context concise.

### Context Offloading (TencentDB Canvas)
If a command output, log file, build result, or file contents is very large (>500 lines or >10k characters):
- **DO NOT print it raw** in the conversation.
- Offload it immediately using:
  ```powershell
  powershell -File "C:\devcore\DEV_CORE\Scripts\canvas_manager.ps1" -Action Offload -Content "YOUR_LARGE_CONTENT_HERE" -TaskId "T-XX" -Type "log"
  ```
- Use the returned node ID (e.g. `T02_log_e4c3`) in your thoughts and visual Mermaid diagrams.

### Commit Tagging
After every step where tests pass and the codebase is stable, commit your changes using the active task ID prefix:
```bash
git add -A
git commit -m "feat: [step description] [T-XX]"
```

---

## 3. LAST ACTION — End of Session

Before closing the session or completing the task, always execute:
```powershell
powershell -ExecutionPolicy Bypass -NonInteractive -File "C:\devcore\DEV_CORE\Scripts\endday.ps1" -SkipBackup
```
This runs synthetic diagnostics, synchronizes agent memories, and updates the cockpit metrics.
