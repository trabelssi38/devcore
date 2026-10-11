"""Read a project card and validated decisions without database or network access."""

from __future__ import annotations

from datetime import date
import hashlib
import json
from pathlib import Path
import re


MAX_FILE_BYTES = 256 * 1024
STATUSES = {"effective", "proposed", "superseded"}


class ContextBudgetExceeded(ValueError):
    pass


def encode_context(result: dict) -> str:
    """The CLI and budget calculation use exactly the same wire representation."""
    return json.dumps(result, ensure_ascii=False, separators=(",", ":"))


def _measure(result: dict) -> int:
    result["measurement"]["used"] = 0
    for _ in range(8):
        measured = len((encode_context(result) + "\n").encode("utf-8"))
        if measured == result["measurement"]["used"]:
            return measured
        result["measurement"]["used"] = measured
    raise ValueError("context measurement did not stabilize")


def _read_inside(directory: Path, name: str) -> bytes:
    path = (directory / name).resolve()
    if not path.is_relative_to(directory) or not path.is_file():
        raise ValueError("context file is missing or outside the selected directory")
    with path.open("rb") as stream:
        raw = stream.read(MAX_FILE_BYTES + 1)
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError("context file exceeds the size limit")
    return raw


def _text(value, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"invalid {field}")
    return value


def _validate(manifest: dict, project: str) -> list[dict]:
    if type(manifest.get("schema_version")) is not int or manifest.get("schema_version") != 1 or manifest.get("project") != project:
        raise ValueError("context schema or explicit project mismatch")
    _text(manifest.get("card"), "card")
    digest = manifest.get("card_sha256")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("invalid card_sha256")
    decisions = manifest.get("decisions")
    if not isinstance(decisions, list) or len(decisions) > 128:
        raise ValueError("invalid decisions list")
    by_id = {}
    for item in decisions:
        if not isinstance(item, dict):
            raise ValueError("invalid decision")
        identity = _text(item.get("id"), "decision id")
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", identity) or identity in by_id:
            raise ValueError("invalid or duplicate decision id")
        by_id[identity] = item
        if item.get("status") not in STATUSES or type(item.get("required")) is not bool:
            raise ValueError("invalid decision status or required flag")
        if item["required"] and item["status"] != "effective":
            raise ValueError("only effective decisions may be required")
        for field in ("decision", "rationale", "validation"):
            _text(item.get(field), field)
        for field in ("sources", "tags", "replaces"):
            values = item.get(field)
            if not isinstance(values, list) or any(not isinstance(v, str) or not v for v in values):
                raise ValueError(f"invalid {field}")
        if not item["sources"]:
            raise ValueError("decision requires sources")
        if item.get("date") is not None:
            date.fromisoformat(_text(item["date"], "decision date"))
    replacements = {}
    for item in decisions:
        for old in item["replaces"]:
            if old not in by_id or by_id[old]["status"] != "superseded" or old in replacements:
                raise ValueError("invalid or ambiguous decision replacement")
            replacements[old] = item["id"]
    for identity, item in by_id.items():
        if item["status"] == "superseded" and identity not in replacements:
            raise ValueError("superseded decision requires a replacement")
        visited = set()
        node = identity
        while node in replacements:
            if node in visited:
                raise ValueError("cyclic decision replacement")
            visited.add(node)
            node = replacements[node]
        if item["status"] == "superseded" and by_id[node]["status"] != "effective":
            raise ValueError("replacement chain must end in an effective decision")
    return decisions


def load_project_context(directory: Path, project: str, *, budget_bytes: int = 12000,
                         query: str = "", today: date | None = None,
                         max_age_days: int = 7) -> dict:
    """Bound the complete JSON response, including diagnostics, in UTF-8 bytes.

    Required facts are never truncated. Bytes are not reported as model tokens.
    Source citations and review dates are declarations, not runtime validation.
    """
    if not isinstance(project, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", project) or ".." in project:
        raise ValueError("invalid explicit project")
    if type(budget_bytes) is not int or not 256 <= budget_bytes <= 65536:
        raise ValueError("budget_bytes must be between 256 and 65536")
    if not isinstance(query, str) or len(query) > 4096:
        raise ValueError("invalid query")
    if type(max_age_days) is not int or not 0 <= max_age_days <= 365:
        raise ValueError("invalid freshness window")
    directory = Path(directory).resolve()
    manifest_raw = _read_inside(directory, "context.json")
    manifest = json.loads(manifest_raw)
    if not isinstance(manifest, dict):
        raise ValueError("invalid manifest")
    decisions = _validate(manifest, project)
    reviewed = date.fromisoformat(_text(manifest.get("reviewed_at"), "reviewed_at"))
    age = ((today or date.today()) - reviewed).days
    card_raw = _read_inside(directory, manifest["card"])
    card = card_raw.decode("utf-8-sig")
    _text(card, "card content")
    digest = hashlib.sha256(card_raw).hexdigest()
    warnings = []
    if digest != manifest["card_sha256"]:
        warnings.append("card_changed_since_review")
    if age < 0:
        warnings.append("review_date_in_future")
    elif age > max_age_days:
        warnings.append("context_review_expired")
    required = [d for d in decisions if d["required"]]
    terms = set(re.findall(r"\w+", query.casefold()))
    optional = [d for d in decisions if not d["required"] and d["status"] != "superseded"]
    rank = lambda item: len(terms.intersection(re.findall(r"\w+", " ".join(item["tags"]).casefold())))
    relevant = sorted((d for d in optional if rank(d)), key=lambda d: (-rank(d), d["id"]))
    superseded = [d["id"] for d in decisions if d["status"] == "superseded"]
    result = {
        "project": project, "schema_version": 1,
        "measurement": {"unit": "utf8_bytes", "budget": budget_bytes, "used": 0,
                        "scope": "complete_json_line", "model_tokens_measured": False},
        "provenance": {"manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
                       "card_sha256": digest, "reviewed_at": reviewed.isoformat(),
                       "source_contents_verified": False},
        "warnings": warnings, "card": card, "decisions": required.copy(),
        "excluded_superseded": superseded,
        "omitted": [{"id": d["id"], "reason": "not_relevant"} for d in optional],
    }
    if _measure(result) > budget_bytes:
        raise ContextBudgetExceeded("required card and decisions exceed budget_bytes; no partial context returned")
    for item in relevant:
        result["decisions"].append(item)
        omission = next(o for o in result["omitted"] if o["id"] == item["id"])
        result["omitted"].remove(omission)
        if _measure(result) > budget_bytes:
            result["decisions"].pop()
            omission["reason"] = "budget"
            result["omitted"].append(omission)
    if _measure(result) > budget_bytes:
        raise ContextBudgetExceeded("context diagnostics exceed budget_bytes")
    return result
