from devcore.bootstrap_types import BootstrapBlock, BootstrapContext, BootstrapResult


def _matches(block: BootstrapBlock, context: BootstrapContext) -> bool:
    if not block.when:
        return True
    for key, value in block.when.items():
        if key == "project" and context.project != value:
            return False
        if key == "moment" and context.moment != value:
            return False
        if key == "task_type" and context.task_type != value:
            return False
        if key == "stack" and value not in context.stack:
            return False
    return True


def resolve_bootstrap(
    blocks: list[BootstrapBlock], context: BootstrapContext
) -> BootstrapResult:
    ordered = sorted(blocks, key=lambda block: block.priority, reverse=True)
    loaded_files: list[str] = []
    policies: list[str] = []
    trace: list[str] = []

    for block in ordered:
        if not _matches(block, context):
            trace.append(f"skipped {block.section}")
            continue
        if block.when:
            for key, value in block.when.items():
                trace.append(f"{key} {value} matched")
        else:
            trace.append("core block loaded")
        for directive in block.directives:
            if directive.kind == "load" and directive.value not in loaded_files:
                loaded_files.append(directive.value)
            if directive.kind == "policy" and directive.value not in policies:
                policies.append(directive.value)

    return BootstrapResult(
        loaded_files=loaded_files,
        policies=policies,
        trace=trace,
    )
