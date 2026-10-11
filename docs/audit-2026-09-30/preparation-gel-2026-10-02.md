# Préparation du gel des écritures — 2 octobre 2026

Périmètre confirmé par l'utilisateur : deux postes utilisent `DEV_CORE_DATA` ; DevCore ne tourne plus sur l'autre poste et aucun troisième poste n'est concerné. Les copies de son code et de `DEV_CORE_LOCAL` sont conservées sur `E:`. Cette confirmation permet de préparer une seule fenêtre d'arrêt applicatif sur le poste actuel. **Le gel n'a pas commencé** et aucune donnée active ou Dropbox n'a été modifiée pour ce relevé.

## Écrivains encore observés sur ce poste

Au contrôle ponctuel, `scheduler_tick.py` (PID 9052) et `dashboard_api.py` (PID 19052) sont actifs. Les ports `127.0.0.1:20129`, `:20130`, `:8787` et `:7337` écoutent ; `:20131` n'écoute pas. Le planificateur dynamique garde huit jobs activés, notamment `daily_launch`, `daily_endday`, `weekly_maintenance` et `periodic_task_scan`, alors que le registre statique du dépôt les désactive désormais et que leurs commandes héritées échouent sans contexte explicite. Les PID et ports peuvent changer avant la fenêtre.

`DEV_CORE/Scripts/stop.ps1` ne convient pas tel quel au gel : il termine une session du projet `devcore` sans sélectionner le projet actif, puis tue de force tous les processus portant certains noms ou les ports configurés, sans vérifier leur identité ni les travaux en cours. Ne pas l'exécuter comme procédure de migration. Le mécanisme d'arrêt contrôlé devra être qualifié avant la fenêtre réelle.

## Séquence prévue pour la fenêtre

1. Annoncer l'indisponibilité aux utilisateurs et interdire tout nouveau travail DevCore sur les deux postes. Vérifier une dernière fois que l'autre poste est arrêté et que Dropbox affiche une synchronisation terminée. Ne pas traiter l'arrêt de Dropbox comme un arrêt des écrivains applicatifs.
2. Sur ce poste, identifier à nouveau les processus, leurs commandes et propriétaires ; vérifier les travaux en cours et la file locale. Arrêter d'abord les nouveaux déclenchements du planificateur, puis attendre ou annuler explicitement les travaux actifs avec trace. Arrêter ensuite les services API, Dashboard, watchers et passerelles selon une procédure par identité de processus. Ne pas utiliser le `stop.ps1` actuel.
3. Confirmer qu'aucun processus DevCore ne peut écrire dans `DEV_CORE_LOCAL`, `DEV_CORE_DATA` ou l'index RepoWise concerné ; vérifier que les files `Bus/events` et `Bus/processing` sont stables. Relever de nouveau les ports et les horodatages des fichiers d'état.
4. Capturer une sauvegarde SQLite cohérente et les JSON hérités vers un répertoire hors Dropbox ; calculer les empreintes avant/après. Capturer aussi `scheduler.db`, l'état dynamique et les 13 conflits Dropbox sans sélectionner automatiquement une version. Vérifier restauration, `integrity_check`, comptes et références sur une copie de recette.
5. Réconcilier les deux bases locales et les événements selon [l'analyse de l'autre poste](copie-locale-autre-poste-2026-10-02.md). Si une écriture ou un nouveau conflit apparaît pendant la capture, invalider la fenêtre et recommencer à partir d'un nouvel état stable.
6. Garder les originaux et les sauvegardes jusqu'à validation de la nouvelle source de vérité et des clients CLI, MCP et Cockpit. La réouverture des écritures exige les critères L3 à L9 ; elle n'est pas déclenchée par ce document.

La date de la fenêtre et l'arrêt contrôlé du poste actuel restent à préparer lorsque la migration de recette, les tests de restauration et la nouvelle API seront prêts. Les documents Dropbox peuvent continuer à se synchroniser hors état transactionnel.
