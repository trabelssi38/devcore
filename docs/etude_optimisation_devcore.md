# Étude de Faisabilité : Optimisation de DEV_CORE et Remplacement des Dépendances Lourdes

Cette étude évalue la faisabilité technique, les avantages/inconvénients et l'effort nécessaire pour remplacer les dépendances externes lourdes de DEV_CORE (PostgreSQL, Qdrant, l'application Obsidian, et le serveur Next.js Node) par des alternatives locales et légères, afin de réduire drastiquement l'empreinte mémoire et CPU sans perte de fonctionnalité ou de performance.

---

## 1. Résumé Exécutif

Actuellement, DEV_CORE v10 nécessite l'exécution de **7 conteneurs Docker** (Postgres, Qdrant, Gemini Router, API, Scheduler, Dashboard API et le serveur Web Node), pour une limite de mémoire cumulée de **2,8 Go de RAM**. Sur une machine hôte de développement (en particulier sous Windows avec WSL2/Docker Desktop), l'empreinte réelle est encore plus élevée en raison de la virtualisation.

En migrant la base de données et les calculs vectoriels vers le processus local (SQLite + Recherche Vectorielle Locale), en affichant les notes Markdown directement dans le Cockpit web, et en compilant le frontend Next.js en HTML statique, il est possible de **supprimer complètement la dépendance à Docker** (si désiré) ou de réduire l'empreinte mémoire de **plus de 90 % (de 2,8 Go à environ 150-200 Mo)** tout en conservant 100 % des fonctionnalités actuelles de DEV_CORE.

---

## 2. Étude de Faisabilité par Module

### A. Le Module Obsidian (Notes de Mémoire)
* **Rôle Actuel** : Stocke les logs quotidiens, les décisions et les leçons apprises sous forme de fichiers Markdown dans `DEV_CORE_DATA/Obsidian/`. Il est accessible via le serveur MCP `obsidian-vault`.
* **Le Mythe** : DEV_CORE ne communique jamais avec l'application de bureau Obsidian. Il se contente de lire et d'écrire des fichiers `.md` dans un dossier structuré.
* **Stratégie de Remplacement** : Conserver la structure de fichiers Markdown sur le disque (légère, lisible par l'humain, versionnable par Git) mais **supprimer la dépendance visuelle à l'application externe Obsidian**.
* **Intégration Cockpit** : Ajouter un composant de rendu Markdown directement dans le **Cockpit de DEV_CORE (Dashboard Next.js)**. L'utilisateur peut ainsi consulter, rechercher et éditer ses notes de mémoire sémantique directement depuis le dashboard.
* **Verdict** : 🟢 **GAIN FACILE**. Zéro perte de fonctionnalité, meilleure expérience utilisateur unifiée.

### B. Base de Données PostgreSQL
* **Rôle Actuel** : Stocke les tables des tâches, des organisations, des workspaces, des sessions et des métriques de consommation.
* **Stratégie de Remplacement** : Migrer vers **SQLite**.
* **Faisabilité** : Très élevée. DEV_CORE utilise l'ORM SQLAlchemy, qui abstrait les moteurs SQL.
* **Modifications requises** :
  1. Modifier l'URL de connexion dans `config.py` : `sqlite:///DEV_CORE_DATA/devcore.db`.
  2. Dans `models.py`, remplacer le type spécifique PostgreSQL `JSONB` par le type générique SQLAlchemy `JSON` (SQLite gère nativement le JSON depuis la version 3.9).
  3. Configurer Alembic pour générer des migrations compatibles SQLite (activer `render_as_batch=True` pour contourner l'impossibilité de modifier des colonnes directement sur SQLite).
* **Verdict** : 🟢 **RECOMMANDÉ**. Économise ~512 Mo de RAM et simplifie le cycle de vie (la base de données devient un simple fichier local). Le mode mono-agent de DEV_CORE élimine tout problème de verrouillage de transactions concurrentes.

### C. Base de Données Vectorielle Qdrant
* **Rôle Actuel** : Stocke et recherche les plongements vectoriels (embeddings) des notes de décisions, leçons et patterns.
* **Stratégie de Remplacement** : Utiliser un **Moteur de Recherche Vectorielle Locale en Python** (type cos-similarity avec numpy stocké sous forme de BLOBs dans SQLite).
* **Faisabilité** : Élevée.
  * L'indexation de la mémoire d'un développeur dépasse rarement les 10 000 entrées. Sur une telle volumétrie, un calcul de similarité cosinus codé en Python pur (ou via numpy) s'exécute en **moins de 5 millisecondes**, éliminant le besoin d'un conteneur Qdrant complet et de requêtes réseau HTTP.
* **Verdict** : 🟢 **RECOMMANDÉ**. Économise 512 Mo de RAM et supprime un conteneur Docker.

### D. Le Conteneur Web Next.js (Port 30000)
* **Rôle Actuel** : Sert le frontend React du Cockpit.
* **Stratégie de Remplacement** : **Export HTML Statique + Rendu par FastAPI**.
* **Faisabilité** : Élevée.
  1. Configurer Next.js en mode export statique (`output: 'export'` dans `next.config.js`).
  2. Compiler l'application (`next build`) pour générer les fichiers statiques (dossier `out/`).
  3. Monter ce dossier dans le serveur API Python de DEV_CORE (FastAPI) via `StaticFiles` :
     ```python
     from fastapi.staticfiles import StaticFiles
     app.mount("/", StaticFiles(directory="Web/out", html=True), name="static")
     ```
* **Verdict** : 🟢 **TRÈS RECOMMANDÉ**. Supprime complètement le conteneur Node.js Web en arrière-plan, économisant 512 Mo de RAM.

---

## 3. Matrice Comparative des Architectures

| Métrique / Composant | Architecture Actuelle (v10) | Architecture Optimisée (Cible) | Gain de Ressources |
|---|---|---|---|
| **Base de Données** | Conteneur PostgreSQL (512 Mo) | SQLite (Intégré au processus Python, 0 Mo) | **100 % économisé (512 Mo)** |
| **Base Vectorielle** | Conteneur Qdrant (512 Mo) | Similarité Cosinus Locale (Python, 0 Mo) | **100 % économisé (512 Mo)** |
| **Frontend Web** | Conteneur Node.js (512 Mo) | Rendu Statique via FastAPI (0 Mo supplémentaire) | **100 % économisé (512 Mo)** |
| **Notes Workspace** | Application Obsidian externe | Affichage Markdown intégré au Cockpit | **Espace de travail épuré** |
| **Démon / Planificateur** | Scripts de boucle d'arrière-plan PS | Boucle d'événements unique Asyncio Python | **Réduction de l'usage CPU** |
| **Dépendance Docker** | Obligatoire (3 Go+ RAM requis) | **Optionnelle** (Exécution 100 % native possible) | **Pas de surcharge de virtualisation** |
| **Empreinte RAM Totale** | **2,8 Go de RAM** | **~150 - 200 Mo de RAM** (API + Routeur) | **Réduction de 92 % de la RAM** |

---

## 4. Plan de Migration Suggéré

1. **Phase 1 : Unification SQL (SQLite)** : Remplacer les types `JSONB` de `models.py` par `JSON` et valider les scripts d'import.
2. **Phase 2 : Moteur Vectoriel Interne** : Créer une classe Python de recherche de similarité vectorielle stockant ses vecteurs dans SQLite. Remplacer les appels HTTP Qdrant par des appels de fonctions locales.
3. **Phase 3 : Export Statique Cockpit** : Compiler le site Next.js en statique et le lier à FastAPI, puis désactiver les conteneurs superflus dans le `docker-compose.yml`.
