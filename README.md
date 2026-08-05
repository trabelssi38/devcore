# DEV_CORE v10 - README

**SQLite Unifié & Engine Python Natif** — Plateforme d'orchestration IA pour le développement logiciel

Version : 10.2.0
Mode : Single Client (sans Docker)

---

## 🚀 Lancement & Architecture

La plateforme s'exécute entièrement de manière native sur l'hôte à l'aide d'un moteur Python unifié (`devcore_engine`) et d'une base de données unique SQLite WAL (`devcore.db`). **Aucun conteneur Docker n'est requis.**

### Prérequis
- **Python 3.13+**
- Une clé API Google Gemini et/ou Anthropic (définie dans le fichier `C:\devcore\DEV_CORE_DATA\Security\gemini_api_key.txt` ou via l'interface du Cockpit)

### Étape 1 : Configurer la CLI locale (Hôte Windows)
Pour utiliser le raccourci `dc` directement depuis votre console hôte Windows PowerShell :
```powershell
cd C:\devcore\DEV_CORE\Scripts
.\setup.ps1
```
*Note : Cela installe l'alias permanent `dc` pointant vers `dc.ps1`.*

### Étape 2 : Lancer la plateforme
Pour démarrer tous les services natifs en arrière-plan :
```powershell
python -m devcore_engine launch
# ou simplement :
dc launch
```
Cette commande :
- Valide ou migre la base de données unifiée `DEV_CORE_DATA/devcore.db`.
- Lance automatiquement les services en processus détachés silencieux :
  - **Dashboard API** sur le port `20129`.
  - **Gemini Router** sur le port `20130`.

### Étape 3 : Valider l'installation
```powershell
# Exécuter les diagnostics de santé et de conformité
dc check
```

---

## 📋 Workflow Tasks

```powershell
# Créer une tâche
dc new task "Implémenter API REST" -reasoning

# Charger la tâche active
dc next task

# Travailler...
git commit -m "feat: add REST endpoints [T-01]"

# Valider la tâche
dc task done

# Voir le statut
dc task status
```

---

## 🎯 Modes Cognitifs & Gemini Router

La plateforme utilise un routeur intelligent (**Gemini Router** sur le port `20130`) qui intercepte les requêtes LLM locales, analyse l'intention cognitive et redirige l'exécution vers le modèle optimal selon le mode requis :

| Mode | Usage | Budget Contexte | Modèle Google Gemini Cible |
|------|-------|-----------------|-----------------------------|
| **reasoning** | Architecture, spécifications, décisions critiques | 32k tokens | Gemini 2.5 Pro |
| **coding** | Implémentation de code, cycle TDD, génération de patches | 8k tokens | Gemini 2.5 Pro |
| **bulk** | Génération de masse, documentation, écriture de tests unitaires | 16k tokens | Gemini 2.5 Flash |

Le routeur gère automatiquement le rate-limiting (retries avec backoff exponentiel sur erreur 429).

---

## 📁 Structure du Projet

```text
C:\devcore\
├── DEV_CORE\                   # Code source de la plateforme (Python Engine)
│   ├── devcore_engine\         # Package Python unifié (db, services, lifecycle, hooks)
│   ├── API\                    # FastAPI API
│   ├── Bus\                    # Bus d'événements interne
│   ├── Config\                 # Fichiers de configuration (AGENTS.md, CLAUDE.md, BOOT.md)
│   ├── Dashboard\              # Rendu du Cockpit (template.html & template_terminal.html)
│   ├── Scripts\                # Scripts orchestrateurs
│   └── tests\                  # Suite de tests unitaires (pytest)
├── DEV_CORE_DATA\              # Répertoire de données persistant
│   ├── devcore.db              # Base de données unique SQLite WAL & sqlite-vec (768d)
│   ├── Logs\                   # Journaux d'exécution
│   └── Obsidian\               # Vault Obsidian des notes de l'agent
└── README.md                   # Ce fichier
```

## 🔗 Ports & Services

Voici la cartographie des ports réseau utilisés par les différents services de la plateforme DevCore :

| Port | Service | Description | Statut |
|------|---------|-------------|--------|
| **7337** | Repowise API | Indexation intelligente, graphe de connaissances et dead-code | ✅ Actif |
| **8787** | Headroom Proxy | Proxy local pour la journalisation et le contrôle des coûts | ✅ Actif |
| **8788** | Anthropic Adapter | Adaptateur de protocole Anthropic -> Headroom -> OpenAI | ✅ Actif |
| **20129** | Dashboard/Cockpit API | API et serveur web du Cockpit (FastAPI) | ✅ Actif |
| **20130** | Gemini Router | Proxy intelligent d'inférence avec rate-limiting et modes cognitifs | ✅ Actif |
| **20131** | API Principale | API backend de DevCore (FastAPI) | ✅ Actif |
| **30000** | Web Frontend | Interface web Next.js / React (accessible via Docker) | ✅ Actif |

---

## 🔧 Commandes principales

### Tâches
- `dc next task` — Charge la prochaine tâche.
- `dc task done` — Valide + sync la mémoire.
- `dc task status` — Affiche le statut.
- `dc new task [titre] -[mode]` — Crée une tâche.

### Cycle & Plateforme
- `dc launch` — Démarrage de la journée et des démons.
- `dc check` — Diagnostic complet via le moteur de diag unifié.
- `dc check --gate` — Diagnostic release gate avec code de sortie.
- **Tests Unitaires (Cross-platform)** :
  - Sur Windows/Linux : `python -m unittest discover -s devcore_engine/tests`
  - Sur Ubuntu : `python3 -m unittest discover -s devcore_engine/tests`


---

## 📊 Cockpit Dashboard

Ouvrir dans un navigateur :
- **Mode Cockpit** (Design graphique moderne) : `http://127.0.0.1:20129/`
- **Mode Terminal** (Scanline vert/cyan) : `http://127.0.0.1:20129/index_terminal.html`

### Fonctionnalités Clés :
- **SQLite Vector DB** : Statut de la base virtuelle `sqlite-vec` surveillé en direct.
- **Supervision Headroom & Télémétrie Unifiée** : Suivi persistant des sessions et tokens. Intègre à la fois l'activité automatisée de DevCore et le chat interactif direct de l'IDE Antigravity (via le client virtuel `headroom-proxy` et l'analyse de transcripts).
- **Filtrage par Projet** : Sélection par projet avec ré-indexation dynamique du graphique.
- **Configuration Unifiée** : Synchronisation des clés d'API et clients actifs.
- **Optimisation SQLite & Silence Logs** : Avertissements d'importation de `sqlite-vec` réduits au silence via des variables d'environnement ciblées (`SQLITE_VEC_NO_WARN=1`) pour des diagnostics et logs 100% propres.
- **Détails & Actions Intuitives** : Affichage exclusif de la check-list des étapes de tâches et des descriptions au sein du pop-up interactif du bouton *Détails*, préservant la compacité et la lisibilité du tableau de bord.

---
