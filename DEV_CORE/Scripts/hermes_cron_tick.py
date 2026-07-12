#!/usr/bin/env python3
"""Standalone cron scheduler tick loop daemon.
Runs in the background, executing cron.scheduler.tick() every 60 seconds.
Logs status and outcomes to DEV_CORE_DATA/Logs/hermes/cron_tick.log.
"""
import os
import sys
import time
import logging
from pathlib import Path

# Append Hermes checkout to path to import native cron scheduler APIs
HERMES_HOME = Path("C:/devcore/hermes")
sys.path.append(str(HERMES_HOME))

# Configure logging
LOG_DIR = Path("C:/devcore/DEV_CORE_DATA/Logs/hermes")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "cron_tick.log"

handlers = [logging.FileHandler(LOG_FILE, encoding="utf-8")]
if sys.stdout is not None:
    handlers.append(logging.StreamHandler(sys.stdout))

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    handlers=handlers
)
logger = logging.getLogger("HermesCronDaemon")

def main():
    logger.info("Starting Standalone Hermes Cron Scheduler Daemon v9.0...")
    logger.info(f"Logging to {LOG_FILE}")
    
    try:
        from cron.scheduler import tick
        logger.info("Successfully imported Hermes cron scheduler.")
    except ImportError as e:
        logger.error(f"Failed to import Hermes cron scheduler from {HERMES_HOME}: {e}")
        sys.exit(1)

    # Infinite tick loop
    while True:
        try:
            logger.info("Executing scheduler tick...")
            # Run tick
            jobs_executed = tick(verbose=True)
            if jobs_executed > 0:
                logger.info(f"Tick complete. Executed {jobs_executed} job(s).")
            else:
                logger.info("Tick complete. No jobs due.")
            
            # Explicitly flush log file to disk instantly
            for handler in logger.handlers + logging.getLogger().handlers:
                try:
                    handler.flush()
                    if hasattr(handler, "stream") and handler.stream is not None and hasattr(handler.stream, "flush"):
                        handler.stream.flush()
                except OSError:
                    pass
        except Exception as e:
            logger.error(f"Exception during scheduler tick: {e}", exc_info=True)
            
        # Sleep for 60 seconds
        time.sleep(60)

if __name__ == "__main__":
    main()
