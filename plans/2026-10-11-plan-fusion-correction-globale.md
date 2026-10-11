# Plan détaillé — fusion et correction globale des données DevCore

Date : 2026-10-11  
Portée : fusion de la base principale du poste actuel avec la copie de l'autre poste, puis correction contrôlée du graphe et du scheduler.  
Statut : plan de recette, aucune bascule autorisée par ce document seul.

## 1. Objectif et résultat attendu

Produire une base candidate unique, traçable et restaurable contenant les données utiles des deux installations, sans écraser une version concurrente ni supprimer silencieusement l'historique.

Le résultat attendu est :

- une base principale candidate `devcore.db` avec un projet explicite sur chaque tâche, événement, nœud et arête ;
- une base scheduler candidate séparée, ou une décision documentée de conservation de l'historique scheduler hors migration ;
- une table de correspondance pour les projets, tâches, nœuds, arêtes et événements fusionnés ;
- une quarantaine résolue, conservée ou rejetée avec motif et preuve ;
- des empreintes et rapports permettant de reproduire la décision ;
- une procédure de bascule et de retour arrière validée sur copies.

La cible PostgreSQL équipe reste hors de cette opération tant qu'un cluster réel n'est pas qualifié. La recette porte d'abord sur SQLite et l'API commune.

## 2. Données connues avant la fusion

### Poste actuel

- Base locale historique : 1 378 tâches, 27 projets, 20 989 événements bus, 9 entrées mémoire.
- Copie réconciliée : 427 401 arêtes valides et 268 866 arêtes en quarantaine.
- Deux projets provisoires à examiner : `scripts` (13 tâches) et `xtream_universal_manager` (33 tâches).
- Les identifiants texte de tâches, une collision numérique et deux `T-00` ont déjà reçu un mapping sur la copie de pilote.

### Autre poste

- `devcore.db` : 1 336 tâches, 4 projets SQL, 757 événements `bus_events`, 64 états de workflow.
- `Scheduler/scheduler.db` : 12 245 lignes `run_history`.
- `Scheduler/jobs.json` : 8 définitions historiques à inventorier, sans réactivation automatique.
- La base principale passe `integrity_check`, mais `foreign_key_check` échoue avec `foreign key mismatch - "runs" referencing "tasks"`.
- Les 1 336 clés de tâches de l'autre poste sont présentes sur le poste actuel ; des divergences de statut, progression, dates, métadonnées et titre existent.

Ces chiffres sont des points de départ. Ils doivent être recalculés après gel des écrivains et empreinte de chaque copie.

## 3. Règles de sécurité et d'arrêt

1. Ne jamais écrire dans les bases actives, Dropbox ou les répertoires de production pendant la recette.
2. Travailler sur trois copies indépendantes : source actuelle, source autre poste, et candidate de fusion.
3. Ouvrir les sources SQLite en lecture seule pour l'inventaire.
4. Définir `DEVCORE_LOCAL_ROOT` et `DEVCORE_DATA_ROOT` vers des racines temporaires avant tout import ou sous-processus.
5. Conserver une sauvegarde cohérente SQLite et son SHA-256 avant chaque transformation.
6. Arrêter la procédure si un identifiant de projet, de tâche ou de nœud ne peut pas être classé de façon déterministe.
7. Ne jamais choisir une valeur plus récente uniquement sur la date : les horodatages des deux postes ont déjà montré des divergences de format et de réécriture.
8. Ne supprimer une ligne qu'après conservation de sa représentation source, de son motif et de l'approbation de la règle correspondante.

## 4. Phase A — gel, inventaire et empreintes

### A1. Préparer la fenêtre de gel

- Identifier les processus et écrivains DevCore sur le poste actuel.
- Vérifier que l'autre poste ne produit plus d'écritures ; le journal indique qu'il ne tourne plus, mais cette preuve doit être reprise au moment du gel.
- Suspendre les jobs et hooks qui écrivent dans la base, le bus local ou les exports JSON.
- Noter l'heure, le compte Windows, les versions du runtime et les chemins résolus.

### A2. Capturer les copies

Pour chaque poste, copier par l'API de sauvegarde SQLite :

- `devcore.db` et ses bases auxiliaires éventuelles ;
- `Scheduler/scheduler.db` ;
- `Scheduler/jobs.json` ;
- les fichiers `Memory` et exports nécessaires à la provenance ;
- le registre des projets et les manifestes `.devcore/project.json`.

Produire un manifeste indiquant taille, mtime, SHA-256, version SQLite, présence de WAL/SHM et état `integrity_check`.

### A3. Inventaire structurel

Comparer les tables, colonnes, index, triggers, contraintes et versions de schéma. Signaler séparément :

