# Présentation Cockpit équipe — 18 octobre 2026

Demande : retrouver l'affichage du terminal historique pour les sections dont
les sources existent dans le déploiement PostgreSQL, avec droits par projet.

Le rendu réutilise les cartes de tâches, groupes de worktrees, étapes cochées,
bulles de détails et boutons de l'ancien terminal. Les deux vues reçoivent les
mêmes sections structurées : mémoire, budget, événements, plugins, graphe,
planifications, consommation par modèle et appels récents, runs et services.
Les compteurs Metrics Service décrivent les événements et runs récents, les jetons
attribués et l'absence de coûts. L'Event Bus retrouve ses cartes datées ; Plugin SDK
et les types de nœuds du graphe retrouvent leurs compteurs. L'onglet Configuration
présente les paramètres observables en lecture seule, sans formulaire de clés ou
commandes d'administration partagées. Les alertes sans budget et la conformité non
mesurée sont explicites ; aucun résultat « conforme » n'est présumé.
La santé RepoWise lit uniquement l'index local du répertoire enregistré pour le
projet et l'identifie comme un instantané. Aucun score par défaut n'est créé.

La pagination conserve une limite de 60 tâches, permet d'ouvrir les tâches plus
anciennes et conserve la page lors du rafraîchissement. Le bandeau affiche le
nombre total du projet, le port Gateway 20131 et les états du superviseur.
Les champs texte des cartes sont échappés, les bulles utilisent `textContent`.
Les huit étapes historiques de T-341 sont encore dans `tasks.metadata` (tableau).
Une correction d'encodage réversible est appliquée à l'affichage de ces libellés,
sans écrire dans la base. Les tests utilisent exclusivement des racines temporaires.

Limites des sources : les coûts, taux de cache, fichiers modifiés et sessions IDE
historiques ne sont pas attribués dans le schéma actif d'usage LLM. Le panneau
montre les jetons fournisseur, modèles et appels du projet ; les interactions
affichent les événements attribués, sans inventer les autres champs. Les dates
et worktrees non renseignés restent absents ou explicitement non renseignés.
Les pourcentages statiques d'économie de l'ancien template ne sont plus présentés
comme des mesures. Les liens documentaires historiques non publiés sont désactivés.

Validation : 26 tests ciblés passent (projection, présentation et autorisation).
Les deux vues, la bulle Détails et le panneau Interactions ont été contrôlés dans
le navigateur sur un aperçu synthétique isolé, port loopback 20136. Les captures
de démonstration sont sous `E:/DevCoreRuntime/qualification/terminal-parity-review`.
La lecture opérationnelle PostgreSQL confirme 398 tâches devcore et 13 scripts ;
T-341 se trouve dans la page d'offset 120 et fournit huit lignes de détails avec
encodage corrigé. Aucune donnée active n'a été utilisée comme fixture de test.

Le candidat nécessite une bascule élevée de DevCoreGlobal, suivie du contrôle
de l'interface avec une session réelle. L'ancienne source reste disponible pour
le retour arrière ; aucun changement du schéma ou du pare-feu n'est requis.

Le préflight réel a détecté un type PostgreSQL absent des premières fixtures :
`SUM(bigint)` est renvoyé en `Decimal` par pg8000. Les compteurs sont convertis en
entiers avant leur projection JSON, et le cas Decimal est maintenant dans le test.
`verify_cockpit_presentation_candidate.py` impose une sérialisation JSON et rend
les deux pages en mémoire sur la base explicitement ciblée. Il ne sauvegarde ni
données projet ni HTML réel. Il passe pour devcore, scripts et la page historique
d'offset 120 (un détail, huit étapes). Ce contrôle précède la bascule Windows.
