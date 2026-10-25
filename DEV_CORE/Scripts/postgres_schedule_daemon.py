"""Run the PostgreSQL schedule dispatcher without loading legacy JSON/SQLite jobs."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from devcore_engine.runs.postgres_schedules import PostgresScheduleDispatcher


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="Read-only schema and schedule preflight")
    group.add_argument("--once", action="store_true", help="Dispatch one polling cycle")
    parser.add_argument("--interval", type=float, default=5.0)
    parser.add_argument("--stop-file", type=Path)
    args = parser.parse_args()
    if not 1 <= args.interval <= 60:
        parser.error("--interval must be 1..60 seconds")
    if not os.environ.get("DEVCORE_LOCAL_ROOT") or not os.environ.get("DEVCORE_DATA_ROOT"):
        parser.error("Explicit isolated local and data roots required")
    if os.environ.get("DEVCORE_TASK_READ_MODE") != "postgres":
        parser.error("PostgreSQL task mode required")
    dsn = os.environ.get("DEVCORE_DATABASE_URL", "").strip()
    if not dsn:
        parser.error("DEVCORE_DATABASE_URL required")
    dispatcher = PostgresScheduleDispatcher(dsn)
    dispatcher.verify_ready()
    if args.check:
        print(json.dumps({"status": "postgres_schedule_ready"}))
        return 0
    if args.once:
        print(json.dumps({"status": "postgres_schedule_cycle", "dispatched": dispatcher.poll_once()}))
        return 0

    stop = threading.Event()
    stop_token = os.environ.get("DEVCORE_SCHEDULER_STOP_TOKEN", "")
    if args.stop_file:
        local_root = Path(os.environ["DEVCORE_LOCAL_ROOT"]).resolve()
        stop_file = args.stop_file.resolve()
        if not stop_file.is_relative_to(local_root) or len(stop_token) != 32:
            parser.error("Qualified stop file and token required")
    else:
        stop_file = None

    def request_stop(*_):
        stop.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, request_stop)
    print(json.dumps({"status": "postgres_schedule_started", "pid": os.getpid()}), flush=True)
    next_cycle = 0.0
    while not stop.is_set():
        if stop_file is not None:
            try:
                request = json.loads(stop_file.read_text(encoding="utf-8"))
                if request.get("pid") == os.getpid() and request.get("token") == stop_token:
                    stop.set()
                    break
            except (OSError, ValueError, AttributeError):
                pass
        if time.monotonic() >= next_cycle:
            try:
                dispatched = dispatcher.poll_once()
                if dispatched:
                    print(json.dumps({"status": "postgres_schedule_cycle", "dispatched": dispatched}), flush=True)
            except Exception as exc:
                print(json.dumps({"status": "postgres_schedule_error", "error": type(exc).__name__}),
                      file=sys.stderr, flush=True)
                return 1
            next_cycle = time.monotonic() + args.interval
        stop.wait(min(1.0, max(0.0, next_cycle - time.monotonic())))
    if stop_file is not None:
        try:
            request = json.loads(stop_file.read_text(encoding="utf-8"))
            if request.get("pid") == os.getpid() and request.get("token") == stop_token:
                stop_file.unlink()
        except (OSError, ValueError, AttributeError):
            pass
    print(json.dumps({"status": "postgres_schedule_stopped"}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
