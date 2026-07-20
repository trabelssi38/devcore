#!/usr/bin/env python3
# profile_performance.py -- DEV_CORE v10 Empirical Performance Profiler
# Measures execution time (p50, p95) across core platform components.

import os
import sys
import time
import json
import sqlite3
from pathlib import Path
from datetime import datetime

DATA_ROOT = Path(os.environ.get("DEVCORE_DATA_ROOT", r"C:\devcore\DEV_CORE_DATA"))
DEVCORE_ROOT = Path(os.environ.get("DEVCORE_PLATFORM_ROOT", r"C:\devcore\DEV_CORE"))
REPORT_PATH = DATA_ROOT / "Logs" / "performance_profile_report.json"

sys.path.insert(0, str(DEVCORE_ROOT / "Scripts"))

def profile_function(name, func, iterations=5):
    durations = []

    for _ in range(iterations):
        t0 = time.perf_counter()
        func()
        t1 = time.perf_counter()
        durations.append((t1 - t0) * 1000.0) # in ms

    durations.sort()

    p50 = durations[len(durations) // 2]
    p95 = durations[int(len(durations) * 0.95)] if len(durations) > 1 else durations[0]
    avg = sum(durations) / len(durations)

    return {
        "component": name,
        "iterations": iterations,
        "p50_ms": round(p50, 2),
        "p95_ms": round(p95, 2),
        "avg_ms": round(avg, 2),
        "min_ms": round(durations[0], 2),
        "max_ms": round(durations[-1], 2)
    }

def main():
    print("[profile_performance] Starting Empirical Performance Profiling...")
    results = []

    # 1. Profile SQLite Query Latency
    db_path = DATA_ROOT / "devcore.db"
    def benchmark_sqlite():
        if db_path.exists():
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT id, title, status FROM tasks ORDER BY CAST(SUBSTR(id, 3) AS INTEGER) DESC LIMIT 20")
            cur.fetchall()
            conn.close()

    results.append(profile_function("SQLite_Task_Query", benchmark_sqlite, iterations=10))

    # 2. Profile UI Motion Static Audit
    try:
        from audit_ui_motion import main as audit_main
        results.append(profile_function("UI_Motion_Static_Audit", audit_main, iterations=3))
    except Exception as e:
        print(f"[profile_performance] Could not benchmark audit_ui_motion: {e}")

    # 3. Profile Dashboard HTML Generation
    try:
        from gen_dashboard import main as gen_dash_main
        results.append(profile_function("Dashboard_HTML_Generation", gen_dash_main, iterations=3))
    except Exception as e:
        print(f"[profile_performance] Could not benchmark gen_dashboard: {e}")

    # 4. Profile Log Rotation Engine
    try:
        from rotate_logs_and_backups import main as rotate_main
        results.append(profile_function("Log_Backup_Rotation", rotate_main, iterations=3))
    except Exception as e:
        print(f"[profile_performance] Could not benchmark rotate_logs_and_backups: {e}")

    report = {
        "timestamp": datetime.now().isoformat(),
        "python_version": sys.version.split()[0],
        "platform": sys.platform,
        "components_count": len(results),
        "metrics": results
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4, ensure_ascii=False)

    print("\n--- Empirical Performance Profiling Summary ---")
    for r in results:
        print(f"[{r['component']}] p50={r['p50_ms']} ms | p95={r['p95_ms']} ms | avg={r['avg_ms']} ms")

    print(f"\nReport saved to: {REPORT_PATH}")

if __name__ == "__main__":
    main()
