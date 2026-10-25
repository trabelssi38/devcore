# Préflight LAN après pilote multiutilisateur

Date : 2026-10-15. Contrôle en lecture seule sur le poste actif.

## Constat

- `DevCoreIndividual` et `postgresql-x64-17` sont en marche et démarrent
  automatiquement. `/project` et `/api/status` répondent HTTP 200 en local.
- DevCore écoute seulement sur `127.0.0.1:20129` ; les ports globaux du profil
  équipe ne sont pas activés.
- PostgreSQL 17 écoute sur `0.0.0.0:5432` et `[::]:5432`, et
  `postgresql.conf` contient `listen_addresses = '*'`. Le fichier
  `pg_hba.conf` ne contient que des règles locales actives, donc une connexion
  distante PostgreSQL n'est pas autorisée par ces règles. Cette restriction
  d'authentification ne supprime pas l'écoute TCP sur les interfaces.
- Le poste a une interface Ethernet privée `172.16.210.32/24`. Le pare-feu
  Windows est désactivé pour les profils privé et domaine ; il est actif pour
  le profil public. L'inventaire détaillé des règles a été refusé dans cette
  session non élevée.
- Le système est Windows 10 Professionnel, version `10.0.19045`. Son état de
  maintenance et de mises à jour a été relevé à titre informatif.
- Le service DevCore tourne sous `.\\Administrateur`, exception connue du
  pilote local. L'API utilise HTTP sur localhost ; aucun terminateur TLS LAN
  ni test depuis un second poste n'est qualifié.

## Action préparée

`DEV_CORE/Scripts/harden_postgresql_loopback_elevated.ps1` limite
`listen_addresses` à `localhost`, sauvegarde le fichier original, redémarre
PostgreSQL avec DevCore arrêté, puis vérifie les listeners, la disponibilité
PostgreSQL et les deux sondes HTTP DevCore. Une erreur déclenche une tentative
de retour arrière vers la configuration sauvegardée. Le script refuse une
configuration dont l'empreinte a changé depuis ce préflight.

La syntaxe PowerShell a été validée. Le lancement dans la session courante non
élevée a été refusé avant toute modification. L'empreinte active du fichier
reste `FFF874182DD5FB4A1C5D133F0D2657D732C0CF87EDAE2FB0F10653E1EFB4649C`.
Le port PostgreSQL écoute toujours sur toutes les interfaces au moment de ce
rapport.

## Exécution et contrôle indépendant

L'utilisateur a exécuté le script dans PowerShell 7 élevé. Résultat déclaré :
`postgresql_loopback_verified`, sauvegarde
`C:/Program Files/PostgreSQL/17/data/postgresql.conf.before-loopback-20261015-225223.bak`,
nouvelle empreinte `E367331F0CC83FD98E47701538F2FD2CFD30405DF073753E8EA368AD3A6AAAC7`,
listeners `::1` et `127.0.0.1`, sondes DevCore HTTP 200.

Le contrôle indépendant suivant confirme la même empreinte, PostgreSQL limité
à `::1:5432` et `127.0.0.1:5432`, DevCore limité à `127.0.0.1:20129`, les
deux services en marche et les deux sondes HTTP 200. La sous-gate d'écoute
PostgreSQL est **close**. Les constats de la section initiale décrivent l'état
avant cette correction.

## Maintenance du système : contrôle complémentaire

Le système installé est Windows 10 Pro 22H2, build `19045.5487`.
`Get-HotFix` ne remonte aucune installation postérieure au 12 février 2025 ;
ce relevé ne constitue pas un inventaire exhaustif de Windows Update.
L'interrogation locale de la licence ESU n'a pas abouti dans un délai utile ;
aucune inscription ESU n'est donc établie. Microsoft indique que le support
ordinaire de Windows 10 a pris fin le 14 octobre 2025 :
<https://support.microsoft.com/en-us/windows/deployment/updates-lifecycle/windows-10-support-has-ended-on-october-14-2025>.
Ce relevé historique décrit l'état du poste ; la décision ultérieure de
l'utilisateur retire la preuve ESU et la mise à niveau des critères de cette
migration.

