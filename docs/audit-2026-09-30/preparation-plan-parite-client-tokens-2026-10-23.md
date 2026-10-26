# Préparation du plan parité, client réseau et tokens

Date : 23 octobre 2026. Portée : documentation uniquement.

À la demande de l'utilisateur, création de
[`2026-10-23-parite-client-reseau-mesure-llm.md`](../../plans/2026-10-23-parite-client-reseau-mesure-llm.md),
à exécuter après le plan hooks/jobs du 19 octobre. Les dix points demandés
sont associés à des lots, livrables et preuves de sortie. Les phases 0–5 du
prédécesseur sont des prérequis ; sa phase 6 reste une option distincte avec
décision explicite. Aucun travail d'implémentation ou de déploiement lancé.

Sources relues : plan préalable et sa phase 6, journal v486–v492, contexte
obligatoire obtenu précédemment dans ce fil, protocole tokens Codex, exemple MCP,
contrat de séparation LLM et fichiers locaux du routeur, du compacteur,
du rapport de tokens et du stockage d'usage Gemini. Python de recette présent
au chemin documenté. L'état Git comporte de nombreuses modifications préexistantes ;
elles ont été préservées. Seuls le nouveau plan et cette entrée de journal sont
ajoutés par cette préparation.

RepoWise a été consulté de manière ciblée pour token_report.py, router/policy.py
et postgres_llm_usage.py. L'index annonce le HEAD d54a91944e95, un âge de neuf
jours et des dates relatives incohérentes ; embedder mock, recherche sémantique
désactivée, fichier PostgreSQL absent de l'index. Les constats ont donc été
confrontés aux sources locales. Aucun rafraîchissement de l'index réel effectué.

Limites conservées dans le plan : pas de parité historique générale démontrée,
pas de suppression de DEV_CORE_LOCAL, pas de client réseau Codex complet qualifié,
pas de centralisation RepoWise présumée, pas de passage natif Codex par Headroom
présumé, pas d'économie de tokens acquise. Les essais réels OpenAI/Anthropic
restent conditionnés à une extension explicite du périmètre fournisseur courant.
La stabilité sera réévaluée sur les preuves issues du prédécesseur plutôt que
requalifiée artificiellement par la création du document.

Vérification de préparation : contrôle des liens relatifs des deux nouveaux
documents, présence des quinze dossiers historiques et des lots P0–P9,
et `git diff --no-index --check` sur les fichiers ajoutés. Aucun test applicatif
nécessaire pour cette modification documentaire ; aucune recette fonctionnelle
ni résultat de benchmark revendiqué.

## Découpage en phases — complément du 23 octobre 2026

À la demande utilisateur, les lots P0–P9 sont présentés comme phases 0–9,
avec objectif, prérequis, statut initial et travaux. Une synthèse des critères
de passage et des états de suivi est ajoutée. Les identifiants restent stables,
les actions détaillées et les restrictions sont conservées. Aucun début
d’exécution du plan. Contrôle documentaire : dix phases, dix objectifs et
prérequis, liens relatifs et espaces vérifiés.

## Apports ECC intégrés au plan — complément du 23 octobre 2026

À la demande utilisateur, intégration des améliorations retenues de l'analyse
d'[ECC au commit 90606c8](https://github.com/affaan-m/ECC/tree/90606c8315ee09cafc303515c5f33024db6b9882)
(version déclarée 2.2.3). Analyse statique d'une copie temporaire ; aucun script
ECC exécuté ou installé. Sources DevCore confrontées : skills.py (score fixe
0.95), mémoire historique, stockage d'usage Gemini et événements de hooks
PostgreSQL. RepoWise consulté de manière ciblée : dates relatives incohérentes,
embedder mock et couverture incomplète ; lecture locale utilisée pour les constats.

Le plan conserve P0–P9 et ses prérequis. Ajouts : leçons proposées et reprise par
worktree en P3 ; évaluations réelles, télémétrie et contrôles légers en P4 ;
raccordement au bus existant en P5 ; capacités des adaptateurs client et reprise
réseau en P6 ; ingestion des compteurs, déduplication et santé des skills en P7 ;
comparaisons sans contamination de mémoire en P8 ; scénarios de retrait, échec et
rollback en P9. Un tableau fixe les priorités et impose provenance/licence pour
toute reprise de code. Les données transactionnelles restent dans PostgreSQL.

Python 3.13 documenté présent. Les deux documents étaient déjà non suivis dans
Git ; leurs contenus existants et les autres modifications sont conservés.
Vérification documentaire : dix phases et leurs prérequis, liens locaux,
références ECC figées et absence d'espaces de fin de ligne contrôlés. Aucun test
applicatif nécessaire : cette modification ne lance ni implémentation, ni
déploiement, ni appel fournisseur. Aucun gain ou fonctionnalité qualifiée revendiqué.
