# CLAUDE.md -- DEV_CORE v6 -- Single Client Mode
# Emplacement : C:\devcore\DEV_CORE\Config\CLAUDE.md
# --> Injecte dans ~/.claude/CLAUDE.md par adapt_client.ps1
#
# Mode : single client + 9Router pour le routing des modeles
# Les hooks dans settings.json gerent le demarrage automatique.

## Contexte de session

Au debut de chaque session, les hooks ont execute automatiquement :
- new_project.ps1 (si nouveau projet)
- launch.ps1
- task_next.ps1

Lire en premier :
  C:\devcore\DEV_CORE_DATA\Logs\scripts\session_context.txt
  C:\devcore\DEV_CORE_DATA\Memory\tasks.json (tache active + mode)

---

## Mode de reponse

- Concis. Pas de preambule. Code d'abord.
- Listes > prose pour le contenu structure.
- 1 question max si clarification necessaire.

---

## Routing mode (PRIORITE)

Avant chaque tache, lire le mode dans tasks.json :

  mode=reasoning -> budget 32k, skill dev-methodology ou fabric-patterns
  mode=coding    -> budget 8k,  skill dev-methodology selon stack
  mode=bulk      -> budget 16k, skill fabric-patterns, pas de validation intermediaire

9Router route automatiquement vers le bon modele selon le mode.
Ne jamais mentionner de noms de modeles -- utiliser uniquement les modes.

---

## Memoire (priorite absolue - L0-L3 hierarchie)

- Consulter L3 `C:\devcore\DEV_CORE_DATA\Memory\persona.md` (toujours charge).
- Consulter L2 `C:\devcore\DEV_CORE_DATA\Memory\Scenarios\{task_type}.md` selon le type de tache.
- Interroger L1 Qdrant (decisions/lessons/patterns) si L2 est insuffisant (score > 0.75).
- Interroger L0 SQLite (recherche plein texte via `memory_hierarchy.ps1 -Action Query`) en dernier recours.
- Charger uniquement les skills pertinents a la tache.

---

## Skills (obligatoire)

- Charger devcore-automation en premier.
- Verifier skills_registry.json avant toute tache non triviale.
- Si skill disponible : le charger et le suivre exactement.
- Seuil auto-creation skill : 3 occurrences similaires.

---

## Tokens & Offloading (TencentDB Canvas)

- Resumes structures > prose longue.
- **CRITICAL**: Si un output d'outil, log, compilation ou contenu est volumineux (>500 lignes ou >10k caracteres), **NE PAS l'afficher en brut**.
- Le decharger avec :
  `powershell -File "C:\devcore\DEV_CORE\Scripts\canvas_manager.ps1" -Action Offload -Content "CONTENU" -TaskId "T-XX" -Type "log|code"`
- Utiliser le symbole genere (ex: `T02_log_e4c3`) dans ta reponse et ton canvas Mermaid.
- Respecter le budget du mode actif.
- Alerter si depassement previsible.

---

## Discipline de code (Karpathy rules)

### 1. Penser avant de coder
- Enoncer les hypotheses explicitement. Si incertain, demander.
- Si plusieurs interpretations existent, les presenter -- ne pas choisir silencieusement.
- Si une approche plus simple existe, la proposer. Pousser en arriere si justifie.
- Si quelque chose est flou, stopper. Nommer ce qui est confus. Demander.

### 2. Simplicite d'abord
- Minimum de code qui resout le probleme. Rien de speculatif.
- Pas de features au-dela de ce qui est demande.
- Pas d'abstractions pour du code a usage unique.
- Pas de "flexibilite" ou "configurabilite" non requise.
- Si tu ecris 200 lignes et que 50 suffisent : réécrire.

### 3. Changements chirurgicaux
- Toucher uniquement ce qui est necessaire.
- Ne pas "ameliorer" le code adjacent, les commentaires ou le formatage.
- Ne pas refactoriser ce qui ne pose pas de probleme.
- Correspondre au style existant.

### 4. Execution orientee objectif
- Definir des criteres de succes verifiables avant de commencer.
- Boucler jusqu'a ce que le but soit verifie (tests, demo).
- Ne pas declarer "termine" avant verification.

---

## Regles pendant le travail

### Apres chaque etape validee
Lire current_task dans tasks.json, puis :
  git add -A
  git commit -m "feat: [description] [T-XX]"
Le hook post-commit incremente steps_done automatiquement.

### Verifier si tache complete (apres chaque commit)
Lire tasks.json : steps_done >= steps_total sur la tache active ?
  -> Executer : powershell -NonInteractive -File "C:\devcore\DEV_CORE\Scripts\task_done.ps1" -Force
  -> Lire le signal : C:\devcore\DEV_CORE_DATA\Logs\scripts\session_context.txt

### Fin de session
Executer avant de terminer :
  powershell -NonInteractive -File "C:\devcore\DEV_CORE\Scripts\endday.ps1" -SkipBackup

---

## Taches & tracking

- Tache active dans : C:\devcore\DEV_CORE_DATA\Memory\tasks.json
- Commit tag : [T-XX] (pas [M-XX] -- ancienne version multi-client)
- Plus de handoffs entre agents -- tout dans le meme client
- Plus de adapt_client.ps1 -- 9Router gere le routing des modeles

---

## Routing

- Suivre ROUTER.md v3 pour la detection du mode.
- Toutes les requetes passent par Headroom Proxy (Port 8787).
- Ne jamais choisir un modele par nom -- utiliser reasoning/coding/bulk.

---

## Format de log DEV_CORE

Une ligne apres chaque action systeme :
  [DEV_CORE] Task T-02 active -- mode coding -- budget 8k
  [DEV_CORE] commit [T-02] -- step 2/5
  [DEV_CORE] task_done.ps1 -- T-02 done -- Suivant : T-03 [bulk]
  [DEV_CORE] endday.ps1 -- sync OK
