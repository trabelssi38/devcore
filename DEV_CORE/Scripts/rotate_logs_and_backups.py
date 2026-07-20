# rotate_logs_and_backups.py -- DEV_CORE v10.0 Log & Backup Retention Manager
# Purges log files older than 30 days, bounds automatic backups, and limits token metrics history.

import os
import sys
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

DEV_CORE_DATA = Path(os.environ.get("DEVCORE_DATA_ROOT", r"C:\devcore\DEV_CORE_DATA"))

def rotate_script_logs(max_days=30):
    logs_dir = DEV_CORE_DATA / "Logs" / "scripts"
    if not logs_dir.exists():
        return 0
    cutoff = time.time() - (max_days * 86400)
    removed = 0
    for item in logs_dir.glob("*"):
        if item.is_file() and item.stat().st_mtime < cutoff:
            try:
                item.unlink()
                removed += 1
            except Exception as e:
                print(f"[rotate] Warning: Could not remove {item.name}: {e}")
    print(f"[rotate] Logs rotation complete: {removed} file(s) older than {max_days} days removed.")
    return removed

def rotate_auto_backups(keep_max=5):
    backups_dir = DEV_CORE_DATA / "Backups" / "auto"
    if not backups_dir.exists():
        return 0
    
    # Group files by prefix (e.g., tasks_devcore, board_devcore)
    groups = {}
    for item in backups_dir.glob("*"):
        if item.is_file():
            parts = item.name.split("_")
            prefix = "_".join(parts[:-1]) if len(parts) > 1 else "default"
            groups.setdefault(prefix, []).append(item)

    removed = 0
    for prefix, files in groups.items():
        files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        for old_file in files[keep_max:]:
            try:
                old_file.unlink()
                removed += 1
            except Exception as e:
                print(f"[rotate] Warning: Could not remove old backup {old_file.name}: {e}")
    print(f"[rotate] Auto backups rotation complete: {removed} old backup file(s) removed.")
    return removed

def bound_token_metrics(days_keep=7):
    token_json = DEV_CORE_DATA / "Logs" / "token_reports" / "token_metrics_summary.json"
    if not token_json.exists():
        return
    try:
        data = json.loads(token_json.read_text(encoding="utf-8-sig"))
        sessions = data.get("sessions", [])
        if not sessions:
            return
        
        cutoff_date = (datetime.now() - timedelta(days=days_keep)).strftime("%Y-%m-%d")
        fresh_sessions = []
        archived_sessions = []

        for s in sessions:
            s_date = s.get("date", "")
            if s_date >= cutoff_date:
                fresh_sessions.append(s)
            else:
                archived_sessions.append(s)

        if archived_sessions:
            archive_dir = DEV_CORE_DATA / "Logs" / "token_reports" / "archive"
            archive_dir.mkdir(parents=True, exist_ok=True)
            archive_file = archive_dir / f"archive_tokens_{datetime.now().strftime('%Y_%m')}.json"
            
            existing_archive = []
            if archive_file.exists():
                try:
                    existing_archive = json.loads(archive_file.read_text(encoding="utf-8"))
                except Exception:
                    pass
            existing_archive.extend(archived_sessions)
            archive_file.write_text(json.dumps(existing_archive, indent=2, ensure_ascii=False), encoding="utf-8")
            
            data["sessions"] = fresh_sessions
            token_json.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"[rotate] Token metrics bounded: {len(archived_sessions)} sessions archived ({len(fresh_sessions)} retained).")
    except Exception as e:
        print(f"[rotate] Warning: Token metrics rotation error: {e}")

def main():
    print(f"[rotate] Starting DEV_CORE data rotation for {DEV_CORE_DATA}...")
    rotate_script_logs(max_days=30)
    rotate_auto_backups(keep_max=5)
    bound_token_metrics(days_keep=7)
    print("[rotate] Data rotation completed successfully.")

if __name__ == "__main__":
    main()
