# DevCore Engine

The `devcore-engine` package contains the core Python services and CLI for the
DevCore local pilot. The wider repository also contains API, scheduler, MCP,
dashboard and PowerShell entry points. See the repository root README and the
local multi-user implementation plan for operating instructions.

## Candidat Windows L9

Le candidat individuel versionné est installé sous `E:/DevCoreRuntime/releases/devcore-py31316-20261010-l9`.
Ses racines de données sont déclarées dans `individual-service.json` par rapport à la racine du runtime :
`state/local` et `state/data` résolvent aujourd'hui vers `E:/DevCoreRuntime/state/local` et
`E:/DevCoreRuntime/state/data`. Elles restent hors de la release lors d'une mise à jour.
Pour une nouvelle release, la commande `prepare` écrit aussi `windows_startup` dans ce fichier :
`automatic` (valeur par défaut) demande au gestionnaire de services Windows de lancer DevCore
au démarrage du système ; `manual` laisse le démarrage à l'opérateur. Exemple :

```powershell
$release = 'E:/DevCoreRuntime/releases/<nouvelle-release>'
& "$release/Scripts/python.exe" -I "$release/controls/Scripts/install_individual_service.py" `
  --release $release prepare --local-relative state/local --data-relative state/data `
  --windows-startup automatic
```

Choisir ce mode avant `install`. L'option `install --start` lance le service immédiatement,
sans modifier le mode de démarrage Windows. Les profils de schéma 1 existants sont lus comme
`automatic`. Pour changer le mode d'un service déjà enregistré, préparer une nouvelle release
avec le profil voulu puis réinstaller le service depuis cette release ; ne pas éditer la release active
en place. Le chemin de l'exécutable enregistré dans SCM doit correspondre à cette release.

Dans PowerShell, vérifier la release et le cycle de service sur des racines temporaires :

```powershell
$release = 'E:/DevCoreRuntime/releases/devcore-py31316-20261010-l9'
& "$release/Scripts/python.exe" -I "$release/controls/Scripts/verify_engine_release.py" --release $release
uv pip check --python "$release/Scripts/python.exe" --offline
& "$release/Scripts/python.exe" -I "$release/controls/Scripts/qualify_individual_managed.py" --release $release
```

La configuration portable et le magasin d'identité privé sont déjà préparés sur ce poste.
Sur ce poste, `DevCoreIndividual` est enregistré dans SCM sous `.\Administrateur`, configuré
en démarrage automatique et en cours d'exécution. Son profil historique de schéma 1 est
interprété comme `automatic`. Sa release contient un hôte pywin32 et
les DLL Python épinglés par `provenance.json` ; le contrôle ci-dessus doit réussir avant
chaque démarrage. Le droit Windows `SeServiceLogonRight` a été attribué à ce compte.
Pour une réinstallation, exécuter la commande suivante dans une fenêtre PowerShell élevée ;
elle demande le mot de passe dans cette fenêtre uniquement :

```powershell
& "$release/Scripts/python.exe" -I "$release/controls/Scripts/install_individual_service.py" `
  --release $release install --account '.\Administrateur' --start
Get-Service DevCoreIndividual
Stop-Service DevCoreIndividual
Start-Service DevCoreIndividual
```

`Stop-Service` déclenche l'arrêt coopératif du Dashboard et attend le résultat enregistré par
`service_runtime`. Sur ce poste, l'arrêt a produit `outcome=ok`, puis le redémarrage a rendu
`http://127.0.0.1:20129/project` disponible avec HTTP 200. Le démarrage après redémarrage de
Windows reste à vérifier. Le compte Administrateur demandé pour cette installation n'est pas un compte
restreint ; le critère L9 correspondant reste ouvert. La recette temporaire ne valide ni la
bascule des données, ni le pilote à deux comptes. Déplacer la racine du runtime après
l'enregistrement SCM impose de réinstaller le service, dont le chemin exécutable est absolu.

La nouvelle racine `state/local` ne contient pas encore l'ancienne base de tâches. Le passage v228
du journal conserve une copie cohérente sous `E:/DevCoreRuntime/qualification`, puis constate
268 866 arêtes de graphe orphelines et des écarts de schéma. La copie réconciliée est réservée
à la revue ; ne pas la déposer directement dans `state/local` avant la résolution des données
et la migration de schéma. Le Dashboard actif ne prouve donc pas que les anciennes tâches ont basculé.

Le passage v229 prépare une **copie de pilote** dans
`E:/DevCoreRuntime/qualification/pilot-v229` avec base, magasin d'identité privé
et racines distinctes de `state/local` et `state/data`. Le script
`Scripts/prepare_individual_pilot_copy.py` prépare la base depuis une copie
réconciliée sans modifier la source. Son rapport se trouve dans
`qualification/pilot-copy-20261010-v229b.json` ; la validation complémentaire
est dans `qualification/pilot-validation-20261010-v229.json`. Le préflight de la
release et un démarrage temporaire sur `127.0.0.1:20132` ont réussi ; deux
comptes de sonde ont lu seulement leur projet, puis ont été désactivés. Cette
copie ne doit pas être substituée aux racines actives avant le gel des écrivains,
la revue des projets provisoires, le pilote de charge et la preuve de retour arrière.

Le passage v230 a trouvé un défaut du paquet installé : les runs Windows y
cherchaient `DEV_CORE.Scheduler.windows_job`, absent de la wheel. Le moteur source
importe désormais `devcore_engine.infra.windows_job`. Une **nouvelle release candidate**
`E:/DevCoreRuntime/releases/devcore-py31316-20261011-l9-runfix` a été construite
et attestée séparément ; le service SCM utilise toujours la release du 10 octobre.
Le passage v235 a ensuite construit une copie de qualification sous
`E:/DevCoreRuntime/qualification/autostart-v235/runtime` avec le profil
`windows_startup=automatic` de schéma 2, des racines de recette et une attestation valide.
Cette copie n'est pas enregistrée dans SCM ; le test après redémarrage de Windows reste ouvert.
La sonde `qualification/pilot-v230/qualification.json` atteste cinq sessions HTTP
isolées et deux runs courts parallèles sur copie. Le rapport
`qualification/restore-v231/restore-qualification.json` atteste une restauration
indépendante des tâches, runs et identités avec révocation de tous les accès.
L'ancienne release ne peut servir de retour arrière complet pour les runs.

Une sonde supplémentaire sur `qualification/pilot-v232` a vérifié 20 sessions
simulées et 200 lectures (p95 observé 89,74 ms), puis deux runs. La mémoire
libre n'a été lue qu'avant et après. Le rapport `qualification/crash-v233`
documente l'arrêt brutal d'un worker isolé, la mort de son enfant et la reprise
du run en file. Ces résultats ne changent pas les racines ni le service actifs.
