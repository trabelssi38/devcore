"""Start the PostgreSQL Gateway with the managed service lifecycle."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "API"))
from devcore_api.app import app
from service_runtime import run_managed


if __name__ == "__main__":
    run_managed(app, host="127.0.0.1", port=20131,
                service="gateway", proxy_headers=False)
