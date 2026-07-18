import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


def setup_scheduler_logging(
    log_dir: Path,
    log_name: str = "scheduler_tick.log",
    level: int = logging.INFO
) -> logging.Logger:
    """Configure rotating file logging and console logging for the scheduler."""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / log_name

    logger = logging.getLogger()
    logger.setLevel(level)

    # Clear existing handlers to prevent duplicate logs in tests
    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 1. Rotating File Handler (Max 5MB, keep 5 backups)
    file_handler = RotatingFileHandler(
        str(log_file),
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 2. Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Disable propagating for cleaner output
    logger.propagate = False

    return logger
