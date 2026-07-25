#!/usr/bin/env python3
"""Standalone cron scheduler tick loop daemon.
Runs in the background, executing cron.scheduler.tick() every 60 seconds.
Logs status and outcomes to DEV_CORE_DATA/Logs/hermes/cron_tick.log.
"""
import os
import sys
import time
import logging
PLATFORM_ROOT = Path(os.environ.get("DEVCORE_PLATFORM_ROOT", Path(__file__).resolve().parents[1]))
REPO_ROOT = Path(os.environ.get("DEVCORE_REPO_ROOT", PLATFORM_ROOT.parent))
DATA_ROOT = Path(os.environ.get("DEVCORE_DATA_ROOT", r"C:\devcore\DEV_CORE_DATA" if os.name == "nt" else "/data"))

# Append Hermes checkout to path to import native cron scheduler APIs
HERMES_HOME = Path(os.environ.get("HERMES_REPO_HOME", REPO_ROOT / "hermes"))
if HERMES_HOME.exists():
    sys.path.append(str(HERMES_HOME))

# Configure logging
LOG_DIR = DATA_ROOT / "Logs" / "hermes"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "cron_tick.log"
LOCK_FILE = Path(os.environ.get("HERMES_CRON_LOCK_FILE") or os.path.expanduser("~/.hermes/cron/.tick.lock"))
LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)

handlers = [RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")]
if sys.stdout is not None:
    handlers.append(logging.StreamHandler(sys.stdout))

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    handlers=handlers
)
logger = logging.getLogger("HermesCronDaemon")

def acquire_single_instance_lock():
    lock_handle = LOCK_FILE.open("a+b")
    try:
        if sys.platform == "win32":
            import msvcrt
            msvcrt.locking(lock_handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (OSError, IOError):
        logger.warning(f"Another hermes_cron_tick.py instance owns {LOCK_FILE}; exiting.")
        lock_handle.close()
        sys.exit(0)
    lock_handle.seek(0)
    lock_handle.truncate()
    lock_handle.write(str(os.getpid()).encode("ascii"))
    lock_handle.flush()
    return lock_handle

def main():
    lock_handle = acquire_single_instance_lock()
    logger.info("Starting Standalone Hermes Cron Scheduler Daemon v9.0...")
    logger.info(f"Logging to {LOG_FILE}")
    logger.info(f"Single-instance lock acquired: {LOCK_FILE}")
    
    try:
        from cron.scheduler import tick
        logger.info("Successfully imported Hermes cron scheduler.")
    except ImportError as e:
        logger.error(f"Failed to import Hermes cron scheduler from {HERMES_HOME}: {e}")
        sys.exit(1)

    # Infinite tick loop
    try:
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
    finally:
        try:
            if sys.platform == "win32":
                import msvcrt
                msvcrt.locking(lock_handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        except Exception:
            pass
        lock_handle.close()

if __name__ == "__main__":
    main()
