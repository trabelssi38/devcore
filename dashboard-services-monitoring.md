# Dashboard Services Monitoring

## Goal
Rendre dynamique l'affichage de l'état (status) et de la dernière exécution des services backend (Cron, Hermes, Hooks, Qdrant, Obsidian) dans le dashboard pour détecter facilement les défaillances.

## Tasks
- [x] Task 1: Mettre à jour `gen_dashboard.ps1` pour vérifier l'état des services réseau (Qdrant `6333`, Hermes `20128`, Ollama `11434`) via `Test-NetConnection` ou un ping HTTP rapide, et stocker l'état.
  - **Verify**: Le script identifie correctement si les ports locaux sont ouverts.
- [x] Task 2: Ajouter dans `gen_dashboard.ps1` la lecture de la dernière exécution des crons et hooks en vérifiant le fichier `LastWriteTime` de leurs fichiers de logs respectifs dans `DEV_CORE_DATA\Logs\scripts\`.
  - **Verify**: Le script extrait un horodatage (timestamp) récent pour chaque script d'automatisation.
- [x] Task 3: Modifier `Dashboard\template.html` pour remplacer les blocs de code HTML statiques des composants d'infrastructure par des balises dynamiques (ex: `{{HERMES_STATUS}}`, `{{HOOKS_STATUS}}`, `{{QDRANT_STATUS}}`, etc.) ou un bloc global `{{INFRA_STATUS}}`.
  - **Verify**: Le template est purgé des données en dur.
- [x] Task 4: Modifier `gen_dashboard.ps1` pour générer le HTML de ces composants avec des indicateurs visuels : vert (`status-ok`) si c'est récent/en ligne, rouge (`status-error`) si c'est hors ligne ou si le log date de plusieurs jours.
  - **Verify**: `index.html` affiche l'état réel et l'heure exacte.

## Done When
- [x] L'état réseau de Qdrant, Hermes et Ollama est vérifié en temps réel.
- [x] L'heure d'exécution des hooks et crons est affichée.
- [x] Une défaillance (port fermé, log trop ancien) est immédiatement visible visuellement (rouge).
