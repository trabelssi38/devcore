# Fiche projet — DevCore

Projet : `devcore`. Revue : 2026-10-26.
Portée : ce dépôt et son pilote local. Une qualification de production générale n'est pas établie.

## Objectif et architecture

DevCore coordonne tâches, agents, connaissances du code et Cockpit. Un projet
délimite les données et les droits ; un run est une tentative persistante ;
un workspace est un répertoire de travail, sans garantie de sandbox.
Le profil équipe actif utilise l'API commune, PostgreSQL local, les droits par
projet et le Cockpit. Le profil individuel historique et ses adaptateurs
SQLite/JSON restent distincts. RepoWise garde un index séparé par dépôt.
Décisions applicables : `context.json`.

## État vérifié le 26 octobre 2026

- P0 a été qualifiée à 11:02 Tunis sur l'ancienne source `d4dbfe2`, après
  le reboot lent du 26 octobre et environ 10 h 16 min de stabilité observée.
  La bascule approuvée à 14:50 Tunis a ensuite déployé `d6cac93` : tâche S4U
  active, six composants sains, cinq listeners et cinq sondes HTTP à 200.
  La stabilité prolongée de `d6cac93` reste à observer.
- Le Cockpit équipe affiche les projets Git autorisés à l'utilisateur connecté,
  permet leur sélection et leur archivage, et charge les données propres au
  projet sans recharger la page. La projection PostgreSQL a rendu les deux
  vues pour `devcore`, `dashboard_recette_br` et `job_tracker` en lecture seule.
- L'Agent pilote a été retiré du service sur accord utilisateur : routes,
  page, lien et contrôleur supprimés ; les jobs et hooks restent. Les patchs
  sont désormais traités dans ce fil, à la demande et avec accord préalable.
  Le retrait est au commit propre `d6cac93` ; 38 tests ciblés ont réussi.
- « Composition du contexte » lit séparément la fiche et les décisions sous
  le droit `context.read`, affiche leur revue, leur provenance et les alertes
  de fraîcheur. La réponse complète est bornée en octets UTF-8 ; ce volume
  n'est pas une mesure des tokens réellement envoyés à Codex. Les entrées
  `memory_entries` et l'index RepoWise restent des sources distinctes.
  DevCore sait produire un instantané Git et d'empreintes vérifiées ; le
  Cockpit le présente. Son échéance naturelle de 09:00 Tunis le 26 octobre
  a réussi, sans doublon. La revue narrative et
  les décisions ne sont jamais datées automatiquement.
- L'audit des 29 appartenances de `majdi`, avant filtre Git, trouvait zéro ligne
  dans `memory_entries`, `budgets` et `plugins`. Le bilan quotidien à 08:00
  Tunis et les faits à 09:00 ont réussi les 24 et 25 octobre. Les deux
  schedules ont été réactivés le 26 octobre à 00:08 sur instruction.
  Leurs passages naturels du 26 octobre à 08:00 et 09:00 sont `succeeded`,
  code 0, une occurrence chacun, avec historique de dispatch puis fin. Les
  schedules restent `active`, prochaine échéance le 27 octobre, commandes
  rattachées à `d6cac93`, heures et historique inchangés. Le Cockpit sous
  `majdi` les affichait à 10:09 avant la bascule.
  La mesure quotidienne des dépassements et la conformité du
  protocole agent ne sont pas encore produites par projet ; le Cockpit montre
  des états explicites pour les sources manquantes.
- La séparation LLM conserve 8787 pour le natif et 8789 pour l'auxiliaire
  explicite vers Gemini Router 20130. Un appel Gemini réel a été vérifié ;
  OpenAI et Anthropic sont hors du périmètre actuel. Aucun gain effectif de
  tokens n'est établi par une comparaison contrôlée.

## Limites et reprise

Le Cockpit connecté sous `majdi` affichait le 25 octobre les passages
réussis et l'instantané du contexte. Après reconnexion le 26 octobre à 10:09,
il affiche les deux succès naturels du jour, les échéances du 27, la fiche
bornée et les services sains. Aucun rechargement manuel n'a été effectué.
La séparation visible entre `devcore` et `dashboard_recette_br` a été
revérifiée le 26 octobre. Les passages sont aussi contrôlés en base et dans le
journal du scheduler. La session Cockpit a expiré avant 11:02.
Un échec simulé a été qualifié sur PostgreSQL temporaire jusqu'à son rendu
Cockpit isolé. Un retour arrière réel avec le schedule actif, suivi de la
restauration de la candidate, a préservé le dernier passage et l'échéance.
Les deux premiers reboots ont nécessité une récupération manuelle ; le
troisième et celui du 26 ont montré un démarrage automatique, lent le 26.
Une panne contrôlée du 24 octobre
a prouvé une reprise en cours d'exécution sans intervention. La cause des
pertes de santé antérieures restent à étudier ; la qualification porte sur le
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
