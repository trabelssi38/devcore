# Fenêtre de gel historique post-L9 — procédure exécutable

Statut : **exécutée le 14 octobre 2026**. Le profil PostgreSQL individuel v250 reste
actif sur `127.0.0.1:20129`. Ce gel vise les anciennes écritures SQLite/JSON et
leur archivage ; il ne constitue pas une seconde bascule PostgreSQL.

## Confirmation requise de l'utilisateur

1. Confirmer que l'autre poste qui utilisait `DEV_CORE_DATA` est arrêté et ne
   lance aucun DevCore, Scheduler, hook ou synchronisation de données actives.
2. Vérifier dans l'interface Dropbox de ce poste que la synchronisation affiche
   **À jour**, sans conflit en attente. Le client Dropbox peut rester ouvert.
3. Choisir une courte fenêtre durant laquelle personne ne lance de commande
   historique DevCore ni de session utilisant les anciens JSON/SQLite.

Ces confirmations sont une preuve humaine datée ; le scan WMI local ne peut pas
les établir. Ne pas interrompre `DevCoreIndividual` ou PostgreSQL uniquement
pour ce gel historique : ils sont la source active du profil individuel.

## Préflight automatique pendant la fenêtre

1. Relever l'heure UTC, le commit Git, les services/ports et les processus par
   PID, exécutable et rôle. Exclure les processus du contrôle lui-même.
2. Résoudre explicitement les **racines historiques** `DEVCORE_LOCAL_ROOT` et
   `DEVCORE_DATA_ROOT` à capturer. Ne jamais supposer que les racines de recette
   `p0-services-20261012` sont les données historiques actives.
3. Vérifier les travaux/runs en cours et les files `Bus/events`, `Bus/processing`.
   Si un Scheduler historique est présent, demander son arrêt coopératif avec
   son profil exact ; ne pas utiliser `Scripts/stop.ps1` pour cette migration.
4. Confirmer qu'aucun écrivain historique ne demeure et que les tailles,
   horodatages et empreintes restent stables pendant la fenêtre d'observation.
   La présence de Dropbox seule ne constitue pas une écriture historique.

## Capture et validation

1. Capturer vers un **nouveau** répertoire hors des deux racines sources et hors
   Dropbox avec `capture_migration_snapshot.py --source-local <racine-locale>
   --source-data <racine-partagée> --output <nouvelle-destination>`.
2. Le script refuse un WAL SQLite non vide, une destination existante ou sous
   les sources, et toute mutation détectée entre les empreintes avant/après.
   Il copie les bases SQLite de façon cohérente ainsi que les fichiers locaux
   non SQLite (dont `Scheduler/jobs.json`) et les documents partagés.
3. Valider le manifeste : `source_stable=true`, chaque base `integrity=ok`,
   et les nombres de fichiers sont expliqués. Les violations FK historiques
   sont enregistrées, pas supprimées ; elles ne rendent pas la copie prête pour
   une bascule. Restaurer la copie dans une racine de qualification distincte
   et vérifier les empreintes.
4. Conserver les originaux et l'archive avant toute décision de nettoyage.

## Arrêt de la fenêtre

Invalider la capture si un écrivain apparaît, si Dropbox signale un conflit,
si un WAL reste actif, si une empreinte change, si une base échoue aux contrôles
ou si la restauration diffère. Conserver le rapport d'échec ; reprendre avec
une nouvelle destination après correction. Ne jamais remplacer automatiquement
la source PostgreSQL v250 par l'archive historique.

## Critère de clôture

Le gate est clos seulement avec : confirmations humaines datées, inventaire des
écrivains à zéro, manifeste stable, restauration sur copie réussie et journal
de la fenêtre. L'accès réseau externe et l'activation des jobs globaux restent
des décisions distinctes conformément à D-002 et D-009.

## Exécution du 14 octobre 2026

- Confirmations humaines reçues : autre poste arrêté, Dropbox « À jour », fenêtre
  de maintenance autorisée. Le scan local n'a trouvé aucun écrivain historique.
- Sources : `C:\Users\Administrateur\AppData\Local\DEV_CORE_LOCAL` et
  `C:\Users\Administrateur\Dropbox\DEV_CORE_DATA`. Capture :
  `E:\DevCoreRuntime\qualification\historical-freeze-20261014-130504`.
- Manifeste : `source_stable=true`, 3 143 fichiers source, 3 142 capturés ;
  l'écart est l'archive `devcore-before-t532-correction-20260928-0907.db`,
  exclue car son intégrité SQLite échoue. `devcore.db` est intègre mais garde
  268 912 violations FK historiques, explicitement tracées.
- Restauration de contrôle : `E:\DevCoreRuntime\qualification\historical-restore-20261014\devcore.db`,
  empreinte SHA-256 `78b71bb0d6a09888be19bc040fe303d6a116116c83c07fa8f4987862963768ad`,
  identique au manifeste.
