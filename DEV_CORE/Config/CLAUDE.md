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

## Memoire (priorite absolue)

- Consulter MEMORY.md avant tout sujet potentiellement connu.
- Interroger Qdrant (collections decisions/lessons/patterns).
- Score > 0.75 : utiliser sans re-generer.
- Charger uniquement les skills pertinents a la tache.

---

## Skills (obligatoire)

- Charger devcore-automation en premier.
- Verifier skills_registry.json avant toute tache non triviale.
- Si skill disponible : le charger et le suivre exactement.
- Seuil auto-creation skill : 3 occurrences similaires.

---

## Tokens

- Resumes structures > prose longue.
- Ne pas repeter le contexte deja fourni.
- Respecter le budget du mode actif.
- Alerter si depassement previsible.

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

- Suivre ROUTER.md v2 pour la detection du mode.
- Ne jamais choisir un modele par nom -- utiliser reasoning/coding/bulk.

---

## Format de log DEV_CORE

Une ligne apres chaque action systeme :
  [DEV_CORE] Task T-02 active -- mode coding -- budget 8k
  [DEV_CORE] commit [T-02] -- step 2/5
  [DEV_CORE] task_done.ps1 -- T-02 done -- Suivant : T-03 [bulk]
  [DEV_CORE] endday.ps1 -- sync OK
