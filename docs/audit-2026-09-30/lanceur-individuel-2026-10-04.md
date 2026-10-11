# Lanceur Dashboard du candidat individuel

`Scripts/launch_individual_candidate.py` exige explicitement snapshot, SHA-256
du manifeste provenant d'une source fiable, racines locales/documents existantes
séparées, magasin d'identités existant sous la racine locale et port. Aucun
bootstrap, migration, création de compte ou service Windows n'est effectué.
Il refuse liens/jonctions dans ces chemins et ne répare pas les permissions.

Avant import du serveur : empreinte du manifeste, allowlist/empreintes de tous
les fichiers, empreinte du manifeste répétée, moteur installé sous sys.prefix,
permissions NTFS du magasin d'identités et SQLite corrigé vérifiés. La sonde NTFS
ne doit pas ouvrir SQLite. Profil individual et bind 127.0.0.1 imposés ; origine
CORS liée au port exact, proxy_headers désactivé. Les valeurs legacy héritées
sont remplacées. Pas de mode LAN ni TLS dans ce lanceur de recette.

Exemple de prévalidation (placeholders à remplacer ; ne pointe vers aucune
fixture ou donnée active par défaut) :

```powershell
& 'E:/DevCoreRuntime/releases/devcore-py31316-20261003/Scripts/python.exe' -I `
  E:/DevCoreRuntime/releases/devcore-py31316-20261003/candidate-control/launch_individual_candidate.py `
  --bundle E:/DevCoreRuntime/releases/devcore-py31316-20261003/individual-platform `
  --manifest-sha256 d38e0c16cf1bb7604811538f015d14bd38c47743b49268e331c81871c6ff9027 `
  --local-root '<racine locale de recette existante>' `
  --data-root '<racine documents de recette existante et séparée>' `
  --identity-store '<racine locale>/Security/identity.db' --port 54321 --check
```

`--check` ne lie aucun port et ne crée aucun magasin. Sans ce drapeau, le serveur
HTTP démarre au port explicite. Utiliser Python -I pour exclure les chemins de
modules ambiants. Les erreurs de prévalidation sortent avec code 2 et un code
générique sans détails de magasin/secret. Le lanceur et son vérificateur sont
conservés dans candidate-control avec manifeste séparé ; protéger ce code et
le runtime sous un compte restreint reste une condition de déploiement.

## Résultat

**12 tests réussis en 9,45 s**, zéro échec/skip : configuration manquante/pin/port,
chemins croisés, identité hors racine, snapshot mêlé aux données, vraie fixture
NTFS privée, prévalidation Python -I/moteur installé sans modification de base,
et lancement HTTP temporaire depuis un snapshot. Environnement legacy hérité
explicitement remplacé dans ces tests.

Le parcours authentifié sur socket localhost temporaire lit alpha, refuse beta
et les routes globales, clôture T-01 avec version 1 et relit l'audit d'Alice/done/v2.
T-01 de beta reste todo/v1. Serveur de test terminé dans finally ; pas de donnée
active/Dropbox, pas d'index réel. Cas HTTP avec bearer, pas un test navigateur
ou MCP, et arrêt de processus de fixture sans qualification d'arrêt gracieux.

Trace : C:/Users/Administrateur/AppData/Local/Temp/devcore-candidate-launcher-7ac9ff82c22243f9bcd079ba3c9b6cf7/tests-final.txt
SHA-256 : 2a78d0d01c0f642bb9811effc799c88b5d21f190fce004091041c0c517d7fbcb.
Contrôles candidate-control : manifest SHA-256
 a1923be9771b0406c0ceefa83d90ff628edf2bbbb04ca0337731b07a6a9b6df3.

La CI installe désormais le moteur sans editable avant la gate et inclut ces
12 tests ; YAML/AST/diff vérifiés, pas de CI distante complète annoncée.
Le wheel doit être présent sous sys.prefix pour la prévalidation isolée.

## Limites

Lanceur Dashboard uniquement ; MCP depuis snapshot reste à qualifier.
Pas de confinement de code, d'attestation authentique/signature du runtime,
ni de protection contre une modification après la vérification. Permissions
NTFS du snapshot/runtime/parents, compte de service, renouvellement/révocation,
lecture en vol, deux profils navigateur, charge, services et rollback restent
à qualifier. Le dossier documents n'est pas certifié hors Dropbox par ce
contrôle de chemins ; cette vérification opérationnelle reste nécessaire.
Aucune activation du candidat ni changement de configuration active.

Extension : [lanceur MCP et contexte durable depuis le snapshot](lanceur-mcp-individuel-2026-10-04.md). Controleurs v2 distincts, aucune bascule.
