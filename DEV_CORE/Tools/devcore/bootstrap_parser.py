from pathlib import Path

from devcore.bootstrap_types import BootstrapBlock, BootstrapDirective


def parse_bootstrap_markdown(path: Path) -> list[BootstrapBlock]:
    lines = path.read_text(encoding="utf-8").splitlines()
    blocks: list[BootstrapBlock] = []
    current_section = "Default"
    current_when: dict[str, str] = {}
    current_priority = 100
    current_directives: list[BootstrapDirective] = []

    def flush() -> None:
        nonlocal current_when, current_priority, current_directives
        if current_directives:
            blocks.append(
                BootstrapBlock(
                    section=current_section,
                    when=current_when,
                    priority=current_priority,
                    directives=current_directives,
                )
            )
        current_when = {}
        current_priority = 100
        current_directives = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("## "):
            flush()
            current_section = line[3:].strip()
            continue
        if line.startswith("@when "):
            if current_directives:
                flush()
            key, value = line[6:].split("=", 1)
            current_when = {key.strip(): value.strip()}
            continue
        if line.startswith("@priority "):
            current_priority = int(line[10:].strip())
            continue
        if line.startswith("@load "):
            current_directives.append(
                BootstrapDirective(kind="load", value=line[6:].strip())
            )
            continue
        if line.startswith("@policy "):
            current_directives.append(
                BootstrapDirective(kind="policy", value=line[8:].strip())
            )

    flush()
    return blocks
