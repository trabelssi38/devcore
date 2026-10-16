"""Publish an attested service-startup candidate without touching the active SCM service."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import zipfile

from build_v253_lan_candidate import sha, update_record, write_json


PARENT = Path("E:/DevCoreRuntime/qualification/service-profile-v250-postgres/runtime/releases")
OLD = PARENT / "devcore-py31316-20261015-postgres-v253-lan"
NEW = PARENT / "devcore-py31316-20261016-postgres-v254-restart"
SOURCE = Path("E:/src_python/devcore/DEV_CORE/devcore_engine/windows_service.py")
ENGINE_FILE = "devcore_engine/windows_service.py"
WHEEL_NAME = "devcore_engine-10.2.0-py3-none-any.whl"
DIST_RECORD = "devcore_engine-10.2.0.dist-info/RECORD"


def build() -> dict:
    if not OLD.is_dir() or NEW.exists():
        raise ValueError("Pinned v253 release missing or v254 destination already exists")
    engine_manifest_path = OLD / "artifacts/manifest.json"
    controls_manifest_path = OLD / "controls/manifest.json"
    provenance = json.loads((OLD / "provenance.json").read_text(encoding="utf-8"))
    engine_manifest = json.loads(engine_manifest_path.read_text(encoding="utf-8"))
    if (sha(engine_manifest_path.read_bytes()) != provenance["engine_artifact_manifest_sha256"]
            or sha(controls_manifest_path.read_bytes()) != provenance["controls_manifest_sha256"]):
        raise ValueError("Pinned v253 release manifest changed")
    parent_engine = OLD / "Lib/site-packages" / ENGINE_FILE
    if sha(parent_engine.read_bytes()) != engine_manifest["source_files_sha256"][ENGINE_FILE]:
        raise ValueError("Pinned v253 service module changed")
    replacement = SOURCE.read_bytes()
    compile(replacement, ENGINE_FILE, "exec")
    if replacement == parent_engine.read_bytes():
        raise ValueError("The service module has no startup change")

    shutil.copytree(OLD, NEW, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    (NEW / "Lib/site-packages" / ENGINE_FILE).write_bytes(replacement)
    installed_record = NEW / "Lib/site-packages" / DIST_RECORD
    installed_record.write_bytes(update_record(installed_record.read_bytes(), ENGINE_FILE, replacement))

    wheel = NEW / "artifacts/wheels" / WHEEL_NAME
    temporary = wheel.with_suffix(".candidate")
    with zipfile.ZipFile(wheel) as original, zipfile.ZipFile(temporary, "w") as updated:
        if ENGINE_FILE not in original.namelist() or DIST_RECORD not in original.namelist():
            raise ValueError("Pinned wheel is missing its service module or RECORD")
        wheel_record = update_record(original.read(DIST_RECORD), ENGINE_FILE, replacement)
        for member in original.infolist():
            data = (replacement if member.filename == ENGINE_FILE else
                    wheel_record if member.filename == DIST_RECORD else original.read(member.filename))
            updated.writestr(member, data)
    temporary.replace(wheel)

    new_manifest = NEW / "artifacts/manifest.json"
    engine_manifest["source_files_sha256"][ENGINE_FILE] = sha(replacement)
    engine_manifest["wheel_sha256"][WHEEL_NAME] = sha(wheel.read_bytes())
    write_json(new_manifest, engine_manifest)
    provenance["engine_artifact_manifest_sha256"] = sha(new_manifest.read_bytes())
    provenance["restart_parent_release"] = str(OLD)
    provenance["restart_change"] = "Bounded startup attest/readiness waits extended to 120 seconds"
    write_json(NEW / "provenance.json", provenance)
    return {"status": "v254_restart_candidate_built", "release": str(NEW),
            "engine_manifest_sha256": provenance["engine_artifact_manifest_sha256"],
            "wheel_sha256": engine_manifest["wheel_sha256"][WHEEL_NAME],
            "service_module_sha256": sha(replacement)}


if __name__ == "__main__":
    print(json.dumps(build(), separators=(",", ":")))
