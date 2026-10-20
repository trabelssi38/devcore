# Sauvegarde et maintenance du profil équipe — politique candidate

La maintenance historique `weekly_maintenance.ps1` ne devient pas un job du
profil équipe. Elle couvre des fichiers SQLite/JSON et des caches partagés,
alors que PostgreSQL est maintenant la source transactionnelle. Aucun script
de nettoyage, copie Dropbox ou rotation historique n'est réactivé par la
phase 3.

Une sauvegarde de ce profil doit être opérée au niveau du service, sous une
identité de maintenance distincte des membres projet. Le dump PostgreSQL
complet au format custom doit inclure organisations, utilisateurs,
appartenances, projets, tâches, événements, runs, hooks, planifications,
historique et migrations. Les fichiers de configuration privés et clés
nécessaires au redémarrage sont inventoriés dans une archive séparée à ACL
restreinte ; les dépôts Git sont conservés par leurs propres remotes et les
index RepoWise sont reconstruisibles. Dropbox n'est pas une destination de
sauvegarde automatique du pilote.

Politique proposée pour qualification : un dump quotidien et un point
hebdomadaire, avec sept quotidiens et quatre hebdomadaires conservés dans
`E:/DevCoreRuntime/backups/private`. Chaque archive porte SHA-256, taille,
version de schéma, date UTC et inventaire `pg_restore --list`. La rotation ne
supprime jamais le dernier point restaurable et ne commence qu'après une
restauration complète d'essai réussie sur une **nouvelle base temporaire**.
Cet essai vérifie les comptes essentiels, les clés étrangères, RLS sous le
rôle applicatif et un parcours API autorisé/refusé sur deux projets. Les
secrets ne figurent ni dans les commandes de run, ni dans l'historique projet.

Une panne de dump, une empreinte incorrecte ou un test de restauration raté
conserve les archives et produit un échec visible. L'activation exige un
script de sauvegarde et de retour arrière qualifiés, des ACL vérifiées, un
emplacement dont la capacité est surveillée, et un essai de restauration
documenté. **Aucun job de sauvegarde ou de purge n'est actuellement créé.**
