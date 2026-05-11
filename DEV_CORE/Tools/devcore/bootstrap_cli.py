from pathlib import Path

from devcore.bootstrap_context import detect_bootstrap_context
from devcore.bootstrap_parser import parse_bootstrap_markdown
from devcore.bootstrap_resolver import resolve_bootstrap
from devcore.paths import get_paths


def build_bootstrap_payload(
    cwd: Path,
    task_type: str | None = None,
    prompt_text: str = "",
) -> dict:
    boot_path = get_paths().platform_root / "Config" / "BOOT.md"
    blocks = parse_bootstrap_markdown(boot_path)
    context = detect_bootstrap_context(
        cwd=cwd,
        task_type=task_type,
        prompt_text=prompt_text,
    )
    result = resolve_bootstrap(blocks, context)
    return {
        "loaded_files": result.loaded_files,
        "policies": result.policies,
        "trace": result.trace,
        "context": {
            "project": context.project,
            "stack": context.stack,
            "moment": context.moment,
            "task_type": context.task_type,
        },
    }
