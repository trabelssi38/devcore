# Audit des données du Cockpit — 2026-10-18

Lecture opérationnelle du projet `devcore` à 14:19 UTC, sans mutation des données.
Source installée : `pg-global-source-20261018-terminal-coldboot`, commit attendu
`891218981164082f00fe614d1fb41af4fd247492`. Projection exécutée depuis cette
source avec la configuration PostgreSQL installée et des racines locales
temporaires distinctes. Les deux rendus HTML sont construits en mémoire.

| Section | Observation actuelle | Portée réelle |
|---|---|---|
| Projets | 398 tâches, 393 terminées, 99 % | Comptages PostgreSQL ; incluent les tâches supprimées |
| Tâches | 60 affichées sur 398, détails issus des métadonnées | Pagination réelle ; une ligne DELETED T-388 reste affichée |
| Services | Six composants vrais, manifeste récent | Supervision ; les cinq sondes HTTP indépendantes répondent 200 |
| RepoWise Health | 8,4/10, 1 418 fichiers, commit d54a91944e95 | Mesures enregistrées du dépôt du projet ; index de quatre jours selon MCP, modifications locales non couvertes |
| Automation Hooks | Aucun job planifié | Lecture de schedules et schedule_history ; ne recense pas tous les hooks externes |
| Consommation et activité | Un appel google-gemini/gemini-2.5-flash ; 5 jetons entrée, 1 sortie ; aucun run | project_llm_usage et runs ; uniquement appels attribués au projet, pas la consommation globale des IDE |
| Composition du contexte | Aucune entrée mémoire | Agrégation memory_entries par task_type ; ne mesure pas la composition des prompts |
| Metrics Service | 10 événements récents, 0 run récent, 6 jetons | Fenêtres limitées à 10 pour événements/runs ; compteurs LLM cumulés sans filtre quotidien |
| Budget, alertes, conformité | Aucun budget ; alertes non configurées ; conformité non mesurée | Aucun indicateur de coût ou de conformité réel disponible |
| Événements | Dix enregistrements datés, dont TaskDeleted du 18 octobre | Historique PostgreSQL réel, mélangeant événements récents et historiques |
| Graphe | 2 268 nœuds, 681 642 arêtes | Graphe historique attribué au projet, hors quarantaine ; pas une reconstruction en direct du code |
| Plugin SDK | 0 plugin, contrôles non mesurés | Registre PostgreSQL du projet ; pas l'inventaire des plugins Codex installés |
| Configuration | Projet, profil équipe, période de rafraîchissement et services | Lecture seule ; paramètres déclarés et santé supervisée |
| Interactions des tâches | Événements issus des dix événements récents du projet | Pas un historique exhaustif par tâche ; jetons, coûts et fichiers non attribués |

Les deux vues produisent les dix sections sans placeholder non résolu.
Les anciennes affirmations statiques de réduction de tokens sont absentes et
l'appel initial loadSettings() est supprimé. Les coûts, dépassements,
sollicitation des services et contrôles plugins restent explicitement non mesurés.

## Limites et écarts

- Tâches supprimées : la projection n'exclut pas status=deleted dans le total
  ni dans la page. Le pourcentage utilise donc également ces lignes.
- La tâche active de la carte projet est recherchée dans la page de 60 tâches :
  à un offset ultérieur, « Aucune tâche active » peut être trompeur.
- Composition du contexte et Plugin SDK ont une portée plus étroite que leurs titres.
- Santé RepoWise : données réelles mais historiques ; le rendu expose le commit,
  sans avertissement explicite sur l'âge ni sur les changements non indexés.
- Aucun navigateur authentifié n'a été inspecté pendant cet audit : il valide
  les sources et le rendu serveur installé, pas l'exécution JavaScript ni toutes
  les interactions d'une session réelle. La recette HTTP des deux comptes après
  boot figure dans le journal v447 et n'a pas été rejouée ici.

Le Python documenté du 2 octobre est présent mais ne possède pas pg8000 ; la
lecture a donc utilisé le Python 3.13 de la release opérationnelle v254. Le
premier essai a aussi rencontré un refus de nettoyage du répertoire temporaire
`C:/Users/ADMINI~1/AppData/Local/Temp/cockpit-audit-nxv9spc2` ; aucune suppression
forcée n'a été tentée. Aucun test n'a utilisé les données actives comme fixture.
La fiche de contexte avertit card_changed_since_review ; RepoWise utilise un
index de quatre jours et ne retrouve pas team_cockpit, confronté au code installé.
