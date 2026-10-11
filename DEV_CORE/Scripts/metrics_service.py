"""Bounded, local-only metric events for the legacy PowerShell contract."""
from __future__ import annotations

import argparse
import base64
import binascii
from contextlib import contextmanager
from datetime import datetime
import json
import math
import os
from pathlib import Path
import re
import sys


SNAPSHOT_TYPES = {"tokens", "cache_hits", "cost", "sessions"}
SECRET_KEYS = ("secret", "password", "api_key", "access_token", "authorization", "credential")
MAX_PAYLOAD_BYTES = 8192
MAX_EVENT_BYTES = 16384
MAX_STORE_BYTES = 64 * 1024 * 1024
MAX_BATCH_EVENTS = 512


def local_metrics_dir() -> Path:
    explicit = os.getenv("DEVCORE_LOCAL_ROOT")
    app_data = os.getenv("LOCALAPPDATA")
    if not explicit and not app_data:
        raise ValueError("DEVCORE_LOCAL_ROOT or LOCALAPPDATA is required")
    root = Path(explicit) if explicit else Path(app_data) / "DEV_CORE_LOCAL"
    root = root.resolve()
    data = os.getenv("DEVCORE_DATA_ROOT")
    if data and root.is_relative_to(Path(data).resolve()):
        raise ValueError("Local metrics root cannot be inside DEVCORE_DATA_ROOT")
    return root / "Logs" / "metrics"


def store_path(day: str | None = None) -> Path:
    return local_metrics_dir() / f"metrics-{day or datetime.now().strftime('%Y-%m-%d')}.jsonl"


