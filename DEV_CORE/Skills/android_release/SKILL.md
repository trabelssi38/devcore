---
name: android_release
description: Utiliser pour toute tâche Android : release, build Gradle, APK/AAB, versionCode, signing, déploiement Play Store.
compatibility: Claude Code · Codex · Gemini · Qwen
---
# Skill — Android Release

## Règles fondamentales
- Toujours bumper versionCode avant un tag git
- Utiliser Gradle wrapper (./gradlew), jamais gradle direct
- Signing keystore : ne jamais commiter, utiliser secrets d'environnement
- Build release : `./gradlew assembleRelease` ou `bundleRelease` pour AAB
- Tests : `./gradlew test` + `./gradlew connectedAndroidTest`
- Perf : minifier avec R8, pas ProGuard (obsolète)

## Checklist release
- [ ] versionCode++ dans build.gradle
- [ ] versionName mis à jour
- [ ] Tests passants
- [ ] Build release signé
- [ ] Pas de logs debug en prod (BuildConfig.DEBUG)
- [ ] Permissions minimales dans AndroidManifest
