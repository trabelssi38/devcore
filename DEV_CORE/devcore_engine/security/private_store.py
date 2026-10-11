"""Explicit provisioning and point-in-time NTFS inspection, outside the request path."""

import os
from pathlib import Path

from .identity import initialize_store
from .secret_files import protect_empty_directory, protect_reserved_file, windows_acl


def check_store_protection(path):
    """Read descriptors only; never open SQLite, recover a journal or repair an ACL."""
    return windows_acl(path, "CheckStore")


def initialize_private_store(path):
    """Require an existing empty local NTFS directory; never adopt an existing store.

    Protect the directory before SQLite can create a journal, and the reserved
    database before schema bytes. On failure keep any reserved file for inspection;
    no existing data are deleted and no account or administrative access is created.
    """
    path = Path(path)
    if not path.is_absolute():
        raise ValueError("Identity store requires an absolute path")
    # Check the original path before resolve() could hide a junction alias.
    protect_empty_directory(path.parent)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(descriptor)
    protect_reserved_file(path)
    initialize_store(path)
    return check_store_protection(path)
