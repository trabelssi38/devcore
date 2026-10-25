# Fiche projet — DevCore

Projet : `devcore`. Revue : 2026-10-25.
Portée : ce dépôt et son pilote local. Une qualification de production générale n'est pas établie.

## Objectif et architecture

DevCore coordonne tâches, agents, connaissances du code et Cockpit. Un projet
délimite les données et les droits ; un run est une tentative persistante ;
un workspace est un répertoire de travail, sans garantie de sandbox.
Le profil équipe actif utilise l'API commune, PostgreSQL local, les droits par
projet et le Cockpit. Le profil individuel historique et ses adaptateurs
SQLite/JSON restent distincts. RepoWise garde un index séparé par dépôt.
Les décisions applicables et leurs remplacements sont dans `context.json`.

## État vérifié le 25 octobre 2026

- `DevCoreGlobal` exécute la candidate Git `1f5ec0f6e9d31898d11f0f41dc5d2682d916b7c6`.
  Son démarrage au troisième reboot du 23 octobre était automatique. Depuis
  le 24 octobre, un déclencheur temporel toutes les cinq minutes complète
  celui du boot et ignore les passages si la tâche tourne déjà. Après arrêt
  contrôlé du processus RepoWise, le superviseur a quitté avec code 1 puis
  Windows a relancé seul la pile : `ready` en 255 secondes. Le même superviseur
  PID 3628 est encore actif le 25 octobre à 12:30 Tunis, six composants et
  cinq sondes HTTP sains. Un état gateway faux sur un battement a disparu à
  la sonde suivante, sans arrêt. Voir journal v494–v495.
- Le Cockpit équipe affiche les projets Git autorisés à l'utilisateur connecté,
  permet leur sélection et leur archivage, et charge les données propres au
  projet sans recharger la page. La projection PostgreSQL a rendu les deux
  vues pour `devcore`, `dashboard_recette_br` et `job_tracker` en lecture seule.
- « Composition du contexte » lit séparément la fiche et les décisions sous
  le droit `context.read`, affiche leur revue, leur provenance et les alertes
  de fraîcheur. La réponse complète est bornée en octets UTF-8 ; ce volume
  n'est pas une mesure des tokens réellement envoyés à Codex. Les entrées
  `memory_entries` et l'index RepoWise restent des sources distinctes.
  DevCore sait produire un instantané Git et d'empreintes vérifiées ; le
  Cockpit le présente. Son échéance quotidienne de 09:00 Tunis est désactivée
  depuis le 25 octobre à la demande de l'utilisateur. La revue narrative et
  les décisions ne sont jamais datées automatiquement.
- L'audit des 29 appartenances de `majdi`, avant filtre Git, trouvait zéro ligne
  dans `memory_entries`, `budgets` et `plugins`. Le bilan quotidien non destructif
  de `devcore` à 08:00 Tunis et le renouvellement des faits à 09:00 ont réussi
  les 24 et 25 octobre. Le 25, `run-c51cdbf1dc32` et `run-3c73ae09f1e6`
  sont `succeeded`, code 0, avec un seul run par clé d'échéance et l'historique
  `dispatched` puis `finished`. Le 25 octobre, les deux échéances suivantes ont
  été arrêtées : schedules `disabled`, `next_run_at=NULL`, derniers runs
  conservés. La lecture PostgreSQL, le journal du scheduler, le lecteur borné
  et le Cockpit sous `majdi` concordent.
  La mesure quotidienne des dépassements et la conformité du
  protocole agent ne sont pas encore produites par projet ; le Cockpit montre
  des états explicites pour les sources manquantes.
- La séparation LLM conserve 8787 pour le natif et 8789 pour l'auxiliaire
  explicite vers Gemini Router 20130. Un appel Gemini réel a été vérifié ;
  OpenAI et Anthropic sont hors du périmètre actuel. Aucun gain effectif de
  tokens n'est établi par une comparaison contrôlée.

## Limites et reprise

Le Cockpit connecté sous `majdi` affiche le 25 octobre les deux passages
réussis et l'instantané du contexte, puis les deux planifications désactivées
sans prochain passage, sans rechargement de page. La séparation visible entre
`devcore` et `dashboard_recette_br` a été
vérifiée le 22 octobre. Les passages sont aussi contrôlés en base et dans le
journal du scheduler.
Un échec simulé a été qualifié sur PostgreSQL temporaire jusqu'à son rendu
Cockpit isolé. Un retour arrière réel avec le schedule actif, suivi de la
restauration de la candidate, a préservé le dernier passage et l'échéance.
Les deux premiers reboots ont nécessité une récupération manuelle ; le
troisième a prouvé le démarrage automatique. Une panne contrôlée du 24 octobre
a prouvé une reprise en cours d'exécution sans intervention. La cause des
pertes de santé antérieures et le comportement après un nouveau reboot avec
le déclencheur temporel restent à observer ; la qualification porte sur le
pilote local, pas sur une disponibilité générale.
Le retour arrière de la candidate, l'affichage distinct des heures de tentative
et de réussite, et le rafraîchissement ciblé après reconnexion SSE ont été
contrôlés en serveur et sous `majdi` (journal v473–v485). Aucun hook client
n'est installé.
L'index RepoWise du dépôt principal doit être confronté au code courant
lorsqu'il est ancien ; ses estimations de tokens ne prouvent pas
une économie réelle. Ne jamais utiliser les données actives, Dropbox ni un
index RepoWise réel comme fixture de test. Définir `DEVCORE_LOCAL_ROOT` et
`DEVCORE_DATA_ROOT` temporaires avant imports et sous-processus de recette.

Pour reprendre, lire les décisions en vigueur du registre structuré, puis
contrôler les preuves actuelles avant d'annoncer une qualification ou une
mise en service. L'historique L0–L9 et les limites se trouvent dans le
[plan](../../plans/2026-10-01-devcore-local-multiutilisateur.md) et le
[journal](../audit-2026-09-30/execution-2026-10-05.md), notamment v493–v495.
Le [protocole de mesure des tokens](../audit-2026-09-30/protocole-tokens-codex.md)
reste à exécuter sur des tâches comparables.
