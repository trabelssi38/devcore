#!/usr/bin/env python3
# check_ui_gates.py -- DEV_CORE v10 CI Gate Enforcement for UI & Motion Standards
# Returns exit code 1 if any P0 (transition: all) or critical animation violation is found.

import os
import sys
import json
from pathlib import Path

# Add Scripts directory to sys.path
sys.path.insert(0, str(Path(__file__).parent))

from audit_ui_motion import scan_file, TARGET_PATHS

def main():
    print("[check_ui_gates] Running CI UI Gates Enforcement Check...")
    all_findings = []
    files_scanned = 0

    for path in TARGET_PATHS:
        if path.is_file():
            all_findings.extend(scan_file(path))
            files_scanned += 1
        elif path.is_dir():
            for root, _, files in os.walk(path):
                for f in files:
                    if f.endswith((".html", ".css", ".tsx", ".jsx", ".js", ".ts")):
                        file_path = Path(root) / f
                        all_findings.extend(scan_file(file_path))
                        files_scanned += 1

    p0_count = sum(1 for f in all_findings if f["severity"] == "P0")
    p1_count = sum(1 for f in all_findings if f["severity"] == "P1")

    print(f"[check_ui_gates] Scanned {files_scanned} files. P0 (Critical) = {p0_count}, P1 (Warning) = {p1_count}")

    if p0_count > 0:
        print(f"[check_ui_gates] FAIL: {p0_count} P0 violation(s) detected (e.g. transition: all). CI Gate FAILED.")
        sys.exit(1)
    else:
        print("[check_ui_gates] PASS: Zero P0 violations. UI & Motion Gate PASSED.")
        sys.exit(0)

if __name__ == "__main__":
    main()
