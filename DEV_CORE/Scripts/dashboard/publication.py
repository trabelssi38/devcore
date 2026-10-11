"""Publish one dashboard artifact without exposing a partial UTF-8 file."""
import os
from pathlib import Path
import tempfile


def atomic_write_text(path: Path, text: str) -> None:
    """Replace one file after a complete write and fsync; propagate failures.

    This is not a transaction across artifacts, nor a multiwriter lock.
    Directory durability after power loss depends on the operating system.
    """
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", delete=False,
            dir=path.parent, prefix=f".{path.name}.", suffix=".tmp",
        ) as stream:
            temporary = Path(stream.name)
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
