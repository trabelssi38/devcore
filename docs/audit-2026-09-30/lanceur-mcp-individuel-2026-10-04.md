# Lanceur MCP individuel depuis un snapshot épinglé

Le lanceur `Scripts/launch_individual_mcp_candidate.py` reprend le vérificateur
commun du lanceur HTTP. Exiger snapshot/manifeste SHA-256 fiable, moteur installé
sous sys.prefix, origine HTTP 127.0.0.1 avec port explicite, credential existant
privé NTFS et projet. Capabilities fermées par défaut : contexte uniquement.
--tasks read/write, --audit et --delete sont des options séparées ; delete exige
write. Toutes les valeurs héritées legacy/write/delete/audit sont remplacées.
Le fichier credential est contrôlé avant admission puis relu par le client à
chaque appel. Aucun secret n'est imprimé. Sans --check, stdout appartient au
protocole MCP ; un refus de prévalidation retourne code 2 sur stderr JSON.

Les scripts serveur du snapshot n'importent pas les hooks/handlers historiques
en individual. Aucun accès local aux magasins métier/identités côté MCP : l'API
contrôle les droits à chaque appel. Il ne faut pas pointer ce candidat vers les
données actives avant qualification de la bascule.

```powershell
& 'E:/DevCoreRuntime/releases/devcore-py31316-20261003/Scripts/python.exe' -I `
  E:/DevCoreRuntime/releases/devcore-py31316-20261003/candidate-control-v2/launch_individual_mcp_candidate.py `
  --bundle E:/DevCoreRuntime/releases/devcore-py31316-20261003/individual-platform `
  --manifest-sha256 d38e0c16cf1bb7604811538f015d14bd38c47743b49268e331c81871c6ff9027 `
  --api-url http://127.0.0.1:54321 --credential-file '<fichier privé de recette>' `
  --project '<projet de recette>' --tasks read --audit --check
```

Sans --check : serveur stdio. La prévalidation ne vérifie pas une autorisation
HTTP, la disponibilité du serveur ou l'expiration du jeton ; ces contrôles se
font lors des appels. Le timeout socket n'est pas un délai global strict.
Le launcher/vérificateur sont conservés sous candidate-control-v2, sans écraser
candidate-control ; manifest SHA-256
`324d35c970546344e2d07d2b7b4ee98b41618c2bc676208bfa2799c82e5f51da`.

## Qualification

**20 tests distincts réussis en 23,48 s**, zéro skip/échec, les deux fichiers
lanceurs (HTTP 12 + MCP 8). Les refus de capacités/origine/credential précèdent
les échanges stdio ; configuration absente ne crée aucun magasin. Régression
HTTP rejouée après extraction du vérificateur commun.

Parcours réel : snapshot HTTP sur socket temporaire et trois processus MCP
Python -I utilisant le moteur wheel installé. Default expose seulement contexte ;
lecture expose tâches/audit sans mutation ; write expose clôture sans suppression.
Fiche Alpha et décision effective chargées via API, décision remplacée exclue,
ligne UTF-8 mesurée <= 2 000 octets. Lecture Alpha, refus Beta, mutation explicitement
activée avec version 1, audit Alice/done/v2, puis révocation et refus HTTP 401.
MCP ping réussi. T-01 Beta reste todo/v1, racines MCP vides et snapshot intact.
Tous les clients et l'API temporaire arrêtés ; aucun port/service actif modifié.

Trace `C:/Users/Administrateur/AppData/Local/Temp/devcore-mcp-launcher-cd93549451044892ae6fbca3e703585c/tests-final.txt`, SHA-256 `b482c2a9db11532aacd84a0541b3fb9c2fc3ba0ddc3203dd3055d50f9e35a221`.
Gate CI inclut le nouveau fichier ; AST/YAML/diff ciblés vérifiés, aucune CI
complète distante annoncée. Sources/roots temporaires avant imports/processus,
pas de tests sur Dropbox/données actives/index réel.

## Limites

Pas une nouvelle conversation Codex qualifiée ni une économie de tokens mesurée.
La suppression MCP, rotation/expiration et toutes les pannes ne sont pas rejouées
sur ce snapshot dans ce passage (couvertures antérieures à distinguer). Parents/
runtime/code NTFS, modifications après vérification, service Windows, HTTPS/LAN,
charge et rollback opérationnels restent ouverts. Les lanceurs/control files et
le runtime doivent être protégés : un pin ne remplace pas ces droits OS.
Pas de bascule ou modification de la configuration active.
