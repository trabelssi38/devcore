from dataclasses import asdict
from pathlib import Path

from devcore.ask_confirm import render_confirmation_text
from devcore.ask_parser import interpret_french_prompt
from devcore.bootstrap_cli import build_bootstrap_payload
from devcore.cli import build_prepare_payload


def build_ask_launch_payload(prompt_fr: str, cwd: Path) -> dict:
    interpretation = interpret_french_prompt(prompt_fr=prompt_fr, cwd=cwd)
    bootstrap_payload = build_bootstrap_payload(
        cwd=cwd,
        task_type=interpretation.task_type,
        prompt_text=prompt_fr,
    )
    prepare_payload = build_prepare_payload(
        project_id=interpretation.project_id or "default",
        task_type=interpretation.task_type,
        urgency="urgent"
        if "urgence" in prompt_fr.lower() or "urgent" in prompt_fr.lower()
        else "normal",
        volume="small",
        intent=interpretation.intent,
        context_summary=interpretation.context_summary,
        context_refs=[],
        constraints=["human confirmation required"],
        expected_output="patch + explanation + risks",
    )
    return {
        "interpretation": asdict(interpretation),
        "bootstrap": bootstrap_payload,
        "confirmation_text": render_confirmation_text(
            interpretation, bootstrap_payload
        ),
        "prepare": prepare_payload,
    }