Le choix antérieur d'une voie ESU a été remplacé par la décision utilisateur
du 15 octobre : cette inscription et ses mises à jour ne sont plus une
condition du gate LAN demandé.

Un outil interactif de réinitialisation des comptes pilote est aussi préparé :
`DEV_CORE/Scripts/reset_postgres_pilot_password.py --user majdi|mohd`. Il
effectue une sauvegarde PostgreSQL complète avant chaque changement, conserve
les adhésions et révoque les sessions de l'utilisateur modifié. Les deux
nouveaux secrets peuvent être saisis localement si un reset est demandé ; aucun
reset n'a été exécuté pendant ce préflight. Aucun changement de mot de passe
n'est exigé pour le gate LAN.

## Gate LAN

**Non prêt pour l'ouverture LAN.** Le durcissement de l'écoute PostgreSQL est
terminé. Avant une ouverture LAN de DevCore, qualifier TLS, un pare-feu
limité au réseau utile, les origines
autorisées et un test depuis un second poste. PostgreSQL et les ports internes
doivent rester inaccessibles aux clients directs.

Décision utilisateur du 15 octobre : ni Windows 10 avec ESU ni le changement
des mots de passe `majdi`/`mohd` ne constituent des exigences de migration.

## Candidate TLS LAN en préparation

Le lanceur source `launch_individual_candidate.py` accepte désormais une
adresse IPv4 privée exacte avec `--lan-bind`, `--tls-certfile` et
`--tls-keyfile`. Le préflight refuse un certificat sans SAN pour cette adresse,
un certificat expiré, une paire clé/certificat invalide et tout bind large ou
public. Il configure l'origine HTTPS exacte et conserve le profil individuel.
Le mode service géré accepte maintenant cette configuration TLS exacte. La
release v253 LAN a été publiée et attestée, sans remplacer la v252 active.
Le certificat TLS a été créé dans `state/local/Security/lan-tls`, avec clé
privée sous ACL NTFS ; son empreinte SHA-256 est
`a0c09147dd2943bce9204f5608f1a3d75644208ae7ba8825c7ac883d657be1a1`
et il expire le 14 novembre 2026. Le second poste ne lui fait pas encore
confiance. Le pare-feu privé est toujours désactivé.

La release v253 a passé `verify_engine_release` (manifeste contrôles
`cefcf0a3131dde9a3afad78c6ef87af914043ec485857f55201e69fde51bd62e`).
Sur une interface virtuelle et des racines temporaires, le cycle HTTPS géré
a réussi : page 200, anonyme 401, origine hostile 403, connexion 200 avec
cookie `Secure`, tâches 200, déconnexion 200 puis session révoquée 401 et
arrêt coopératif. Le listener de recette est arrêté ; le service actif reste
v252 sur `127.0.0.1:20129`.

`configure_devcore_lan_firewall_elevated.ps1` est préparé pour l'adresse
`172.16.210.32` et le sous-réseau `172.16.210.0/24`. Sans `-Apply`, il contrôle
le profil réseau et affiche le changement prévu ; ce préflight a réussi. Avec
`-Apply` dans PowerShell élevé, il crée une règle entrante limitée à cette
adresse, ce sous-réseau, au port 20129 et au profil privé, active ce profil et
revient à l'état initial si la vérification échoue. L'application réelle n'a
pas été effectuée.

Le script `cutover_service_v253_lan_elevated.ps1` est préparé avec préflight,
application de la règle, bascule SCM, sondes HTTPS et tentative de retour
arrière du service et du pare-feu. Sa syntaxe passe ; la session non élevée le
refuse avant toute mutation. Il n'a pas été exécuté.

Restent : installer explicitement la confiance envers le certificat public
sur le second poste, exécuter la bascule élevée, qualifier les sessions HTTPS
depuis ce poste et vérifier que PostgreSQL et les ports internes lui sont
inaccessibles. Une reprise après redémarrage LAN reste aussi à consigner.

