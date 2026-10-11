# Profil local et prérequis — 2 octobre 2026

Le fichier [local-team.env.example](../../DEV_CORE/Config/local-team.env.example) décrit uniquement les variables non secrètes du futur profil équipe. Il n'est ni chargé ni adapté à l'instance active. `DEVCORE_LOCAL_ROOT` doit être un répertoire local hors Dropbox ; `DEVCORE_DATA_ROOT` vise les documents partagés et exports historiques, sans base ou file transactionnelle vivante. L'API et les workers devront posséder une configuration explicite de ce profil avant L9.

## Racines explicites — correctif du 3 octobre

Les résolveurs Python `devcore_engine.db` respectent désormais une variable
`DEVCORE_LOCAL_ROOT` ou `DEVCORE_DATA_ROOT` définie, même lorsque le dossier
n'existe pas encore. Le stockage local crée ses parents ; le résolveur de
documents ne crée aucun dossier. Une valeur vide/blanche, un fichier à la place
d'un dossier ou une erreur de création locale provoquent une erreur : aucun
repli vers un autre magasin. Un ancien chemin configuré n'est plus interprété
comme un motif d'autodétection Dropbox.

Avant de lancer un service, corriger ses chemins explicites obsolètes ou vides.
Les valeurs relatives restent compatibles ; le profil équipe exige des chemins
absolus validés. Une variable absente conserve le comportement historique de
découverte ; une variable vide ne signifie donc pas « utiliser le défaut ».
La configuration explicite reste nécessaire pour tous les sous-processus de
recette. Ce correctif n'interdit pas un chemin volontairement choisi dans
Dropbox, une jonction ou un partage réseau et ne migre aucune donnée active.

## Ports au relevé

`Config/network.json` déclare des liaisons `127.0.0.1` pour Dashboard 20129, routeur Gemini 20130, proxy 8787 et RepoWise 7337. Tous quatre écoutent effectivement sur `127.0.0.1`. Le port 8788 écoute également et son processus a été identifié comme adaptateur Anthropic ; il ne figure pas dans ce registre réseau. Le port 20131, prévu pour l'API versionnée, n'écoutait pas au relevé. Aucun port du profil observé n'était lié à `0.0.0.0`, mais l'absence de collision future n'est pas garantie par un seul instantané. Le propriétaire du port 8787 n'a pas été confirmé par son nom de processus : vérifier sa commande et sa configuration avant un arrêt ou une ouverture réseau.

Les ports occupés correspondent aux services actuels ; ne pas lancer une seconde instance sur ces ports. Refaire `Get-NetTCPConnection -State Listen` et vérifier l'identité des propriétaires juste avant tout démarrage de recette ou bascule. `Scripts/stop.ps1` tue des PID par port sans cette vérification et ne sert pas de procédure sûre de migration.

## Système et moteurs

Le poste rapporte Windows 10 Professionnel 64 bits, version 10.0.19045. Le niveau de correctifs et l'aptitude à une exposition réseau n'ont pas été qualifiés ; le pilote reste lié à localhost. `docker version` ne joint pas le moteur Docker Desktop Linux ; le service `com.docker.service` est arrêté. `wsl --status` indique WSL version 2 avec `docker-desktop` comme distribution par défaut, sans prouver qu'une distribution de travail ou un moteur conteneur fonctionne. Aucun `psql`, `pg_ctl` ou service Windows PostgreSQL n'a été trouvé. Il faut donc installer et qualifier PostgreSQL séparément en L3, sans supposer que Docker ou WSL puissent l'héberger.

Python 3.13.3 est qualifié pour l'[environnement de recette verrouillé](environnement-python-2026-10-02.md) ; les services en cours utilisent encore le Python existant. Les chemins, ACL Windows, espace disque et sauvegardes devront être vérifiés à nouveau avant de déplacer des données actives vers `E:/DevCoreRuntime`.
