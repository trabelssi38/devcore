# CLAUDE.md -- DEV_CORE v10.0 -- Universal Agent Mode
# Emplacement : C:\devcore\DEV_CORE\Config\CLAUDE.md
# --> Injecté dans ~/.claude/CLAUDE.md par adapt_client.ps1

## RÈGLES D'EXÉCUTION DU ROUTAGE UNIVERSEL

Veuillez vous référer et suivre STRICTEMENT les instructions du fichier de configuration global :
[DEVCORE_AGENT_INSTRUCTIONS.md](file:///C:/devcore/DEV_CORE/Config/DEVCORE_AGENT_INSTRUCTIONS.md)

### Résumé des commandes obligatoires :
- Début de session (Vérification tâche & Lancement platform) :
  ```powershell
  powershell -ExecutionPolicy Bypass -NonInteractive -File "C:\devcore\DEV_CORE\Scripts\launch.ps1"
  ```
- Activation / Déclaration d'une tâche (Auto-bootstrap protocole) :
  Si aucune tâche n'est active, les requêtes LLM seront rattachées à une session éphémère EPH-XXX et comporteront un rappel.
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

## Discipline de code (Karpathy rules) :

### 1. Penser avant de coder
- Énoncer les hypothèses explicitement. Si incertain, demander.
- Si plusieurs interprétations existent, les présenter -- ne pas choisir silencieusement.
- Si une approche plus simple existe, la proposer.

### 2. Simplicité absolue
- Minimum de code qui résout le problème. Rien de spéculatif.
- Pas de features au-delà de ce qui est demandé.
- Pas d'abstractions pour du code à usage unique.

### 3. Changements chirurgicaux
- Toucher uniquement ce qui est nécessaire.
- Ne pas refactoriser ce qui ne pose pas de problème.
- Correspondre au style existant.

### 4. Vérification avant de livrer
- Définir des critères de succès vérifiables avant de commencer.
- Boucler jusqu'à ce que le but soit vérifié (tests, démo).
- Ne pas déclarer "terminé" avant vérification.