Le contrôle second poste est prêt dans
`DEV_CORE/Scripts/verify_v253_second_host.py`. Il dépend seulement de Python et
de la copie du **certificat public** `cert.pem` (jamais `key.pem`). Il valide
le certificat, le formulaire des deux comptes avec saisie masquée, le refus
inter-projets, la déconnexion et l'inaccessibilité de 5432, 7337, 8787,
8789, 20130 et 20131. Ce contrôle utilise le certificat public fourni comme
ancre de confiance ; le navigateur du second poste nécessite sa propre
installation de confiance avant l'essai interactif. Aucune vérification depuis
ce second poste n'a encore été exécutée.

## Séquence opérationnelle restante

> **Historique du préflight v253.** Cette séquence de bascule et son retour
> arrière décrivent l'état avant la mise en service v254. Ne pas relancer la
> bascule v253 sur le service v254 actif. Les résultats du 16 octobre en fin de
> document font foi pour le pilote LAN et sa reprise après redémarrage.

1. Copier uniquement `cert.pem` et `verify_v253_second_host.py` sur le second
   poste. Ne jamais y copier `key.pem`. Faire approuver le certificat par le
   navigateur de ce poste pour l'essai interactif.
2. Sur le poste serveur, lancer dans **PowerShell 7 élevé** :
   `& 'E:/src_python/devcore/DEV_CORE/Scripts/cutover_service_v253_lan_elevated.ps1'`.
   Le script applique d'abord le pare-feu limité, puis bascule et sonde v253.
3. Sur le second poste, lancer avec Python 3 :
   `py -3 verify_v253_second_host.py --certificate cert.pem` depuis le
   répertoire où les deux fichiers publics ont été copiés. Saisir localement
   les deux mots de passe demandés. Le script ne les affiche pas.
4. Tester ensuite `https://172.16.210.32:20129/project` dans un navigateur du
   second poste et consigner la reprise après redémarrage du serveur.

En cas d'échec après une bascule locale réussie, lancer sur le serveur dans
PowerShell 7 élevé
`& 'E:/src_python/devcore/DEV_CORE/Scripts/rollback_service_v253_lan_elevated.ps1'`.
Ce retour arrière ferme d'abord la règle DevCore, restaure v252 localhost et
laisse le pare-feu privé activé.

## Mise à jour après la première tentative (2026-10-16)

La première exécution élevée a échoué pendant la configuration du pare-feu,
avant la bascule SCM. L'erreur de retour arrière était une conversion invalide
de `[bool] False` vers `NetSecurity.GpoBoolean` ; les scripts sont corrigés pour
transmettre la valeur native. La cause initiale de l'échec du pare-feu
était masquée. Une prochaine tentative l'affichera avec les valeurs observées
si elle persiste.

Contrôle après l'échec : service v252 `Running`, HTTP localhost 200, écoute
DevCore uniquement sur `127.0.0.1:20129`, PostgreSQL uniquement sur loopback,
aucune règle DevCore. Le pare-feu Private est activé. Les indications plus haut
qui le disent désactivé et la bascule jamais exécutée décrivent l'état avant
la tentative. Le prochain geste est de relancer le script de bascule corrigé
dans PowerShell 7 élevé, puis d'examiner sa sortie avant l'essai du second poste.

La deuxième tentative a précisé l'échec : NetSecurity restitue la portée
`172.16.210.0/24` sous la forme équivalente `172.16.210.0/255.255.255.0`.
La vérification accepte maintenant ces deux formes du même réseau. Le retour
arrière a retiré la règle et restauré le profil Private ; v252 reste actif.

## État après bascule v253 et échec du premier essai distant (2026-10-16)

Le service actif utilise maintenant le binaire v253 et écoute sur
`172.16.210.32:20129`. Les sondes HTTPS faites sur le serveur avec le
certificat public répondent 200 pour `/project` et `/api/status`, 401 pour la
session anonyme. `netsh` confirme la règle entrante Private/TCP/20129 limitée
à l'adresse locale `172.16.210.32` et aux clients `172.16.210.0/24`.
`ActiveStore` accepte les règles locales et bloque par défaut les autres
entrées. PostgreSQL écoute toujours uniquement sur loopback.

