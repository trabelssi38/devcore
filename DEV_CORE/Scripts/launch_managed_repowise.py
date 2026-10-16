"""Run RepoWise with a PID/token-qualified cooperative stop on Windows."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import threading


def main() -> None:
    if len(sys.argv) < 4 or sys.argv[1] != "--stop-file":
        raise SystemExit("Usage: launch_managed_repowise.py --stop-file PATH serve ...")
    stop_file = Path(sys.argv[2])
    token = os.environ.get("DEVCORE_REPOWISE_STOP_TOKEN", "")
    if not stop_file.is_absolute() or len(token) != 32:
        raise SystemExit("Qualified RepoWise stop file and token required")
    sys.argv = ["repowise", *sys.argv[3:]]

    import uvicorn
    from repowise.cli.main import cli

    original_run = uvicorn.Server.run

    def controlled_run(server, *args, **kwargs):
        finished = threading.Event()

        def watch_stop():
            while not finished.wait(.2):
                try:
                    request = json.loads(stop_file.read_text(encoding="utf-8"))
                    if request.get("pid") == os.getpid() and request.get("token") == token:
                        server.should_exit = True
                        return
                except (OSError, ValueError, AttributeError):
                    pass

        watcher = threading.Thread(target=watch_stop, daemon=True)
        watcher.start()
        try:
            return original_run(server, *args, **kwargs)
        finally:
            finished.set()
            watcher.join(timeout=1)
            try:
                request = json.loads(stop_file.read_text(encoding="utf-8"))
                if request.get("pid") == os.getpid() and request.get("token") == token:
                    stop_file.unlink()
            except (OSError, ValueError, AttributeError):
                pass

    uvicorn.Server.run = controlled_run
    cli()


if __name__ == "__main__":
    main()
