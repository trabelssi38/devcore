from pathlib import Path

from devcore.bootstrap_types import BootstrapContext


def detect_bootstrap_context(
    cwd: Path,
    task_type: str | None = None,
    prompt_text: str = "",
) -> BootstrapContext:
    project = cwd.name if cwd else None

    stack: list[str] = []
    lowered = project.lower() if project else ""
    if "android" in lowered:
        stack.append("android")
    if "python" in lowered or "api" in lowered:
        stack.append("python")
    if "web" in lowered or "ui" in lowered:
        stack.append("web")

    moment = None
    prompt_lower = prompt_text.lower()
    if any(term in prompt_lower for term in ["daily", "priorities", "blockers", "today"]):
        moment = "daily"

    return BootstrapContext(
        project=project,
        stack=stack,
        moment=moment,
        task_type=task_type,
    )
