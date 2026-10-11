"""Compare two explicitly selected Codex rollouts; writes only to stdout."""

import argparse
import hashlib
import json
from pathlib import Path

from Auto.token_report import codex_counter_delta


def read_observed_usage(path: Path) -> dict:
    before = path.stat()
    digest = hashlib.sha256()
    previous = None
    warnings = set()
    tokens = cache_hits = output_tokens = samples = 0
    session_id = None
    models = set()
    with path.open("rb") as stream:
        for number, line in enumerate(stream, 1):
            digest.update(line)
            try:
                row = json.loads(line)
            except (ValueError, UnicodeError) as exc:
                raise ValueError(f"invalid JSONL at line {number}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"invalid record at line {number}")
            payload = row.get("payload")
            if not isinstance(payload, dict):
                continue
            if row.get("type") == "session_meta":
                session_id = payload.get("id") or payload.get("session_id")
            elif row.get("type") == "turn_context" and payload.get("model"):
                models.add(payload["model"])
            elif row.get("type") == "event_msg" and payload.get("type") == "token_count" and payload.get("info") is not None:
                usage, previous, warning = codex_counter_delta(payload, previous)
                if warning:
                    warnings.add(warning)
                if usage:
                    tokens += usage["tokens"]
                    cache_hits += usage["cache_hits"]
                    output_tokens += usage["output_tokens"]
                    samples += 1
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        warnings.add("rollout_changed_during_read")
    if not session_id:
        warnings.add("missing_session_identity")
    if not samples:
        warnings.add("no_observed_usage")
    return {"session_id": session_id, "sha256": digest.hexdigest(), "models": sorted(models),
            "tokens": tokens, "cached_input_tokens": cache_hits, "output_tokens": output_tokens,
            "warnings": sorted(warnings), "samples": samples}


def compare(manifest_path: Path) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if manifest.get("schema_version") != 1:
        raise ValueError("schema_version must be 1")
    runs = manifest.get("runs", [])
    if len(runs) != 2 or {run.get("condition") for run in runs} != {"baseline", "context"}:
        raise ValueError("exactly one baseline and one context run are required")
    runs = {run["condition"]: run for run in runs}
    reasons = []
    for key in ("project_id", "task_id", "git_commit", "model", "reasoning_effort"):
        if not runs["baseline"].get(key) or runs["baseline"].get(key) != runs["context"].get(key):
            reasons.append(f"incomparable_{key}")
    measurements = {}
    for condition, run in runs.items():
        path = (manifest_path.parent / run["rollout"]).resolve()
        observed = read_observed_usage(path)
        measurements[condition] = observed
        reasons.extend(f"{condition}:{warning}" for warning in observed["warnings"])
        if observed["models"] != [run.get("model")]:
            reasons.append(f"{condition}:observed_model_mismatch")
        quality = run.get("quality_checks")
        if run.get("completed") is not True or not isinstance(quality, dict) or not quality or any(value is not True for value in quality.values()):
            reasons.append(f"{condition}:quality_not_accepted")
    if set(runs["baseline"].get("quality_checks", {})) != set(runs["context"].get("quality_checks", {})):
        reasons.append("different_quality_criteria")
    if measurements["baseline"]["session_id"] == measurements["context"]["session_id"]:
        reasons.append("same_conversation")
    if measurements["baseline"]["tokens"] <= 0:
        reasons.append("empty_baseline")
    report = {"schema_version": 1, "status": "inconclusive" if reasons else "comparable",
              "reasons": sorted(set(reasons)), "runs": measurements,
              "equivalence_and_quality": "declared_in_manifest",
              "scope": "two_selected_conversations; child agents excluded unless separately supplied"}
    if not reasons:
        baseline = measurements["baseline"]["tokens"]
        context = measurements["context"]["tokens"]
        report["tokens_saved"] = baseline - context
        report["tokens_saved_percent"] = round(100 * (baseline - context) / baseline, 2)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    try:
        report = compare(args.manifest.resolve())
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
