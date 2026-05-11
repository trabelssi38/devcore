import json

from devcore.contracts import validate_contract
from devcore.paths import get_paths
from devcore.telemetry import log_outcome_event


def create_session(handoff: dict):
    validate_contract("handoff", handoff)
    paths = get_paths()
    session_dir = paths.session_root / handoff["handoff_id"]
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "request.json").write_text(
        json.dumps(handoff, indent=2),
        encoding="utf-8",
    )
    return session_dir


def write_router_decision(session_dir, decision: dict) -> None:
    (session_dir / "router-decision.json").write_text(
        json.dumps(decision, indent=2),
        encoding="utf-8",
    )


def write_receipt(session_dir, receipt: dict) -> None:
    validate_contract("receipt", receipt)
    (session_dir / "receipt.json").write_text(
        json.dumps(receipt, indent=2),
        encoding="utf-8",
    )


def write_outcome(session_dir, outcome: dict) -> None:
    (session_dir / "outcome.json").write_text(
        json.dumps(outcome, indent=2),
        encoding="utf-8",
    )
    log_outcome_event(outcome)
