from dataclasses import dataclass


@dataclass(frozen=True)
class AskInterpretation:
    raw_prompt_fr: str
    project_id: str | None
    task_type: str
    intent: str
    context_summary: str
    confidence: float
    needs_confirmation: bool
