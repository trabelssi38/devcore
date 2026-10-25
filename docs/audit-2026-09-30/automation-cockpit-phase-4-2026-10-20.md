# Automation Hooks — candidat de phase 4 (2026-10-20)

La projection PostgreSQL du Cockpit distingue trois sources du projet sélectionné :
`automation_hook_events` (dernier événement par type de hook et dernier succès),
`runs` (dernier run Git, RepoWise ou métriques quotidiennes et dernier succès),
et `schedules` avec `schedule_history` (état, prochain passage, dernière tentative
et dernier succès). Chaque ligne expose l'auteur et la source lorsqu'ils sont
enregistrés, ainsi qu'une erreur échappée et limitée à 160 caractères. Une
section vide nomme sa source absente ; le HTML ne crée aucun statut réussi.

Les requêtes utilisent `project_id` dans la transaction RLS de la projection.
Le basculement de projet continue de charger le snapshot du seul projet cible,
sans recharger la page ni reconstruire la liste des projets. La réponse d'un
ancien projet est ignorée. Le flux temps réel existant est réattaché lors de la
bascule ; aucun changement à sa gestion n'est nécessaire pour cette phase.

Recette sur racines `DEVCORE_LOCAL_ROOT` et `DEVCORE_DATA_ROOT` temporaires
définies avant les imports : 18 tests Python de projection/rendu réussis et test
Node de navigation réussi. Les deux vues rendent les états avec succès, échec
et absence de données pour les projets A/B ; la navigation vérifie qu'une
réponse de A ne repeint pas la section de B. Le lecteur de contexte répond en
8 417/12 000 octets UTF-8, sans avertissement ni omission ; sa suite ciblée
donne 6 tests réussis et 1 ignoré.

Ce rendu est un candidat local. Le DDL `automation_hook_events` et les routes
des phases 1–3 ne sont pas installés dans `DevCoreGlobal`. Le Cockpit actif ne
peut donc pas encore afficher ces nouvelles preuves ; l'ordre de migration et
la recette sous utilisateur réel relèvent de la phase 5. Les tests de cette
phase utilisent des réponses de curseur simulées, sans base active ni index
RepoWise réel comme fixture. Ils ne prouvent pas le comportement HTTP après
déploiement ni la qualification visuelle sous `majdi`.
