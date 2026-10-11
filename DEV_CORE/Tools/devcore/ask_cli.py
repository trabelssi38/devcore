from dataclasses import asdict, replace
from pathlib import Path

from devcore.ask_confirm import render_confirmation_text
from devcore.ask_parser import interpret_french_prompt
from devcore.bootstrap_cli import build_bootstrap_payload
from devcore.cli import build_prepare_payload


def build_ask_launch_payload(
    prompt_fr: str,
    cwd: Path,
    project_id: str | None = None,
    mission_id: str | None = None,
) -> dict:
    interpretation = interpret_french_prompt(prompt_fr=prompt_fr, cwd=cwd)
    if project_id is not None:
        interpretation = replace(interpretation, project_id=project_id)
    bootstrap_payload = build_bootstrap_payload(
        cwd=cwd,
        task_type=interpretation.task_type,
        prompt_text=prompt_fr,
    )
    return {
        "interpretation": asdict(interpretation),
        "bootstrap": bootstrap_payload,
        "confirmation_text": render_confirmation_text(
            interpretation, bootstrap_payload, mission_id=mission_id
        ),
        "mission_id": mission_id,
    }


def prepare_ask_launch_payload(interpretation: dict, mission_id: str | None = None) -> dict:
    prompt_fr = str(interpretation["raw_prompt_fr"])
    return build_prepare_payload(
        project_id=str(interpretation["project_id"] or "default"),
        task_type=str(interpretation["task_type"]),
        urgency="urgent"
        if "urgence" in prompt_fr.lower() or "urgent" in prompt_fr.lower()
        else "normal",
        volume="small",
        intent=str(interpretation["intent"]),
        context_summary=str(interpretation["context_summary"]),
        context_refs=[],
        constraints=["human confirmation required"],
        expected_output="patch + explanation + risks",
        mission_id=mission_id,
    )
