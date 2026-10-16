# Pilote interactif de deux comptes sur le service actif

Date : 2026-10-15. Service attendu : `DevCoreIndividual` v252 propre sur
`http://127.0.0.1:20129/project`. Le contrôle HTTP réel avec `majdi` et
`mohd`, puis la charge de 20 sessions, sont déjà réussis. Ce protocole vérifie
le comportement de l'interface dans deux espaces de cookies indépendants.

1. Ouvrir l'adresse dans une fenêtre Edge normale et dans une fenêtre Edge
   InPrivate. Les deux fenêtres doivent rester ouvertes en même temps.
2. Dans la fenêtre normale, ouvrir `devcore` avec `majdi`. Dans InPrivate,
   ouvrir `devcore` avec `mohd`. Saisir les mots de passe uniquement dans les
   formulaires locaux. Vérifier que les deux fenêtres affichent leur propre
   identité, le projet `devcore` et les tâches, sans message d'erreur.
3. Actualiser la fenêtre `majdi`, puis la fenêtre `mohd`. Les deux doivent
   conserver leur session et leurs tâches. Ne modifier aucune tâche.
4. Déconnecter `majdi` dans la fenêtre normale. Actualiser `mohd` dans
   InPrivate : sa session et ses tâches doivent rester disponibles.
5. Dans la fenêtre normale, ouvrir `scripts` avec `majdi` et vérifier la
   lecture de ce projet. Déconnecter ensuite `majdi`.
6. Déconnecter `mohd` dans InPrivate, puis tenter `scripts` avec `mohd`.
   L'interface doit refuser l'accès. Ne pas confondre ce refus avec un mot de
   passe erroné : le test HTTP indépendant a déjà confirmé HTTP 403.

Consigner uniquement les succès ou échecs des étapes 2 à 6, sans mot de passe,
cookie, capture contenant des données privées ni sortie d'outils développeur.
Si un échec apparaît, conserver la v252 active et transmettre l'étape exacte et
le message visible pour diagnostic.

## Contrôle interactif effectué le 15 octobre

Sur le service actif v252, le navigateur intégré a ouvert `majdi` sur `devcore`
et `mohd` sur `devcore` successivement. Les deux identités, le titre du projet
et 20 lignes de tâches étaient visibles. L'actualisation de `mohd` a conservé
son identité et les 20 lignes. Après déconnexion, le formulaire est revenu et
l'espace de travail était masqué. La tentative de `mohd` sur `scripts` a affiché
« Connexion refusée » et n'a pas ouvert l'espace de travail ; le contrôle HTTP
indépendant avait établi HTTP 403 pour cette même restriction. `majdi` a ensuite
ouvert `scripts` : son identité, le projet et 13 lignes de tâches étaient
visibles. Sa déconnexion a été vérifiée dans les deux onglets après
actualisation. Aucune tâche n'a été modifiée.

Les deux onglets du navigateur intégré partagent leurs cookies : le second a
repris la session du premier, et une déconnexion dans l'un a fermé la session
visible dans l'autre. Ils ne peuvent donc pas démontrer l'étape de deux sessions
simultanées et indépendantes. À la fin de ce contrôle intégré, les étapes 2 à 4
du protocole ci-dessus restaient à faire dans deux profils de navigateur
distincts (Edge normal et InPrivate, ou deux navigateurs séparés). Les accès
et la charge simultanée ont été vérifiés
par HTTP réel, mais ne remplacent pas ce contrôle d'interface.

## Recette à deux navigateurs déclarée réussie

Le 15 octobre, l'utilisateur a confirmé le succès des étapes 2 à 6 du
protocole dans deux profils de navigateur indépendants. Cette attestation
couvre les deux connexions simultanées, leur maintien après actualisation,
l'indépendance de la session `mohd` après déconnexion de `majdi`, la lecture
de `scripts` par `majdi` et le refus de `mohd` sur `scripts`. Aucun mot de
passe ni cookie n'a été consigné. Le contrôle indépendant effectué ensuite
confirme `DevCoreIndividual` et PostgreSQL en marche, avec `/project` et
`/api/status` à HTTP 200. Gate du pilote interactif : **close sur
attestation utilisateur** ; aucun rapport de navigateur automatisé distinct
n'a été produit pour les étapes simultanées.
