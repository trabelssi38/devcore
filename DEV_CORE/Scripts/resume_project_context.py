"""Print a bounded local project context without changing any files."""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from devcore_engine.services.project_context import encode_context, load_project_context


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--budget-bytes", type=int, default=12000)
    parser.add_argument("--query", default="")
    args = parser.parse_args()
    try:
        result = load_project_context(args.directory, args.project,
                                      budget_bytes=args.budget_bytes, query=args.query)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    output = (encode_context(result) + "\n").encode("utf-8")
    sys.stdout.buffer.write(output)


if __name__ == "__main__":
    main()
