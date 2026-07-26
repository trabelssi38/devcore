# CLAUDE.md -- DEV_CORE v10.0 -- Universal Agent Mode
# Emplacement : C:\devcore\DEV_CORE\Config\CLAUDE.md
# --> Injecté dans ~/.claude/CLAUDE.md par adapt_client.ps1

## RÈGLES D'EXÉCUTION DU ROUTAGE UNIVERSEL

Veuillez vous référer et suivre STRICTEMENT les instructions du fichier de configuration global :
[DEVCORE_AGENT_INSTRUCTIONS.md](file:///C:/devcore/DEV_CORE/Config/DEVCORE_AGENT_INSTRUCTIONS.md)

### PROCÉDURE OBLIGATOIRE DU PROTOCOLE DEV_CORE (TOUS CLIENTS/AGENTS) :

1. **RÈGLE #1 - ACTIVATION DE TÂCHE OBLIGATOIRE (AVANT TOUT CODE)** :
   Avant TOUTE modification de fichier, refactorisation ou écriture de code, l'agent DOIT créer ou activer une tâche formelle :
   ```powershell
   python C:\devcore\DEV_CORE\Scripts\dc.py task add "Titre descriptif de la tâche"
   # ou via task_service :
   powershell -ExecutionPolicy Bypass -File "C:\devcore\DEV_CORE\Scripts\task_service.ps1" -Action Add -Title "Titre"
   ```
   *Ceci définit `current_task: "T-XXX"` dans `tasks.json` et garantit l'association immédiate de 100% des jetons et métriques à cette tâche.*

2. **Lecture du Contexte** :
   ```powershell
   Get-Content "C:\devcore\DEV_CORE_DATA\Logs\scripts\session_context.txt" -ErrorAction SilentlyContinue
   ```

3. **Commits Git avec Tag `[T-XXX]` Obligatoire** :
   Tout commit DOIT inclure le tag de la tâche active :
   ```bash
   git add -A
   git commit -m "[T-XXX] feat: description du changement"
   ```

4. **Clôture de Tâche (Fin d'intervention)** :
   Dès que le travail est vérifié et validé :
   ```powershell
   python C:\devcore\DEV_CORE\Scripts\dc.py task complete
   # ou via task_service :
   powershell -ExecutionPolicy Bypass -File "C:\devcore\DEV_CORE\Scripts\task_service.ps1" -Action Complete -Id "T-XXX"
   ```
   ```powershell
   powershell -ExecutionPolicy Bypass -NonInteractive -File "C:\devcore\DEV_CORE\Scripts\endday.ps1" -SkipBackup
   ```

---

## INTÉGRATION REPOWISE CODE HEALTH & RADAR (v10.0) :

- **Port HTTP API Repowise** : `http://127.0.0.1:7337`
- **Composant Dashboard** : *Repowise Code Health & Refactoring Radar* (Visualisation de la maintenabilité, performance statique et cibles prioritaires de refactoring).
- **Mode Fallback** : Si le serveur HTTP 7337 est inactif, le Dashboard bascule automatiquement sur le mode indexé MCP (`⚡ MCP INDEXED`) sans perturber le fonctionnement des agents.
- **Portes de Santé (Health Gates)** : Vérification automatique via `test_repowise_health_gate.ps1` (Score moyen global >= 5.0/10 obligatoire).

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
