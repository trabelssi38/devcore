#!/usr/bin/env python3
# audit_ui_motion.py -- DEV_CORE v10 Read-Only UI & Motion Compliance Audit
# Scans HTML, CSS, and TSX files for animation regressions, transition:all, and reduced-motion support.

import os
import sys
import re
import json
from pathlib import Path
from datetime import datetime

DATA_ROOT = Path(os.environ.get("DEVCORE_DATA_ROOT", r"C:\devcore\DEV_CORE_DATA"))
DEVCORE_ROOT = Path(os.environ.get("DEVCORE_PLATFORM_ROOT", r"C:\devcore\DEV_CORE"))
REPORT_PATH = DATA_ROOT / "Logs" / "ui_motion_audit_report.json"

TARGET_PATHS = [
    DEVCORE_ROOT / "Dashboard" / "template.html",
    DEVCORE_ROOT / "Dashboard" / "index.html",
    DEVCORE_ROOT / "Web" / "src"
]

RE_TRANSITION_ALL = re.compile(r"transition\s*:\s*all", re.IGNORECASE)
RE_LAYOUT_TRANSITION = re.compile(r"transition\s*:\s*.*?\b(width|height|margin|padding|top|left)\b", re.IGNORECASE)
RE_HAS_MOTION = re.compile(r"(transition|animation)\s*:", re.IGNORECASE)
RE_REDUCED_MOTION = re.compile(r"prefers-reduced-motion", re.IGNORECASE)

def scan_file(file_path: Path) -> list:
    findings = []
    if not file_path.exists():
        return findings

    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        lines = content.splitlines()

        has_motion = bool(RE_HAS_MOTION.search(content))
        has_reduced_motion = bool(RE_REDUCED_MOTION.search(content))

        if has_motion and not has_reduced_motion:
            findings.append({
                "file": str(file_path),
                "line": 1,
                "severity": "P1",
                "issue": "Missing prefers-reduced-motion media query block",
                "recommendation": "Add @media (prefers-reduced-motion: reduce) block to override transitions."
            })

        for idx, line in enumerate(lines, 1):
            if RE_TRANSITION_ALL.search(line):
                findings.append({
                    "file": str(file_path),
                    "line": idx,
                    "severity": "P0",
                    "issue": "Forbidden transition: all detected",
                    "snippet": line.strip(),
                    "recommendation": "Replace transition: all with explicit composite-only properties (e.g. transition: transform 0.2s, opacity 0.2s)."
                })

            if RE_LAYOUT_TRANSITION.search(line):
                findings.append({
                    "file": str(file_path),
                    "line": idx,
                    "severity": "P1",
                    "issue": "Costly layout property transition detected",
                    "snippet": line.strip(),
                    "recommendation": "Avoid animating layout properties (width/height/margin/padding/top/left). Use transform: scale() or translate() instead."
                })

    except Exception as e:
        print(f"[audit_ui_motion] Error reading {file_path}: {e}")

    return findings

def main():
    print("[audit_ui_motion] Starting UI & Motion Compliance Audit...")
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

    report = {
        "generated_at": datetime.now().isoformat(),
        "files_scanned": files_scanned,
        "total_findings": len(all_findings),
        "summary": {
            "P0": sum(1 for f in all_findings if f["severity"] == "P0"),
            "P1": sum(1 for f in all_findings if f["severity"] == "P1"),
            "P2": sum(1 for f in all_findings if f["severity"] == "P2"),
        },
        "findings": all_findings
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4, ensure_ascii=False)

    print(f"[audit_ui_motion] Scanned {files_scanned} files.")
    print(f"[audit_ui_motion] Findings: P0={report['summary']['P0']}, P1={report['summary']['P1']}, P2={report['summary']['P2']}")
    print(f"[audit_ui_motion] Report written to: {REPORT_PATH}")

if __name__ == "__main__":
    main()
