from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

from devcore.paths import get_paths


@lru_cache(maxsize=None)
def _load_schema(name: str) -> dict:
    schema_path = Path(get_paths().schema_root) / f"{name}.schema.json"
    return json.loads(schema_path.read_text(encoding="utf-8"))


def validate_contract(name: str, payload: dict) -> None:
    validator = Draft202012Validator(_load_schema(name))
    errors = sorted(validator.iter_errors(payload), key=lambda error: tuple(error.path))
    if errors:
        raise ValueError("; ".join(error.message for error in errors))