- la référence invalide `runs → tasks` de l'autre poste ;
- les colonnes `project_id` et `version` manquantes dans les copies historiques ;
- l'absence éventuelle de `knowledge_items` ;
- les tables virtuelles FTS5 et sqlite-vec ;
- les tables de quarantaine déjà créées.

**Critère de sortie A :** les deux sources sont figées, copiées, empreintées et lisibles sans écriture.

## 5. Phase B — normalisation du schéma sur copies

1. Créer une candidate neuve avec le schéma courant.
2. Appliquer les migrations de schéma sur une copie intermédiaire, jamais sur une source.
3. Reconstruire `runs`, `events` et `audit_log` si nécessaire afin de corriger les clés composées.
4. Ajouter les colonnes obligatoires (`project_id`, `version`) avec une valeur explicitement classée : connue, provisoire ou à revoir.
5. Réindexer FTS5 et sqlite-vec après import, avec un rapport des lignes ignorées.
6. Tester `integrity_check`, `foreign_key_check` et les index uniques après chaque sous-étape.

**Critère de sortie B :** chaque source normalisée est cohérente seule ; aucune erreur de contrainte n'est masquée par un simple `integrity_check` positif.

## 6. Phase C — réconciliation des projets

Créer `project_merge_map` avec : `source`, `source_project_id`, `target_project_id`, `decision`, `evidence`, `review_status`.

Règles :

- même identifiant et même racine validée : proposer une fusion ;
- même nom mais racines différentes : conserver deux candidats jusqu'à revue ;
- projet présent sur un seul poste : le conserver ;
- `scripts` et `xtream_universal_manager` : ne pas rattacher automatiquement ; documenter propriétaire et racine ;
- `__legacy_unassigned__` : archive technique interdite dans les vues interactives.

La fusion d'un projet n'est validée que si ses tâches, ses nœuds, ses notes et ses chemins ne créent pas de collision avec un autre projet.

**Critère de sortie C :** chaque ligne importée possède un `target_project_id` ou un statut `needs_review` bloquant la bascule.

## 7. Phase D — réconciliation des tâches

Créer `task_merge_map` indexée par `(source, project_id, legacy_id)`.

### D1. Identité

- Utiliser `(target_project_id, task_number)` comme clé cible après résolution explicite.
- Conserver l'identifiant historique, y compris les slugs et les formes `T-00`.
- Réattribuer un numéro uniquement avec une règle déterministe et un mapping auditable.

### D2. Conflits

Pour chaque même tâche présente sur les deux postes, comparer : titre, statut, étapes, métadonnées, dates, worktree et dépendances.

- valeur identique : fusion automatique ;
- une seule valeur non vide : conserver et tracer la provenance ;
- valeurs divergentes de statut, progression ou titre : revue obligatoire ;
- dépendance absente ou étrangère : quarantaine de la dépendance, pas de suppression de la tâche.

Les 8 différences de statut/progression connues doivent être examinées individuellement avant toute décision globale.

**Critère de sortie D :** zéro doublon de clé cible, zéro tâche sans mapping et rapport de chaque conflit.

## 8. Phase E — fusion des événements, runs et scheduler

### E1. Événements et audit

- Importer les événements avec une clé de provenance `(source, source_event_id)`.
- Ne pas dédupliquer les 154 ressemblances observées entre les 757 événements de l'autre poste et ceux du poste actuel sans preuve de même événement logique.
- Conserver les événements sans tâche résolue dans une quarantaine d'audit.
- Recalculer les compteurs et vérifier l'ordre temporel sans réécrire l'horodatage source.

### E2. Runs

- Réparer d'abord le schéma `runs → tasks` sur copie.
- Remapper les tâches par `task_merge_map`.
- Refuser tout run dont le projet ou la tâche restent ambigus.
- Ne jamais relancer automatiquement un run historique pendant la fusion.

### E3. Scheduler

Le scheduler reste un sous-système séparé :

- importer `run_history` dans une table d'archive ou une base scheduler candidate dédiée ;
- comparer les 12 245 lignes par `(job, run, horodatage, statut)` ;
- conserver `jobs.json` comme historique tant que chaque définition n'est pas validée ;
- ne réactiver aucun job importé ;
- vérifier les claims, leases et runs orphelins avant publication.

**Critère de sortie E :** événements, runs et historique scheduler sont traçables à leur source et aucun effet externe n'est déclenché.

## 9. Phase F — correction du graphe de connaissances

### F1. Classer les arêtes

Conserver les 427 401 arêtes valides. Pour les 268 866 arêtes en quarantaine, regrouper par identifiant manquant et par motif :

- `source_node_missing` : 182 169 lignes ;
- `target_node_missing` : 86 697 lignes.