Le vérificateur lancé sur le second poste a expiré avant toute réponse au
premier `GET /project`. Il faut relever sur ce poste l'adresse IPv4 réellement
utilisée et `Test-NetConnection 172.16.210.32 -Port 20129 -InformationLevel
Detailed` pour distinguer une source hors portée, un problème de routage ou
un filtrage sur le chemin. Le contrôle second poste n'est pas encore validé.

Le second poste a ensuite montré une adresse source `10.40.100.2/32` sur
`Ethernet 3`, hors de la portée de la règle initiale. Une règle distincte et
réversible limitée à cet hôte exact est préparée dans
`allow_v253_second_host_elevated.ps1`. L'exécuter avec `-Apply` en PowerShell 7
élevé sur le serveur, puis répéter `Test-NetConnection` sur le second poste.
La règle n'est pas encore appliquée ; si TCP échoue toujours, rechercher le
blocage sur le chemin réseau et sa route de retour avant d'élargir l'accès.

## Pilote LAN vérifié depuis le second poste (2026-10-16)

Après création de la règle limitée à `10.40.100.2/32`, le vérificateur du
second poste a rendu `v253_second_host_verified`. Il a vérifié TLS, les deux
sessions, les refus interprojets, les déconnexions et l'inaccessibilité des
six ports internes. Le serveur confirme v253 `Running` et `Auto`, les deux
règles Private/TCP/20129 bornées à l'adresse locale `172.16.210.32`, ainsi que
PostgreSQL sur loopback seulement. Le gate LAN du pilote est clos. La reprise
après redémarrage et l'essai dans un navigateur sur le second poste ne sont pas
encore documentés comme réussis.

Le contrôle de reprise v253 est prêt dans
`verify_v253_after_windows_restart.ps1`. Une référence de boot du serveur a été
enregistrée le 16 octobre ; le script refuse un succès sur ce même boot.
Après un redémarrage Windows planifié, le lancer en PowerShell 7 élevé sur le
serveur, puis relancer `verify_v253_second_host.py` sur le second poste. Le
redémarrage n'a pas encore été fait dans cette séquence.

Le redémarrage suivant a finalement échoué pour le service v253 : trois
échecs de démarrage ont laissé `DevCoreIndividual` arrêté. Le journal
Application identifie deux délais d'attestation de 30 s, puis un délai de
disponibilité HTTP de 30 s. L'utilisateur a rétabli v253 manuellement, sans
qualifier sa reprise automatique. Une release v254 attestée, avec deux bornes
portées à 120 s, a passé une recette HTTPS isolée. Elle n'est pas encore
active. Le prochain passage est la bascule élevée vers v254, puis une nouvelle
référence de boot et un autre contrôle après redémarrage.

La bascule élevée v254 a ensuite réussi : service `Running/Auto` sur v254,
HTTPS local 200/200/401, mêmes règles de pare-feu. La référence de boot v254
est enregistrée. Le second poste a répété son vérificateur après la bascule
v254 : TLS vérifié, anonyme 401, deux utilisateurs avec accès `devcore` 200,
refus interprojets 403, déconnexions 200, révocations 401 et six ports internes
inaccessibles. Un nouveau redémarrage du serveur doit encore prouver la reprise
automatique avec `verify_v254_after_windows_restart.ps1` lancé avant toute
relance manuelle. Répéter ensuite le contrôle depuis le second poste.

Le redémarrage suivant a eu lieu le 16 octobre à `02:21:47.5000000Z`.
`verify_v254_after_windows_restart.ps1` a rendu
`v254_post_restart_local_verified` : services `Running/Auto`, PostgreSQL sur
loopback, listener LAN attendu, pare-feu borné et HTTPS 200/200/401. Le SCM
confirme indépendamment le binaire v254 en cours d'exécution. Le contrôle du
second poste **après ce redémarrage** reste attendu.

Le contrôle du second poste a ensuite réussi sur ce nouveau boot :
`v253_second_host_verified`, TLS vérifié, deux connexions et lectures `devcore`
200, refus interprojets 403, déconnexions 200, sessions révoquées 401 et ports
internes 5432, 7337, 8787, 8789, 20130, 20131 inaccessibles. La reprise LAN
v254 est qualifiée pour ce poste. L'activation de la pile globale reste séparée.
