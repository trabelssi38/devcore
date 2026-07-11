# DEV_CORE v6 â€” Bootstrap
# Syntaxe dأ©clarative + politiques v6
# Compatible : Claude Code آ· Codex Desktop آ· Antigravity آ· Qwen

## Core
@load 00_Global/AGENTS.md
@load 00_Global/TOKEN_RULES.md
@policy concise
@policy memory_first
@policy intelligent_routing
@policy skills_first
@policy mission_aware

## Skills â€” contexte coding / dev
@when task_type=coding
@priority 90
@load Skills/dev-methodology/SKILL.md

@when task_type=bugfix
@priority 90
@load Skills/dev-methodology/SKILL.md

@when task_type=architecture
@priority 90
@load Skills/dev-methodology/SKILL.md

@when task_type=review
@priority 85
@load Skills/dev-methodology/SKILL.md

## Skills â€” stack
@when project=android_tooling
@priority 80
@load Skills/android_release/SKILL.md

@when stack=python
@priority 70
@load Skills/python_api/SKILL.md

@when stack=web
@priority 70
@load Skills/web_ui/SKILL.md

@when stack=ui
@priority 70
@load Skills/ui-ux/SKILL.md

## Skills â€” mأ©moire & vault
@when task_type=vault
@priority 95
@load Skills/obsidian/SKILL.md

@when task_type=memory
@priority 95
@load Skills/qdrant/SKILL.md

## Skills â€” analyse
@when task_type=analysis
@priority 75
@load Skills/fabric-patterns/SKILL.md

@when task_type=incident
@priority 85
@load Skills/fabric-patterns/SKILL.md

## Daily
@when moment=daily
@priority 40
@load Daily Notes/latest.md
