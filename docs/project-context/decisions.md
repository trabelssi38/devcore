# Registre des décisions — DevCore

Version : 1. Revue : 2026-10-26. Les décisions du plan décrivent une direction ;
leur statut « en vigueur » ne prouve pas leur déploiement.
Toute nouvelle décision doit préciser validation, source et remplacement.
Le lecteur borné utilise le [registre structuré](context.json) ; cette table
en est une synthèse lisible, à mettre à jour avec le registre.

| ID | Statut | Date / validation | Décision et justification | Source / remplacement |
|---|---|---|---|---|
| D-001 | Remplacée | Date initiale non établie ; demande utilisateur dans ce fil | Chercher un hébergement cloud gratuit. L'utilisateur a ensuite choisi de déployer sur ce poste. | Remplacée pour le pilote par D-002. |
| D-002 | En vigueur | 2026-10-01, plan accepté par l'utilisateur | Déploiement local, localhost d'abord. Accès réseau après validation de l'isolation et des comptes. | [Plan §1](../../plans/2026-10-01-devcore-local-multiutilisateur.md) ; instruction utilisateur « je vais deployer en local ». |
| D-003 | En vigueur | 2026-10-01, direction du plan accepté ; état contrôlé le 2026-10-25 | PostgreSQL pour le profil équipe via API commune ; SQLite pour correctif/import. Une seule source de vérité active par instance. Centraliser la concurrence et les droits. | [Plan §3 et L3](../../plans/2026-10-01-devcore-local-multiutilisateur.md) ; [journal v486, v494–v495](../audit-2026-09-30/execution-2026-10-05.md) : troisième reboot autonome, reprise après panne et deux runs du 25 octobre réussis, visibles sous `majdi`. Pilote local ; cause des pertes de santé anciennes inconnue. |
| D-004 | En vigueur | 2026-10-01, contrainte du plan accepté | Séparer données transactionnelles et documents Dropbox ; ne pas tester sur les données actives. Éviter les conflits de synchronisation et préserver les données. | [Plan L0/L9](../../plans/2026-10-01-devcore-local-multiutilisateur.md), instructions des passages programmés. |
| D-005 | Remplacée | 2026-10-10, qualification L5 | DBOS conditionnel. Non installé sur le runtime Python 3.13 et PostgreSQL natif local absent ; écarté pour éviter deux moteurs concurrents et dépendances cloud. | Remplacée pour le pilote par D-008. |
| D-006 | En vigueur | Consignée le 2026-10-02 ; priorité utilisateur confirmée dans ce fil | Réparer les outils, charger une fiche courte et les décisions pertinentes, puis mesurer tokens et qualité sur tâches équivalentes. Ne revendiquer un gain qu'avec preuves comparables. | [Journal L7/L8](../audit-2026-09-30/execution-2026-10-02.md), [protocole](../audit-2026-09-30/protocole-tokens-codex.md). |
| D-008 | En vigueur | 2026-10-10, passage v220 qualifié | Moteur d'exécution durable natif DurableRunEngine (SQLite/PostgreSQL) avec confinement WindowsJob, 8 états, fencing tokens et déduplication des effets externes. | [Plan L5](../../plans/2026-10-01-devcore-local-multiutilisateur.md) ; remplace D-005. |
| D-010 | En vigueur | 2026-10-15, instruction explicite de l'utilisateur | La preuve ESU Windows 10 et la rotation des mots de passe du pilote ne sont pas des critères de cette migration. Conserver les critères TLS, pare-feu limité, origine et essai depuis un second poste pour l'accès LAN. | [Préflight LAN](../audit-2026-09-30/lan-readiness-preflight-2026-10-15.md) ; remplace les exigences ajoutées en v381–v384, sans remplacer D-002. |
| D-011 | En vigueur | 2026-10-26, accord explicite dans ce fil | Retirer l’Agent pilote ; traiter les patchs à la demande avec accord humain avant application. Jobs et hooks conservés. | [Journal v506](../audit-2026-09-30/execution-2026-10-05.md) ; commit déployé `d6cac93`. |

Lecture opérationnelle : appliquer D-002 à D-004, D-006, D-007, D-008, D-010 et D-011 ; conserver D-001
et D-005 pour l'historique. La date exacte de la confirmation D-006 doit être vérifiée dans le fil si nécessaire.

## D-007 — Séparation native / auxiliaire (en vigueur, 2026-10-04)

8787 conserve modèle/fournisseur ; 8789 utilise Gemini explicitement et les
embeddings vont directement au Router 20130. Modèles natifs refusés par Router,
replis explicites et configuration par application. Gemini a passé un appel
réel. Pour le déploiement actuel, l'utilisateur ne prévoit pas OpenAI ni
Anthropic : leurs appels réels sont sans objet pour la clôture de la migration.
Le contrat natif reste testé sur simulation et sa disponibilité réelle sera
qualifiée seulement si ces fournisseurs sont activés plus tard. Voir le
[contrat](../audit-2026-09-30/separation-llm-2026-10-04.md) et le
[journal v431](../audit-2026-09-30/execution-2026-10-05.md).
