"""Protect newly reserved credentials before writing secret bytes; no shell interpolation."""

import json
import os
from pathlib import Path
import subprocess


class SecretProtectionUnavailable(PermissionError):
    pass


def windows_acl(path, mode):
    if os.name != "nt":
        raise SecretProtectionUnavailable("Windows NTFS protection unavailable")
    path = Path(path)
    if not path.is_absolute():
        raise ValueError("Absolute secret path required")
    script = Path(__file__).with_name("windows_secret_acl.ps1")
    executable = Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    # Windows os.environ copies expose uppercase keys; filter case-insensitively.
    environment = {k: v for k, v in os.environ.items() if k.casefold() != "psmodulepath"}
    try:
        result = subprocess.run(
            [str(executable), "-NoProfile", "-NonInteractive", "-File", str(script),
             "-LiteralPath", str(path), "-Mode", mode],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15, check=False,
            env=environment,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        metadata = json.loads(result.stdout) if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        raise SecretProtectionUnavailable("Windows secret protection unavailable") from exc
    if not isinstance(metadata, dict) or metadata.get("valid") is not True:
        raise SecretProtectionUnavailable("Windows secret protection refused")
    return metadata


def protect_reserved_file(path):
    if os.name == "nt":
        return windows_acl(path, "ProtectFile")
    # Conventional POSIX permissions; Windows qualification does not cover this branch.
    os.chmod(path, 0o600)


def check_credential_file(path):
    if os.name == "nt":
        return windows_acl(path, "CheckFile")


def protect_empty_directory(path):
    return windows_acl(path, "ProtectDirectory")


def validate_output_path(path):
    path = Path(path)
    if not path.is_absolute():
        raise ValueError("Absolute secret path required")
    if os.name == "nt":
        windows_acl(path.parent, "ValidateDirectory")
