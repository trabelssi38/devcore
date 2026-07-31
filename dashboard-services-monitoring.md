# Dashboard Services Monitoring & Repowise Code Health Radar

## Overview
Ce document décrit l'architecture et les mécanismes du système de monitoring des services et de santé du code (Repowise Code Health & Refactoring Radar) intégrés au Cockpit DEV_CORE v10.0.

---

## 🏗️ Architecture & Composants

### 1. Monitoring des Services Réseau & Infrastructure
Le cockpit surveille l'état d'activité des services clés :
* **Gemini Router (Primary)** — Port `20130` (IA Passerelle LLM)
* **Dashboard API Server** — Port `20129` (Administration Cockpit API)
* **Headroom Proxy** — Port `8787` (Optimisation & réduction de tokens)
* **DEV_CORE Scheduler / Hermes** — Fréquence d'exécution des tâches d'arrière-plan
* **Qdrant Vector DB** — Port `6333` (Base de données vectorielle)
* **Repowise Engine** — Port `7337` (Moteur d'analyse statique et RAG de code)

### 2. Repowise Code Health & Refactoring Radar Multi-Projets
* **Cartes Dynamiques** : Chaque projet indexé par UUID dans Repowise (`dashboard_recette_br`, `devcore`, `job_tracker`, etc.) génère une carte HTML `repowise-health-card` distincte.
* **Badges d'État** :
  * `🟢 EN DIRECT (Port 7337)` : Métriques réelles (Score Global, Maintenabilité, Performance, Répartition sains/warning/alerte, Cibles de refactoring) récupérées via l'API HTTP Repowise.
  * `⚡ MCP INDEXED` : Mode fallback lorsque l'API HTTP 7337 est incalculable ou inactive.
* **Filtrage JavaScript au Clic** : La fonction `updateRepowiseHealth(projectName)` masque les cartes des autres projets pour n'afficher que celle correspondant au projet sélectionné dans la liste du cockpit.

---

## ⚡ Optimisations & Résolution Réseau (Windows IPv6 / Proxys)

1. **Priorité IPv4 Directe (`127.0.0.1`)** :
   * Les vérifications de ports TCP (`check_port` dans Python et `Check-Port` dans PowerShell) et les requêtes HTTP utilisent directement `127.0.0.1` au lieu de `localhost`.
   * Sous Windows 10/11, cela élimine les latences et timeouts (0.5s par requête) causés par la résolution IPv6 `::1` prioritaire.

2. **Bypass des Proxys HTTP (`ProxyHandler({})`)** :
   * Les appels `urllib.request` vers `127.0.0.1:7337` utilisent un opener `_urllib_req.ProxyHandler({})` pour éviter toute interception par le proxy Headroom local (port `20130`/`8787`).

3. **Délégation PowerShell -> Python (`gen_dashboard.ps1`)** :
   * `gen_dashboard.ps1` délègue l'étape d'injection HTML finale à `gen_dashboard.py`, garantissant l'intégration uniforme des cartes Repowise Health lors des déclenchements automatiques (post-task hooks).

---

## 📋 Statut de Validation
- [x] Vérification réseau en temps réel pour tous les services (Gemini Router, Dashboard API, Headroom, Qdrant, Repowise).
- [x] Rendu multi-cartes et filtrage par projet au clic.
- [x] Tolérance aux pannes avec mode fallback réactif.
- [x] Synchronisation Git et automatisation des événements.
