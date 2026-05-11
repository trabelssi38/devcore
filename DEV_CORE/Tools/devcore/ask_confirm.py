from devcore.ask_types import AskInterpretation


def render_confirmation_text(
    interpretation: AskInterpretation,
    bootstrap_payload: dict,
) -> str:
    loaded_files = "\n".join(
        f"- {item}" for item in bootstrap_payload.get("loaded_files", [])
    )
    trace = "\n".join(f"- {item}" for item in bootstrap_payload.get("trace", []))
    return "\n".join(
        [
            "Prompt:",
            f'"{interpretation.raw_prompt_fr}"',
            "",
            "Interpretation:",
            f"- project_id: {interpretation.project_id}",
            f"- task_type: {interpretation.task_type}",
            f"- intent: {interpretation.intent}",
            f"- context_summary: {interpretation.context_summary}",
            f"- confidence: {interpretation.confidence}",
            "",
            "Bootstrap:",
            loaded_files or "- none",
            "",
            "Trace:",
            trace or "- none",
            "",
            "Confirmer le lancement ? [Y/n]",
        ]
    )
