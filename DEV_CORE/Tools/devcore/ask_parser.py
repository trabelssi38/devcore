from pathlib import Path

from devcore.ask_types import AskInterpretation


TASK_KEYWORDS = [
    ("bugfix", ("corrige", "bug", "erreur", "crash")),
    ("review", ("review", "revue", "audit")),
    ("architecture", ("architecture", "archi", "design")),
    ("migration", ("migration", "convertir", "bulk")),
    ("automation", ("automatiser", "script", "batch")),
    ("refactor", ("refactor", "nettoyer", "simplifier")),
]


def _detect_project_id(cwd: Path) -> str | None:
    return cwd.name if cwd else None


def _detect_task_type(prompt_lower: str) -> tuple[str, float]:
    for task_type, keywords in TASK_KEYWORDS:
        if any(keyword in prompt_lower for keyword in keywords):
            return task_type, 0.85
    return "review", 0.45


def _build_intent(prompt_fr: str, task_type: str) -> str:
    lowered = prompt_fr.strip().rstrip(".")
    if task_type == "bugfix":
        if "parser android" in lowered.lower():
            return "Corriger le bug du parser Android"
        return "Corriger le probleme signale"
    if task_type == "review":
        if "review" in lowered.lower() or "revue" in lowered.lower():
            return "Faire une review ciblee"
        return "Analyser la demande"
    return lowered[:1].upper() + lowered[1:]


def _build_context_summary(prompt_lower: str) -> str:
    parts: list[str] = []
    if "urgent" in prompt_lower or "urgence" in prompt_lower:
        parts.append("demande urgente")
    if "patch minimal" in prompt_lower:
        parts.append("contrainte de patch minimal")
    if "parser" in prompt_lower:
        parts.append("travail autour du parser")
    if not parts:
        parts.append("demande a confirmer")
    return ", ".join(parts)


def interpret_french_prompt(prompt_fr: str, cwd: Path) -> AskInterpretation:
    prompt_lower = prompt_fr.lower()
    project_id = _detect_project_id(cwd)
    task_type, confidence = _detect_task_type(prompt_lower)
    if project_id:
        confidence += 0.05
    confidence = min(confidence, 0.95)

    return AskInterpretation(
        raw_prompt_fr=prompt_fr,
        project_id=project_id,
        task_type=task_type,
        intent=_build_intent(prompt_fr, task_type),
        context_summary=_build_context_summary(prompt_lower),
        confidence=round(confidence, 2),
        needs_confirmation=True,
    )
