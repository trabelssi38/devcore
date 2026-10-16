"""Assemble the two global-stack DDL migrations into one atomic SQL file."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


MIGRATIONS = Path(__file__).resolve().parents[1] / "devcore_engine" / "persistence" / "migrations"
SOURCES = ("20261016_durable_runs.sql", "20261016_team_schedules.sql")


def assemble() -> tuple[str, list[dict]]:
    chunks = []
    sources = []
    for name in SOURCES:
        raw = (MIGRATIONS / name).read_bytes()
        lines = raw.decode("utf-8").splitlines()
        boundaries = [index for index, line in enumerate(lines)
                      if line.strip() in {"BEGIN;", "COMMIT;"}]
        if len(boundaries) != 2 or lines[boundaries[0]].strip() != "BEGIN;" or lines[boundaries[1]].strip() != "COMMIT;":
            raise ValueError(f"Migration transaction boundaries invalid: {name}")
        if any(line.strip() and not line.lstrip().startswith("--") for line in lines[boundaries[1] + 1:]):
            raise ValueError(f"Unexpected SQL after commit: {name}")
        chunks.append("\n".join(lines[boundaries[0] + 1:boundaries[1]]).strip())
        sources.append({"name": name, "sha256": hashlib.sha256(raw).hexdigest()})
    sql = ("-- Atomic global-stack DDL. Apply only after a fresh full backup.\n"
           "BEGIN;\n" + "\n\n".join(chunks) + "\nCOMMIT;\n")
    return sql, sources


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.output.is_absolute() or not args.output.parent.is_dir():
        parser.error("Output needs an existing absolute directory")
    sql, sources = assemble()
    with args.output.open("x", encoding="utf-8", newline="\n") as target:
        target.write(sql)
    print(json.dumps({"status": "global_ddl_prepared", "path": str(args.output),
                      "bytes": args.output.stat().st_size,
                      "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
                      "sources": sources}, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
