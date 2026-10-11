# L9 — Répétition de sauvegarde et rétention sur copie (v239)

La répétition a utilisé exclusivement `E:/DevCoreRuntime/qualification/restore-v231/restored`.
Le rapport mesuré est `E:/DevCoreRuntime/qualification/recovery-v239b/qualification.json`.
La commande reproductible est dans le journal v239. Les racines actives, Dropbox et
les index RepoWise réels ne sont pas des fixtures de cet essai.

## Mesures observées le 11 octobre 2026

| Mesure | Résultat |
|---|---:|
| Base tâches/graphe | 223 928 320 octets |
| Base runs | 32 768 octets |
| Archive d'identité privée | 90 112 octets |
| Total d'une sauvegarde | 224 051 200 octets, environ 214 Mio |
| Copies SQLite et archive d'identité | 11,095 s |
| Restauration des trois bases | 12,565 s |
| Opération complète avec contrôles | 42,689 s |

Les trois archives et restaurations passent `integrity_check=ok` et zéro violation
de clé étrangère. Les bases tâches/runs restaurées correspondent exactement aux
empreintes SHA-256 de leurs archives. La restauration d'identité invalide les
sessions, jetons et comptes ; la reconnexion et la récupération administrative
sont nécessaires. Les empreintes des trois sources sont restées inchangées.

## Politique proposée pour le pilote

- Conserver **7 sauvegardes quotidiennes et 4 hebdomadaires** des trois bases
  transactionnelles, dans un dossier NTFS privé hors des racines actives.
- À la taille mesurée, 11 archives demandent au moins **2 464 563 200 octets
  (environ 2,30 Gio)**, avant croissance, manifestes et espace de travail.
  Prévoir au minimum une archive supplémentaire et une restauration simultanée
  (environ 427 Mio de plus à cette taille), puis surveiller la croissance réelle.
- Créer chaque archive par l'API de sauvegarde SQLite et le mécanisme privé
  `backup_identity_store`, avec empreintes, intégrité et clés étrangères.
  N'effacer une ancienne archive qu'après validation de la nouvelle et de sa
  capacité de restauration. Les archives d'identité contiennent des secrets :
  conserver leurs ACL privées et ne jamais les publier avec la documentation.
- Répéter une restauration vers de **nouvelles racines isolées** au moins chaque
  semaine pendant le pilote. Après restauration d'identité, vérifier la
  révocation et réinitialiser les accès par la procédure administrateur.

Ces valeurs sont une **proposition de recette**, non une rétention activée.
Les 12,565 s ne sont pas un RTO : ils excluent l'arrêt des écrivains, le choix de
l'archive, le redémarrage des services, la reconnexion et la validation des
clients. Un RPO ne peut pas être garanti sans ordonnanceur de sauvegarde actif.
Le retour arrière complet d'une release et la reprise Windows restent ouverts.