@contextmanager
def append_lock(directory: Path):
    with (directory / ".metrics.lock").open("a+b") as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _redact(value):
    if isinstance(value, dict):
        return {str(key): "[REDACTED]" if any(part in str(key).lower() for part in SECRET_KEYS)
                else _redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def _make_event(*, source: str, project: str, task_id: str, metric_type: str,
                value: float, unit: str, payload_json: str = "{}") -> dict:
    for label, item in (("source", source), ("project", project), ("metric_type", metric_type), ("unit", unit)):
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", item):
            raise ValueError(f"Invalid {label}")
    if task_id and not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", task_id):
        raise ValueError("Invalid task_id")
    if not math.isfinite(value):
        raise ValueError("Metric value must be finite")
    if len(payload_json.encode("utf-8")) > MAX_PAYLOAD_BYTES:
        raise ValueError("Metric payload too large")
    payload = json.loads(payload_json)
    if not isinstance(payload, dict):
        raise ValueError("Metric payload must be an object")
    event = {"schema_version": 1, "event_type": "MetricRecorded",
             "recorded_at": datetime.now().astimezone().isoformat(),
             "source": source, "project": project, "task_id": task_id,
             "metric_type": metric_type, "value": value, "unit": unit,
             "payload": _redact(payload)}
    return event


def _append_events(events: list[dict]) -> None:
    encoded_lines = [(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
                     for event in events]
    if any(len(line) > MAX_EVENT_BYTES for line in encoded_lines):
        raise ValueError("Metric event too large")
    encoded = b"".join(encoded_lines)
    path = store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with append_lock(path.parent):
        needs_leading_newline = False
        current_size = 0
        if path.exists():
            current_size = path.stat().st_size
            if current_size > 0:
                with path.open("rb") as reader:
                    reader.seek(current_size - 1)
                    if reader.read(1) != b"\n":
                        needs_leading_newline = True
        prefix = b"\n" if needs_leading_newline else b""
        if current_size + len(prefix) + len(encoded) > MAX_STORE_BYTES:
            raise ValueError("Daily metrics store is full")
        with path.open("ab") as handle:
            if prefix:
                handle.write(prefix)
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())


def record(*, source: str, project: str, task_id: str, metric_type: str,
           value: float, unit: str, payload_json: str = "{}") -> dict:
    event = _make_event(source=source, project=project, task_id=task_id,
                        metric_type=metric_type, value=value, unit=unit,
                        payload_json=payload_json)
    _append_events([event])
    return event


def record_batch(records: list[dict]) -> dict:
    if not isinstance(records, list) or not 1 <= len(records) <= MAX_BATCH_EVENTS:
        raise ValueError("Metric batch size is invalid")
    events = []
    for record_item in records:
        if not isinstance(record_item, dict):
            raise ValueError("Metric batch item must be an object")
        payload = record_item.get("payload", {})
        events.append(_make_event(
            source=record_item.get("source", ""),
            project=record_item.get("project", ""),
            task_id=record_item.get("task_id", ""),
            metric_type=record_item.get("metric_type", ""),
            value=record_item.get("value", 0),
            unit=record_item.get("unit", ""),
            payload_json=json.dumps(payload, ensure_ascii=False),
        ))
    _append_events(events)
    return {"recorded": len(events)}


def health() -> dict:
    path = store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    return {"schema_version": 1, "ok": True, "metrics_dir": str(path.parent),
            "store_path": str(path), "writable": True}


def _group(table: dict, metric_type: str, unit: str, value: float, snapshot: bool):
    entry = table.setdefault(metric_type, {}).setdefault(unit, {
        "count": 0, "sum": 0.0, "latest": 0.0, "aggregation": "sum"})
    entry["count"] += 1
    entry["latest"] = value
    entry["sum"] = value if snapshot else round(entry["sum"] + value, 6)
    if snapshot:
        entry["aggregation"] = "latest"


def valid_event(event) -> bool:
    if not isinstance(event, dict) or event.get("schema_version") != 1 or event.get("event_type") != "MetricRecorded":
        return False
    for key in ("source", "project", "metric_type", "unit"):
        value = event.get(key)
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", value):
            return False
    task_id = event.get("task_id")
    if task_id is not None and task_id != "" and (not isinstance(task_id, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", task_id)):
        return False
    value = event.get("value")
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def aggregate() -> dict:
    path = store_path()
    events, errors = [], 0
    if path.exists():
        if path.stat().st_size > MAX_STORE_BYTES:
            raise ValueError("Daily metrics store is too large")
        with path.open("rb") as handle:
            for line in handle:
                if len(line) > MAX_EVENT_BYTES:
                    errors += 1
                    continue
                try:
                    event = json.loads(line)
                    if not valid_event(event):
                        raise ValueError("Unexpected metric event")
                    events.append(event)
                except (ValueError, AttributeError):
                    errors += 1
    totals, projects, tasks, sources = {}, {}, {}, {}
    snapshot_values = {}
    for event in events:
        kind, unit = event["metric_type"], event["unit"]
        value, source, project = float(event["value"]), event["source"], event["project"]
        task_id = event.get("task_id") or ""
        if not task_id or task_id == "none":
            task_key = "none"
        elif task_id.startswith(f"{project}_"):
            task_key = task_id
        else:
            task_key = f"{project}_{task_id}"
        snapshot = source == "token_report" and kind in SNAPSHOT_TYPES
        project_group = projects.setdefault(project, {"events_count": 0, "totals": {}})
        project_group["events_count"] += 1
        _group(project_group["totals"], kind, unit, value, snapshot)
        task_group = tasks.setdefault(task_key, {"events_count": 0, "totals": {}})
        task_group["events_count"] += 1
        _group(task_group["totals"], kind, unit, value, snapshot)
        sources.setdefault(source, {"events_count": 0})["events_count"] += 1
        if snapshot:
            snapshot_values[(project, kind, unit)] = value
        else:
            _group(totals, kind, unit, value, False)
    snapshot_counts = {}
    for (_, kind, unit), value in snapshot_values.items():
        _group(totals, kind, unit, value, False)
        snapshot_counts[(kind, unit)] = snapshot_counts.get((kind, unit), 0) + 1
    for (kind, unit), count in snapshot_counts.items():
        totals[kind][unit]["aggregation"] = "latest" if count == 1 else "latest_by_project"
    return {"schema_version": 1, "date": datetime.now().strftime("%Y-%m-%d"),
            "store_path": str(path), "events_count": len(events), "errors_count": errors,
            "totals": totals, "projects": projects, "tasks": tasks, "sources": sources}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-Action", required=True, choices=("Health", "Record", "RecordBatch", "Aggregate", "Status"))
    parser.add_argument("-Json", action="store_true")
    parser.add_argument("-Source", default="")
    parser.add_argument("-Project", default="")
    parser.add_argument("-TaskId", default="")
    parser.add_argument("-MetricType", default="")
    parser.add_argument("-Value", type=float, default=0.0)
    parser.add_argument("-Unit", default="")
    parser.add_argument("-PayloadJson", default="{}")
    parser.add_argument("-PayloadBase64")
    args = parser.parse_args()
    try:
        if args.Action == "Health":
            result = health()
        elif args.Action == "Record":
            payload_json = (base64.b64decode(args.PayloadBase64, validate=True).decode("utf-8")
                            if args.PayloadBase64 is not None else args.PayloadJson)
            result = record(source=args.Source, project=args.Project, task_id=args.TaskId,
                            metric_type=args.MetricType, value=args.Value,
                            unit=args.Unit, payload_json=payload_json)
        elif args.Action == "RecordBatch":
            if args.PayloadBase64 is None:
                raise ValueError("RecordBatch requires PayloadBase64")
            batch_json = base64.b64decode(args.PayloadBase64, validate=True).decode("utf-8")
            if len(batch_json.encode("utf-8")) > MAX_BATCH_EVENTS * MAX_EVENT_BYTES:
                raise ValueError("Metric batch too large")
            result = record_batch(json.loads(batch_json))
        elif args.Action == "Aggregate":
            result = aggregate()
        else:
            result = {"health": health(), "aggregate": aggregate()}
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError, UnicodeError, binascii.Error) as exc:
        print(f"metrics_service: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
