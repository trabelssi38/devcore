# Prochaines étapes après la qualification L9

Date de suivi : 2026-10-11

Le pilote individuel local est qualifié après redémarrage Windows. Les trois
chantiers ci-dessous restent ouverts et doivent être menés dans cet ordre.

## 1. Gel et bascule des écritures historiques

Objectif : préserver une copie cohérente de l'historique, arrêter les écrivains
historiques, puis basculer explicitement vers la source de vérité retenue.

Préconditions :

- inventorier les écrivains et leurs processus sur les deux postes connus ;
- notifier et arrêter les sessions/runs avec la procédure de drain coopératif ;
- produire une sauvegarde horodatée et ses empreintes ;
- valider la réconciliation sur copie, y compris les 268 866 arêtes orphelines,
  les deux projets `needs_review` et les 460 identifiants textuels ;
- obtenir un rapport sans écrivain actif avant toute bascule.

Critères de sortie : journal de gel, manifeste de sauvegarde, empreintes avant/
après, zéro écrivain historique actif et procédure de retour arrière testée sur
copie. Aucune écriture Dropbox ou production ne doit être modifiée pendant la
qualification préparatoire.

## 2. Déploiement équipe PostgreSQL réel

Objectif : installer un cluster PostgreSQL local dédié au profil équipe et
déployer le schéma v2 avec le rôle applicatif sans `BYPASSRLS`.

Ordre d'exécution :

1. installer PostgreSQL et choisir les chemins de données hors Dropbox ;
2. créer la base, le rôle propriétaire de migration et le rôle applicatif ;
3. appliquer le schéma et les politiques RLS ;
4. importer un snapshot gelé en mode dry-run, puis vérifier comptes, projets,
   tâches, versions, runs, événements et audit ;
5. exécuter les tests de concurrence et d'isolation par projet ;
6. basculer l'API vers PostgreSQL uniquement après validation des rapports.

Critères de sortie : `integrity_check` logique, zéro violation RLS sur fixtures
réelles, migrations répétables, sauvegarde/restauration testée et API sans
double source de vérité. Le cluster réel n'est pas encore qualifié.

## 3. Activation réseau et OTLP/Langfuse

Objectif : ouvrir l'accès réseau après qualification des identités et de
l'isolation, puis activer l'observabilité distante de façon bornée.

Garde réseau :

- conserver le pilote sur localhost tant que l'authentification multi-utilisateur,
  les ACL par projet et la récupération après panne ne sont pas validées ;
- documenter l'adresse d'écoute, le pare-feu, les origines CORS et les ports ;
- vérifier qu'aucun service de développement n'est exposé par inadvertance.

OTLP/Langfuse :

- configurer un endpoint de recette avec authentification et délai borné ;
- valider redaction, attribution projet/tâche, taille maximale et drainage au
  shutdown ;
- mesurer les files, les pertes acceptées et le comportement lorsque le réseau
  distant est indisponible ;
- activer en continu seulement après ces preuves et une décision de rétention.

## 4. Remise en service coordonnée de la pile globale

Objectif : réactiver le mode global et ses dépendances historiques après la
qualification L9, sans considérer le seul service `DevCoreIndividual` comme
une qualification de la plateforme complète.

Composants à démarrer et vérifier ensemble :

- cockpit global `/index.html` et `/index_terminal.html` ;
- RepoWise (index, serveur local et synchronisation) sur `7337` ;
- Gemini Router sur `20130` ;
- API Gateway sur `20131` ;
- Headroom natif sur `8787` et auxiliaire sur `8789` ;
- Scheduler et ses jobs persistants.

Ordre d'exécution :

1. démarrer la pile via le lanceur global prévu et enregistrer les PID, ports
   et journaux de chaque composant ;
2. vérifier les endpoints de santé et les identités de route, notamment le
   fournisseur et le modèle réellement utilisés par chaque profil LLM ;
3. vérifier que RepoWise est à jour avec le commit courant avant d'afficher
   ses résultats dans le cockpit ;
4. ouvrir les deux interfaces globales et vérifier leurs API, flux et actions
   sur une copie isolée ;
5. tester l'arrêt, le redémarrage et la reprise du Scheduler et des services
   dépendants ;
6. documenter explicitement les services démarrés automatiquement et ceux
   restant manuels.

Critères de sortie : tous les ports déclarés dans `Config/network.json` qui
sont requis par le mode global répondent, chaque réponse de santé est liée au
bon composant, RepoWise n'est pas en retard sur `HEAD`, les deux cockpits
globaux sont utilisables sur copie, et une reprise après redémarrage est
consignée. Le démarrage de `DevCoreIndividual` seul ne satisfait pas ce gate.

## État et décision

Ces étapes sont des travaux à réaliser, pas des fonctionnalités déclarées
terminées. Le compte Windows `Administrateur` reste l'exception acceptée pour
le pilote L9 ; il ne doit pas être confondu avec la qualification PostgreSQL,
réseau ou observabilité.
