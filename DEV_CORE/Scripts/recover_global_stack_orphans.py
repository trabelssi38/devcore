"""Cooperatively stop verified global children after their supervisor exits."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SCRIPTS.parent / "Scheduler"))

from service_runtime import request_stop
from windows_process_identity import process_identity


NAMES = {
    "router": ("gemini_router.py", 20130),
    "headroom-native": ("headroom_routes.py", 8787),
    "headroom-auxiliary": ("headroom_routes.py", 8789),
    "gateway": ("launch_postgres_gateway.py", 20131),
    "scheduler": ("postgres_schedule_daemon.py", None),
    "repowise": ("launch_managed_repowise.py", 7337),
}


def _processes(pids: list[int]) -> dict[int, dict]:
    selected = ",".join(str(pid) for pid in pids)
    command = ("Get-CimInstance Win32_Process | Where-Object { @(" + selected +
               ") -contains $_.ProcessId } | Select-Object ProcessId,ParentProcessId,CommandLine "
               "| ConvertTo-Json -Compress")
    result = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
                            capture_output=True, text=True, timeout=20, check=True)
    raw = result.stdout.strip()
    items = json.loads(raw) if raw else []
    return {int(item["ProcessId"]): item for item in
            (items if isinstance(items, list) else [items])}


def _listeners() -> dict[int, int]:
    result = subprocess.run(["netstat", "-ano", "-p", "TCP"],
                            capture_output=True, text=True, timeout=10, check=True)
    found = {}
    for line in result.stdout.splitlines():
        fields = line.split()
        if (len(fields) == 5 and fields[0] == "TCP" and fields[1].startswith("127.0.0.1:")
                and fields[3] == "LISTENING" and fields[4].isdecimal()):
            found[int(fields[1].rsplit(":", 1)[1])] = int(fields[4])
    return found


def _stop_file(path: Path, pid: int, token: str) -> None:
    path.write_text(json.dumps({"pid": pid, "token": token}), encoding="utf-8")


def recover(manifest_path: Path, local: Path, data: Path, platform: Path, source: Path) -> dict:
    manifest_path = manifest_path.resolve(strict=True)
    local = local.resolve(strict=True)
    data = data.resolve(strict=True)
    platform = platform.resolve(strict=True)
    source = source.resolve(strict=True)
    if manifest_path != local / "GlobalStack" / "candidate-processes.json":
        raise ValueError("Manifest is outside the selected local root")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    parent = manifest.get("supervisor_pid")
    token = manifest.get("stop_token")
    children = manifest.get("processes")
    if (type(parent) is not int or not isinstance(token, str) or len(token) != 32
            or not isinstance(children, dict) or set(children) != set(NAMES)):
        raise ValueError("Invalid global supervisor record")
    try:
        if process_identity(parent) == manifest.get("supervisor_identity"):
            raise ValueError("Global supervisor is still live; use its normal --stop")
    except OSError:
        pass
    pids = {name: item.get("pid") for name, item in children.items()}
    if any(type(pid) is not int or pid <= 0 for pid in pids.values()) or len(set(pids.values())) != len(pids):
        raise ValueError("Invalid or repeated child PID")
    live = _processes(list(pids.values()))
    listeners = _listeners()
    for name, (script_name, port) in NAMES.items():
        pid = pids[name]
        item = live.get(pid)
        if item is None:
            continue
        expected = str(source / "DEV_CORE" / "Scripts" / script_name).lower()
        actual = str(item.get("CommandLine") or "").lower()
        if item.get("ParentProcessId") != parent or expected not in actual:
            raise ValueError(f"Process identity differs for {name}")
        if port is not None and listeners.get(port) != pid:
            raise ValueError(f"Listener identity differs for {name}")
        if name == "headroom-native" and "--route native" not in actual:
            raise ValueError("Native route identity differs")
        if name == "headroom-auxiliary" and "--route auxiliary" not in actual:
            raise ValueError("Auxiliary route identity differs")
    results = {}
    for name in ("repowise", "scheduler"):
        pid = pids[name]
        if pid not in live:
            results[name] = "already_stopped"
            continue
        stop_path = local / "GlobalStack" / f"{name}-stop-{token[:8]}.json"
        _stop_file(stop_path, pid, token)
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            if pid not in _processes([pid]):
                results[name] = "stopped"
                break
            time.sleep(.25)
        else:
            results[name] = "stop_timeout"
    for name in ("gateway", "headroom-auxiliary", "headroom-native", "router"):
        pid = pids[name]
        if pid not in live:
            results[name] = "already_stopped"
            continue
        result = request_stop(str(local), str(data), str(platform), name, wait_seconds=15)
        results[name] = "stopped" if result.get("shutdown_completed") else "stop_incomplete"
    if any(value not in {"stopped", "already_stopped"} for value in results.values()):
        raise RuntimeError("Orphan recovery incomplete: " + json.dumps(results))
    manifest["status"] = "recovered_stopped"
    manifest["recovery"] = results
    temporary = manifest_path.with_suffix(".recovery.tmp")
    temporary.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    deadline = time.monotonic() + 5
    while True:
        try:
            os.replace(temporary, manifest_path)
            break
        except PermissionError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(.05)
    return {"status": "global_orphans_recovered", "children": results}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("manifest", "local", "data", "platform", "source"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(recover(args.manifest, args.local, args.data, args.platform, args.source)))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "global_orphan_recovery_refused", "reason": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
