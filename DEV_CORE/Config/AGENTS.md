# AGENTS.md -- DEV_CORE v10.0 -- Universal Agent Mode
# Emplacement : C:\devcore\DEV_CORE\Config\AGENTS.md
# --> Injecté dans ~/.codex/AGENTS.md par adapt_client.ps1

## RÈGLES D'EXÉCUTION DU ROUTAGE UNIVERSEL

Veuillez vous référer et suivre STRICTEMENT les instructions du fichier de configuration global :
[DEVCORE_AGENT_INSTRUCTIONS.md](file:///C:/devcore/DEV_CORE/Config/DEVCORE_AGENT_INSTRUCTIONS.md)

### Résumé des commandes obligatoires :
- Début de session :
  ```powershell
  powershell -ExecutionPolicy Bypass -NonInteractive -File "C:\devcore\DEV_CORE\Scripts\launch.ps1"
  ```
- Lecture contexte :
  ```powershell
  Get-Content "C:\devcore\DEV_CORE_DATA\Logs\scripts\session_context.txt" -ErrorAction SilentlyContinue
  ```
- Commits :
  ```bash
  git add -A
  git commit -m "feat: description [T-XX]"
  ```
- Fin de session :
  ```powershell
  powershell -ExecutionPolicy Bypass -NonInteractive -File "C:\devcore\DEV_CORE\Scripts\endday.ps1" -SkipBackup
  ```

---

## Response Guidelines

- Concise. Code first. No preamble.
- Lists > prose for structured content.
- 1 question max if clarification needed.
- TDD: write test first, make it pass, then commit.
