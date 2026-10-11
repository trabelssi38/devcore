"""Source entry point for the packaged individual API CLI."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from devcore_engine.clients.individual_cli import main


if __name__ == "__main__":
    raise SystemExit(main())
