# Fiche projet — DevCore

Projet : `devcore`. Version : 233. Revue : 2026-10-11.
Portée : ce dépôt. Production non qualifiée.

## Objectif et vocabulaire

DevCore coordonne les tâches, agents, connaissances du code et le Cockpit.
La cible permet à plusieurs utilisateurs de travailler chacun sur son projet
sans blocage mutuel. Un **projet** délimite données et droits ; un **run** est
une tentative d'exécution persistante ; un **workspace** est son répertoire
de travail, sans garantie de sandbox.

## Architecture actuelle et cible

Actuel : Python, CLI/PowerShell, tâches SQLite, API FastAPI, MCP, Cockpit et
scheduler. Des adaptateurs JSON historiques subsistent. RepoWise garde son
propre index du dépôt. Cible : API commune, PostgreSQL local pour le profil
équipe, droits par projet, workers durables, outbox et SSE. DBOS est à
qualifier. La bascule PostgreSQL et cette chaîne complète ne sont pas
déployées. Lire les décisions en vigueur du registre structuré.

## État utile à la reprise

- Pilote sur ce poste en localhost. Les données transactionnelles actives
  doivent rester hors Dropbox ; tests uniquement sur copies et racines
  temporaires. Aucun second poste requis. Accès réseau après qualification
  des identités, des droits et de l'isolation.
- L0–L2 finalisé : sauvegarde/import sur copies, mutations de tâches isolées par projet
  sur fixtures, ports @runtime_checkable et contrats typés dans devcore_api.
  FileTaskRepository adaptateur atomique, statuts active/in_progress unifiés,
  pagination limit/offset, catalogue /api/v1/routes. Conflits 409 et codes d'erreur
  universels dans task_mutations.py. Routage API du CLI devcore task, dc.py et MCP ;
  barrière DEVCORE_CLIENT_MODE=1 interdisant l'accès direct SQLite côté client.
  Binding gateway sur 127.0.0.1:20131. Voir le journal v164–v217.
- L3 : schéma PostgreSQL v2 (19 tables), RLS par projet, numérotation atomique,
  versions et import dry-run ; aucun cluster réel qualifié. Voir v218–v222.
- L4 : autorisation par projet, refus des divergences query/body, versions, Bearer/cookie,
  audit et DDL `NOBYPASSRLS` qualifiés sur fixtures. Voir v219–v222.
- L5 : `DurableRunEngine` à 8 états, worker borné, pause sûre, confinement Windows Job
  et déduplication. D-008 remplace DBOS (D-005). Voir v220–v222.
- L6 : outbox transactionnelle, snapshots versionnés, producteur unique et SSE à
  reprise stricte ; 362 tests. Voir v223.
- L7 : fournisseurs mémoire SQLite/RepoWise/composite, isolation par projet,
  FTS5/graphe/embeddings 768d avec repli lexical ; 132 tests. Voir v224.
- L8 : scheduler à baux atomiques et arrêt coopératif, Job Object, métriques par
  projet/tâche, export OTLP/LLMOps borné ; 694 tests sur banc. Activation continue
  et Langfuse distant ouverts. Voir v225.
- L9 v226 : runtime Python 3.13.16 / SQLite 3.53.1 et snapshot individuel figé,
  tests WAL et 267 tests collectés (266 réussis, 1 ignoré), gate CI 11/11.
  `operationally_qualified=false`. Voir v226.
- L9 v227 : release candidate séparée `devcore-py31316-20261010-l9`, wheel, contrôles et
  hôte pywin32/DLL attestés par manifeste/provenance ; cycle coopératif réussi sur racines
  temporaires et sur le service SCM réel. Racines portables `state/local` et `state/data`
  sous `E:/DevCoreRuntime`, identité privée initialisée. `DevCoreIndividual` est installé
  et actif sous `.\Administrateur` après attribution de `SeServiceLogonRight` ; `/project`
  répond HTTP 200. Ce compte n'est pas restreint ; reprise après redémarrage Windows,
  bascule des données et pilote restent ouverts.
  Voir journal v227.
- L9 v228 : copie SQLite cohérente de l'ancien état local et de 31 JSON `Memory`
  vers `E:/DevCoreRuntime/qualification`, sans toucher les sources. Prévisualiseur FK
  corrigé pour le schéma historique ; 10 tests ciblés passés. Réconciliation sur
  copies : 1 378 tâches conservées, mais 268 866 arêtes orphelines, 2 projets
  provisoires, 2 collisions et 460 identifiants de tâches non interprétables.
  Le schéma cible manque encore dans la copie (knowledge_items, colonnes project_id
  du graphe/vault et version des tâches). `review_required=true`,
  `ready_for_cutover=false` ; aucun import réel. Voir v228.
- L9 v229 : pilote préparé exclusivement sur copie sous
  `E:/DevCoreRuntime/qualification/pilot-v229` ; 1 378 tâches et 427 401 arêtes
  valides conservées, 268 866 arêtes en quarantaine. Numéros de pilote uniques :
  460 identifiants texte, 1 collision et 2 identifiants `T-00` réattribués dans
  la table de correspondance, avec identifiants originaux intacts. Schéma courant
  ajouté à la copie ; intégrité et clés étrangères OK. Dashboard isolé sur 20132
  et deux comptes temporaires : lecture propre 200, lecture croisée 403 ; comptes
  désactivés et jetons révoqués. Aucune bascule de `state/local`, aucun gel des
  écrivains ; cinq sessions, deux runs, retour arrière et reprise Windows ouverts.
  Voir v229.
- L9 v230–v231 : défaut de confinement des runs reproduit dans la release v227
  (`DEV_CORE.Scheduler` absent du paquet isolé), corrigé dans une release candidate
  séparée `devcore-py31316-20261011-l9-runfix`, sans changer le service.
  Sur copie : 5 sessions concurrentes isolées, 2 runs confinés en parallèle et
  restauration indépendante des tâches/runs/identités. L'ancienne release ouvre
  le Dashboard restauré, mais ne qualifie pas le retour arrière des runs.
  Bascule, compte restreint et reboot restent ouverts. Voir v230–v231.
- L9 v232–v233 : 20 sessions simulées et 200 lectures sur copie, p95 observé
  89,74 ms ; 2 runs réussis. Mémoire libre avant/après ~5,9 Gio, pas de pic
  mesuré. Crash d'un worker de recette : enfant terminé par Job Object, run
  remis en file avec jeton effacé, puis annulé. Voir v232–v233.
- Routage LLM : 8787 natif préserve fournisseur et modèle ; 8789 auxiliaire
  va vers Gemini Router 20130 avec alias explicites, embeddings directs.
  Des contrôles de ports et de refus ont été testés en localhost ; usage
  attribué, authentification et économie réelle restent à qualifier.

## Prochaine action et preuves

Poursuivre le Lot L9 (qualification opérationnelle et déploiement sur ce poste :
mise en service sous compte restreint, bascule vers l'API unique, pilote localhost
multi-utilisateurs et gel définitif des écritures historiques).
Le budget du contexte est en octets, pas en tokens.

[Plan](../../plans/2026-10-01-devcore-local-multiutilisateur.md) ·
[Journal récent](../audit-2026-09-30/execution-2026-10-05.md) ·
[Protocole tokens](../audit-2026-09-30/protocole-tokens-codex.md).
