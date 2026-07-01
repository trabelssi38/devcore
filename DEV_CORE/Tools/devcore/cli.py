# cli.py — DEV_CORE v9.0
# Main entry point — préserve toute la logique existante + mission awareness

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from devcore.adapters import ClaudeAdapter, CodexAdapter, GeminiAdapter
from devcore.bootstrap_cli import build_bootstrap_payload
from devcore.router import recommend_engine
from devcore.session import create_session, write_router_decision
from devcore.telemetry import log_prepare_event


ADAPTERS = {
    "claude": ClaudeAdapter(),
    "codex": CodexAdapter(),
    "gemini": GeminiAdapter(),
}


def build_bootstrap_only_payload(
    cwd: str,
    task_type: str | None = None,
    prompt_text: str = "",
) -> dict:
    return build_bootstrap_payload(
        cwd=Path(cwd),
        task_type=task_type,
        prompt_text=prompt_text,
    )


def build_french_launch_payload(
    prompt_fr: str,
    cwd: str,
) -> dict:
    from devcore.ask_cli import build_ask_launch_payload
    return build_ask_launch_payload(
        prompt_fr=prompt_fr,
        cwd=Path(cwd),
    )


def build_prepare_payload(
    project_id: str,
    task_type: str,
    urgency: str,
    volume: str,
    intent: str,
    context_summary: str,
    context_refs: list[str],
    constraints: list[str],
    expected_output: str,
    mission_id: str | None = None,
) -> dict:
    handoff_id = f"hf_{project_id}_{task_type}"
    if mission_id:
        handoff_id = f"hf_{project_id}_{mission_id}"

    decision = recommend_engine(task_type=task_type, urgency=urgency, volume=volume)
    handoff = {
        "handoff_id": handoff_id,
        "project_id": project_id,
        "task_type": task_type,
        "target_engine": decision["engine"],
        "intent": intent,
        "context_refs": context_refs,
        "context_summary": context_summary,
        "constraints": constraints,
        "expected_output": expected_output,
        "prepared_at": datetime.now(timezone.utc).isoformat(),
    }
    if mission_id:
        handoff["mission_id"] = mission_id

    session_dir = create_session(handoff)
    write_router_decision(session_dir, decision)
    adapter_payload = ADAPTERS[decision["engine"]].prepare(session_dir, handoff)
    (session_dir / "adapter-payload.json").write_text(
        json.dumps(adapter_payload, indent=2), encoding="utf-8",
    )
    prepare_event = {
        "handoff_id": handoff_id,
        "project_id": project_id,
        "task_type": task_type,
        "engine": decision["engine"],
        "fallback": decision["fallback"],
        "confidence": decision["confidence"],
        "reason": decision["reason"],
        "recommended_skill": decision.get("recommended_skill"),
        "prompt_pattern": expected_output,
    }
    log_prepare_event(prepare_event)
    return {
        "handoff_id": handoff_id,
        "engine": decision["engine"],
        "session_dir": str(session_dir),
        "prompt_path": adapter_payload["prompt_path"],
        "recommended_skill": decision.get("recommended_skill"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--task-type", required=True)
    parser.add_argument("--urgency", default="normal")
    parser.add_argument("--volume", default="small")
    parser.add_argument("--intent", required=True)
    parser.add_argument("--context-summary", required=True)
    parser.add_argument("--context-ref", action="append", default=[])
    parser.add_argument("--constraint", action="append", default=[])
    parser.add_argument("--expected-output", required=True)
    parser.add_argument("--mission-id", default=None)
    args = parser.parse_args()

    payload = build_prepare_payload(
        project_id=args.project_id,
        task_type=args.task_type,
        urgency=args.urgency,
        volume=args.volume,
        intent=args.intent,
        context_summary=args.context_summary,
        context_refs=args.context_ref,
        constraints=args.constraint,
        expected_output=args.expected_output,
        mission_id=args.mission_id,
    )
    print(json.dumps(payload))


if __name__ == "__main__":
    main()
