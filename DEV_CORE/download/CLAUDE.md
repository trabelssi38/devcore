# CLAUDE.md -- DEV_CORE v6
# Emplacement : C:\DEV_CORE\Config\CLAUDE.md
# --> Injecte dans ~/.claude/CLAUDE.md par adapt_client.ps1
#
# NOTE : Ce fichier fixe le COMPORTEMENT de l'agent.
# Les ACTIONS autonomes (lancement ps1) sont gerees par les hooks
# dans ~/.claude/settings.json via install_hooks.ps1
# Ces deux fichiers fonctionnent ENSEMBLE.

## Contexte de session

Au debut de chaque session, les hooks ont deja execute automatiquement :
- new_project.ps1 (si nouveau projet detecte)
- launch.ps1
- dc.ps1 next mission

Lire en premier ces deux fichiers pour connaitre la mission active :
  C:\DEV_CORE_DATA\Logs\scripts\session_context.txt
  C:\DEV_CORE_DATA\Logs\scripts\last_handoff.md

---

## Mode de reponse

- Concis. Pas de preambule. Code d'abord.
- Listes > prose pour le contenu structure.
- 1 question max si clarification necessaire.

---

## Memoire (priorite absolue)

- Consulter MEMORY.md avant tout sujet potentiellement connu.
- Interroger Qdrant (collections decisions/lessons/patterns).
- Score > 0.75 : utiliser sans re-generer.
- Charger uniquement les skills pertinents a la tache.

---

## Skills (obligatoire)

- Charger devcore-automation en tout premier.
- Verifier skills_registry.json avant toute tache non triviale.
- Si skill disponible : le charger et le suivre exactement.
- Seuil auto-creation skill : 3 occurrences similaires.

---

## Tokens

- Resumes structures > prose longue.
- Ne pas repeter le contexte deja fourni.
- Budget defaut : 8k tokens. Alerter si depassement previsible.

---

## Regles pendant le travail

Apres chaque etape validee (tests passants) :
  1. Lire current_mission dans C:\DEV_CORE_DATA\Memory\missions.json
  2. git add -A
  3. git commit -m "feat: [description] [M-XX]"
  Le hook PostToolUse detecte MISSION_COMPLETE automatiquement.

Verifier mission_complete_signal.txt apres chaque commit :
  C:\DEV_CORE_DATA\Logs\scripts\mission_complete_signal.txt

Avant de terminer la session :
  powershell -NonInteractive -File "C:\DEV_CORE\Scripts\endday.ps1" -SkipBackup

---

## Handoffs & Missions

- Terminer par Next Actions si la tache genere des suites.
- Logger decisions dans Vault (skill obsidian).
- Upsert patterns dans Qdrant (skill qdrant).
- Commit tag [M-XX] obligatoire a chaque etape.

---

## Routing

- Suivre ROUTER.md pour le choix du moteur et budget token.

---

## Format de log DEV_CORE

Une ligne apres chaque action systeme, puis continuer :
  [DEV_CORE] Session demarree -- Mission M-02 active -- step 2/5
  [DEV_CORE] commit [M-02] -- step 3/5
  [DEV_CORE] MISSION_COMPLETE M-02 -- handoff genere
  [DEV_CORE] endday.ps1 -- sync OK
