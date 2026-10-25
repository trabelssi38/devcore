"""Build an attested v252 performance candidate from the pinned v251 release.

This never changes the active service or its release. It refuses an existing
destination and updates only the Dashboard bundle and one installed engine file.
"""
from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import shutil
import sys
import zipfile
from pathlib import Path


PARENT = Path("E:/DevCoreRuntime/qualification/service-profile-v250-postgres/runtime/releases")
OLD = PARENT / "devcore-py31316-20261015-postgres-v251"
NEW = PARENT / "devcore-py31316-20261015-postgres-v252"
SOURCE = Path("E:/src_python/devcore/DEV_CORE")
ENGINE_NAME = "devcore_engine/security/postgres_browser_sessions.py"
WHEEL_NAME = "devcore_engine-10.2.0-py3-none-any.whl"
DIST_RECORD = "devcore_engine-10.2.0.dist-info/RECORD"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def record_hash(data: bytes) -> str:
    return "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def update_record(data: bytes, member: str, replacement: bytes) -> bytes:
    rows = list(csv.reader(io.StringIO(data.decode("utf-8"))))
    matches = [row for row in rows if row[0] == member]
    if len(matches) != 1:
        raise ValueError(f"Expected one RECORD row for {member}")
    matches[0][1:] = [record_hash(replacement), str(len(replacement))]
    output = io.StringIO(newline="")
    csv.writer(output, lineterminator="\n").writerows(rows)
    return output.getvalue().encode("utf-8")


def patched_engine(source: bytes) -> bytes:
    text = source.decode("utf-8")
    start = text.index("def _read_session(")
    end = text.index("\ndef session_info(", start)
    before, block, after = text[:start], text[start:end], text[end:]
    changes = (
        ("*, csrf: str | None = None, mutate: bool = False) -> BrowserSession:",
         "*, csrf: str | None = None, mutate: bool = False,\n                  connection=None) -> BrowserSession:"),
        ("    conn = _connect(dsn)\n", "    conn = connection if connection is not None else _connect(dsn)\n"),
        ("    finally:\n        conn.close()\n", "    finally:\n        if connection is None:\n            conn.close()\n"),
        ("*, csrf: str | None = None, mutate: bool = False) -> BrowserSession:\n    return _read_session(dsn, secret, project, action, origin, csrf=csrf, mutate=mutate)",
         "*, csrf: str | None = None, mutate: bool = False,\n                      connection=None) -> BrowserSession:\n    return _read_session(dsn, secret, project, action, origin, csrf=csrf,\n                         mutate=mutate, connection=connection)"),
    )
    # The first signature also appears in authorize_session; limit the first
    # replacement to the _read_session block, then replace its own signature.
    for old, new in changes:
        if old not in block:
            raise ValueError(f"Pinned v251 engine structure changed: {old[:35]}")
        block = block.replace(old, new, 1)
    result = (before + block + after).encode("utf-8")
    compile(result, ENGINE_NAME, "exec")
    return result


def main() -> int:
    if not OLD.is_dir() or NEW.exists():
        raise SystemExit("Pinned v251 missing or v252 destination already exists")
    old_bundle_manifest = json.loads((OLD / "individual-platform-v2/manifest.json").read_text(encoding="utf-8"))
    old_engine_manifest = json.loads((OLD / "artifacts/manifest.json").read_text(encoding="utf-8"))
    dashboard_rel = "Scripts/dashboard_api.py"
    old_dashboard = OLD / "individual-platform-v2" / dashboard_rel
    old_engine = OLD / "Lib/site-packages" / ENGINE_NAME
    if sha(old_dashboard.read_bytes()) != old_bundle_manifest["files"][dashboard_rel]:
        raise SystemExit("Pinned v251 Dashboard hash differs")
    if sha(old_engine.read_bytes()) != old_engine_manifest["source_files_sha256"][ENGINE_NAME]:
        raise SystemExit("Pinned v251 engine hash differs")
    dashboard = (SOURCE / dashboard_rel).read_bytes()
    compile(dashboard, dashboard_rel, "exec")
    engine = patched_engine(old_engine.read_bytes())

    shutil.copytree(OLD, NEW, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    (NEW / "individual-platform-v2" / dashboard_rel).write_bytes(dashboard)
    bundle_manifest_path = NEW / "individual-platform-v2/manifest.json"
    bundle_manifest = json.loads(bundle_manifest_path.read_text(encoding="utf-8"))
    bundle_manifest["files"][dashboard_rel] = sha(dashboard)
    write_json(bundle_manifest_path, bundle_manifest)
    service_path = NEW / "individual-service.json"
    service = json.loads(service_path.read_text(encoding="utf-8"))
    service["bundle_manifest_sha256"] = sha(bundle_manifest_path.read_bytes())
    write_json(service_path, service)

    (NEW / "Lib/site-packages" / ENGINE_NAME).write_bytes(engine)
    installed_record = NEW / "Lib/site-packages" / DIST_RECORD
    installed_record.write_bytes(update_record(installed_record.read_bytes(), ENGINE_NAME, engine))

    wheel_path = NEW / "artifacts/wheels" / WHEEL_NAME
    temporary_wheel = wheel_path.with_suffix(".candidate")
    with zipfile.ZipFile(wheel_path) as original, zipfile.ZipFile(temporary_wheel, "w") as updated:
        if ENGINE_NAME not in original.namelist() or DIST_RECORD not in original.namelist():
            raise ValueError("Pinned wheel is missing the engine module or RECORD")
        wheel_record = update_record(original.read(DIST_RECORD), ENGINE_NAME, engine)
        for member in original.infolist():
            data = engine if member.filename == ENGINE_NAME else (wheel_record if member.filename == DIST_RECORD else original.read(member.filename))
            updated.writestr(member, data)
    temporary_wheel.replace(wheel_path)

    engine_manifest_path = NEW / "artifacts/manifest.json"
    engine_manifest = json.loads(engine_manifest_path.read_text(encoding="utf-8"))
    engine_manifest["source_files_sha256"][ENGINE_NAME] = sha(engine)
    engine_manifest["wheel_sha256"][WHEEL_NAME] = sha(wheel_path.read_bytes())
    engine_manifest["performance_candidate"] = "bounded PostgreSQL read pool and single-connection browser task authorization"
    write_json(engine_manifest_path, engine_manifest)
    provenance_path = NEW / "provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["engine_artifact_manifest_sha256"] = sha(engine_manifest_path.read_bytes())
    provenance["performance_parent_release"] = str(OLD)
    provenance["performance_scope"] = "browser task reads only; active service unchanged"
    write_json(provenance_path, provenance)
    print(json.dumps({"status": "v252_candidate_built", "release": str(NEW),
                      "bundle_manifest_sha256": service["bundle_manifest_sha256"],
                      "wheel_sha256": engine_manifest["wheel_sha256"][WHEEL_NAME],
                      "engine_manifest_sha256": provenance["engine_artifact_manifest_sha256"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