Le rapport doit aussi conserver le nombre d'identifiants distincts, les types de relation et les projets concernés.

### F2. Reconstituer les nœuds prouvables

- retrouver les fichiers, fonctions et classes dans le dépôt correspondant ;
- comparer les identifiants RepoWise ou les chemins normalisés ;
- créer une correspondance uniquement si le contenu ou la signature fournit une preuve ;
- traiter `class:UNKNOWN/*` comme ambigu tant qu'une cible ne peut pas être établie.

### F3. Réattacher et dédupliquer

- réattacher les arêtes via `node_merge_map` dans une copie ;
- dédupliquer uniquement les lignes strictement équivalentes après remappage ;
- conserver les propriétés et la provenance des doublons regroupés ;
- laisser en quarantaine les relations sans preuve.

### F4. Vérifier l'impact

Comparer avant/après : nombre de nœuds, arêtes, relations distinctes, types, composantes, résultats de recherche et `impact_analysis` par projet. Aucune tâche ou note ne doit disparaître à cause d'une correction de graphe.

**Critère de sortie F :** zéro FK invalide dans la candidate ; chaque arête supprimée ou fusionnée possède une ligne de décision et une copie source restaurable.

## 10. Phase G — validation fonctionnelle et restauration

Sur une troisième copie indépendante :

- restaurer la candidate avec l'API SQLite ;
- exécuter `integrity_check`, `foreign_key_check`, contrôles d'index et tests de lecture API ;
- vérifier l'isolation entre deux projets ayant des identifiants de tâche identiques ;
- tester lecture, édition, progression, clôture, audit et recherche mémoire ;
- vérifier que les jobs scheduler restent arrêtés ;
- simuler une restauration après interruption avant publication.

Les tests doivent utiliser Python 3.13 documenté, `DEVCORE_LOCAL_ROOT` et `DEVCORE_DATA_ROOT` temporaires, sans données actives, Dropbox ou index RepoWise réel comme fixtures.

**Critère de sortie G :** restauration complète réussie, tests ciblés verts, empreintes documentées et aucun conflit non classé bloquant ignoré.

## 11. Phase H — approbation et bascule

Préparer un dossier de décision contenant :

- manifeste des sources et de la candidate ;
- rapports de projets, tâches, événements, runs et scheduler ;
- rapport des arêtes réattachées, conservées et rejetées ;
- liste des conflits résolus et des éléments `needs_review` ;
- sauvegardes et procédure de retour arrière ;
- résultat des tests et limites restantes.

La bascule ne peut commencer que si :

- `ready_for_cutover=true` est produit par le rapport ;
- les projets provisoires ont une décision ;
- les conflits de tâches sont tous classés ;
- la politique des arêtes restantes en quarantaine est approuvée ;
- le gel des écrivains est actif ;
- une restauration indépendante a réussi.

Pendant la bascule :

1. arrêter proprement les écrivains ;
2. capturer une dernière sauvegarde et son empreinte ;
3. publier la candidate avec permissions et racines correctes ;
4. démarrer l'API en mode lecture contrôlée ;
5. vérifier santé, isolation, compteurs et audit ;
6. réactiver les écrivains progressivement ;
7. conserver l'ancienne base en lecture seule jusqu'à la fin de la période d'observation.

## 12. Retour arrière

Déclencher le retour arrière si une intégrité échoue, si une lecture inter-projet est possible, si un compteur attendu change sans explication, ou si un événement/runs est perdu.

La procédure consiste à arrêter les écrivains, restaurer la dernière sauvegarde validée, vérifier les empreintes, redémarrer en lecture contrôlée, puis consigner l'incident. Aucun retour arrière ne doit supprimer la candidate ni les rapports.

## 13. Décisions encore nécessaires

1. Rattachement ou maintien séparé des projets `scripts` et `xtream_universal_manager`.
2. Politique de conservation des 268 866 arêtes non résolues.
3. Règle pour les 8 conflits de statut/progression et le titre divergent.
4. Conservation de `Scheduler/scheduler.db` comme archive séparée ou import dans une table d'historique.
5. Date et durée de la fenêtre de gel.
6. Durée de conservation de la base source après bascule.

## 14. Références

- `docs/audit-2026-09-30/copie-locale-autre-poste-2026-10-02.md`
- `docs/audit-2026-09-30/execution-2026-10-05.md`, passages v228–v233
- `plans/2026-10-01-devcore-local-multiutilisateur.md`
- `DEV_CORE/Scripts/backup_local_state.py`
- `DEV_CORE/Scripts/preview_sqlite_fk_migration.py`
- `DEV_CORE/Scripts/reconcile_sqlite_candidate.py`
- `DEV_CORE/Scripts/prepare_individual_pilot_copy.py`
