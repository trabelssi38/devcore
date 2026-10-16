"""Publish an attested LAN service candidate without changing the active SCM service."""
from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
from pathlib import Path
import shutil
import zipfile


PARENT = Path("E:/DevCoreRuntime/qualification/service-profile-v250-postgres/runtime/releases")
OLD = PARENT / "devcore-py31316-20261015-postgres-v252-clean"
NEW = PARENT / "devcore-py31316-20261015-postgres-v253-lan"
SOURCE = Path("E:/src_python/devcore/DEV_CORE")
ENGINE_FILE = "devcore_engine/windows_service.py"
CONTROL_FILES = ("Scripts/launch_individual_candidate.py", "Scripts/service_runtime.py")
WHEEL_NAME = "devcore_engine-10.2.0-py3-none-any.whl"
DIST_RECORD = "devcore_engine-10.2.0.dist-info/RECORD"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def record_hash(data: bytes) -> str:
    return "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()


def update_record(data: bytes, member: str, replacement: bytes) -> bytes:
    rows = list(csv.reader(io.StringIO(data.decode("utf-8"))))
    matches = [row for row in rows if row[0] == member]
    if len(matches) != 1:
        raise ValueError(f"Expected one RECORD row for {member}")
    matches[0][1:] = [record_hash(replacement), str(len(replacement))]
    output = io.StringIO(newline="")
    csv.writer(output, lineterminator="\n").writerows(rows)
    return output.getvalue().encode("utf-8")


def build() -> dict:
    if not OLD.is_dir() or NEW.exists():
        raise ValueError("Pinned v252 release missing or v253 destination already exists")
    controls_manifest_path = OLD / "controls/manifest.json"
    controls_manifest = json.loads(controls_manifest_path.read_text(encoding="utf-8"))
    engine_manifest_path = OLD / "artifacts/manifest.json"
    engine_manifest = json.loads(engine_manifest_path.read_text(encoding="utf-8"))
    provenance = json.loads((OLD / "provenance.json").read_text(encoding="utf-8"))
    if (sha(controls_manifest_path.read_bytes()) != provenance["controls_manifest_sha256"]
            or sha(engine_manifest_path.read_bytes()) != provenance["engine_artifact_manifest_sha256"]):
        raise ValueError("Pinned v252 release manifest changed")
    replacements = {name: (SOURCE / name).read_bytes() for name in CONTROL_FILES}
    replacements[ENGINE_FILE] = (SOURCE / ENGINE_FILE).read_bytes()
    for name, data in replacements.items():
        compile(data, name, "exec")
        manifest = controls_manifest if name in CONTROL_FILES else engine_manifest
        pin = manifest["files"][name] if name in CONTROL_FILES else manifest["source_files_sha256"][name]
        source = OLD / ("controls" if name in CONTROL_FILES else "Lib/site-packages") / name
        if sha(source.read_bytes()) != pin:
            raise ValueError(f"Pinned v252 source changed: {name}")

    shutil.copytree(OLD, NEW, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for name in CONTROL_FILES:
        (NEW / "controls" / name).write_bytes(replacements[name])
        controls_manifest["files"][name] = sha(replacements[name])
    new_controls_manifest = NEW / "controls/manifest.json"
    write_json(new_controls_manifest, controls_manifest)

    engine = replacements[ENGINE_FILE]
    (NEW / "Lib/site-packages" / ENGINE_FILE).write_bytes(engine)
    installed_record = NEW / "Lib/site-packages" / DIST_RECORD
    installed_record.write_bytes(update_record(installed_record.read_bytes(), ENGINE_FILE, engine))
    wheel = NEW / "artifacts/wheels" / WHEEL_NAME
    temporary = wheel.with_suffix(".candidate")
    with zipfile.ZipFile(wheel) as original, zipfile.ZipFile(temporary, "w") as updated:
        if ENGINE_FILE not in original.namelist() or DIST_RECORD not in original.namelist():
            raise ValueError("Pinned wheel is missing its engine module or RECORD")
        wheel_record = update_record(original.read(DIST_RECORD), ENGINE_FILE, engine)
        for member in original.infolist():
            data = engine if member.filename == ENGINE_FILE else (
                wheel_record if member.filename == DIST_RECORD else original.read(member.filename))
            updated.writestr(member, data)
    temporary.replace(wheel)
    new_engine_manifest = NEW / "artifacts/manifest.json"
    engine_manifest["source_files_sha256"][ENGINE_FILE] = sha(engine)
    engine_manifest["wheel_sha256"][WHEEL_NAME] = sha(wheel.read_bytes())
    write_json(new_engine_manifest, engine_manifest)

    config_path = NEW / "individual-service.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != 2 or config.get("local_relative") != "state/local":
        raise ValueError("Unexpected v252 service profile")
    config["schema_version"] = 3
    config["network"] = {
        "bind": "172.16.210.32",
        "cert_relative": "state/local/Security/lan-tls/cert.pem",
        "key_relative": "state/local/Security/lan-tls/key.pem",
    }
    write_json(config_path, config)

    new_provenance = NEW / "provenance.json"
    provenance["controls_manifest_sha256"] = sha(new_controls_manifest.read_bytes())
    provenance["engine_artifact_manifest_sha256"] = sha(new_engine_manifest.read_bytes())
    provenance["lan_parent_release"] = str(OLD)
    provenance["lan_scope"] = "HTTPS Dashboard service candidate; active SCM service unchanged"
    write_json(new_provenance, provenance)
    return {"status": "v253_lan_candidate_built", "release": str(NEW),
            "controls_manifest_sha256": provenance["controls_manifest_sha256"],
            "engine_manifest_sha256": provenance["engine_artifact_manifest_sha256"],
            "wheel_sha256": engine_manifest["wheel_sha256"][WHEEL_NAME]}


if __name__ == "__main__":
    print(json.dumps(build(), separators=(",", ":")))
