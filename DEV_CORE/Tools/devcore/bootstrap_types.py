from dataclasses import dataclass, field


@dataclass(frozen=True)
class BootstrapDirective:
    kind: str
    value: str


@dataclass(frozen=True)
class BootstrapBlock:
    section: str
    when: dict[str, str]
    priority: int
    directives: list[BootstrapDirective] = field(default_factory=list)


@dataclass(frozen=True)
class BootstrapContext:
    project: str | None
    stack: list[str]
    moment: str | None
    task_type: str | None


@dataclass(frozen=True)
class BootstrapResult:
    loaded_files: list[str]
    policies: list[str]
    trace: list[str]
