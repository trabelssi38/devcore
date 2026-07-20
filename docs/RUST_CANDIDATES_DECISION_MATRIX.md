# DEV_CORE v10 -- Matrice de Décision Candidates Rust (Python vs Rust)

Matrice d’évaluation empirique pour décider des réécritures ou extractions de composants Python vers des exécutables autonomes en Rust (`Sprint 12 / 13`).

---

## 1. Règle d'Évaluation d'Extraction Rust

Conformément à la feuille de route DEV_CORE v10 (Sprint 12 / 13) :
- **Aucun composant Rust n'est accepté sans preuve d'un goulot d'étranglement mesuré.**
- **Le gain de vitesse mesuré doit être >= 2.0x OU réduire l'empreinte mémoire RAM de manière significative (> 50%).**
- **Tout binaire Rust doit interagir via une frontière de processus JSON/JSONL standardisée.**

---

## 2. Résultats Empiriques des Benchmarks (Sprint 12)

Rapport de performance généré : `DEV_CORE_DATA/Logs/performance_profile_report.json`

| Composant Candidat | Rôle & Fonction | Métrique Python Empirique (p50) | Seuil Déclenchement Rust | Décision Sprint 12 | Justification & Architecture |
|---|---|---|---|---|---|
| `devcore-scan` | Scan récursif du système de fichiers et audits statiques | **27.35 ms** pour 13 fichiers | > 500 ms sur 10 000 fichiers | **REJETÉ (Keep Python)** | Le scanner Python prend 27 ms, très inférieur au budget de 100 ms. |
| `devcore-watch` | Invalidation du cache et événements post-commit | **~15 ms** | > 200 ms | **REJETÉ (Keep Python)** | Mode polling et hooks légers très rapides. |
| `devcore-toon` | Codec et compression de contexte TOON | **< 5 ms** | > 100 ms | **REJETÉ (Keep Python)** | Compresseur Python fluide et économique. |
| `devcore-log-analyzer` | Analyseur de logs et agrégation des métriques | **28.62 ms** | > 500 ms | **REJETÉ (Keep Python)** | Rotation des logs et métriques traitées en 28.6 ms. |
| `SQLite_Task_Query` | Recommandations & requêtes état | **2.28 ms** | > 20 ms | **REJETÉ (Keep Python/SQLite)** | SQLite WAL fournit des réponses sub-3ms. |

---

## 3. Analyse du Générateur Monolithique `gen_dashboard.py`

- **Temps de génération HTML monolithique** : **2359.76 ms** (~2.36s).
- **Raison** : Formatage synchrone de 228 tâches, 100+ événements et cartes dans un template HTML géant.
- **Solution d'Architecture** : Déjà résolue par le passage à **`dashboard_api.py`** (< 2 ms) et l'interface Web Next.js réactive. Aucune réécriture Rust requise pour la génération HTML.

---

## 4. Contrat de Frontière de Processus (Process Boundary JSON)

En cas d'extraction future d'un composant Rust (ex: `devcore-scan`), le binaire CLI devra obligatoirement respecter l'interface d'entrée/sortie suivante :

### Entrée CLI (stdin ou argument)
```json
{
  "action": "scan",
  "root_dir": "C:\\devcore\\DEV_CORE",
  "rules": ["transition:all", "prefers-reduced-motion"]
}
```

### Sortie CLI (stdout)
```json
{
  "status": "success",
  "duration_ms": 4.2,
  "findings_count": 0,
  "findings": []
}
```
