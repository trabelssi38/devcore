#!/usr/bin/env python3
# test_container_e2e.py -- DEV_CORE v10 Container & End-to-End Integration Verification Suite

import sys
import json
import urllib.request
from pathlib import Path

def test_endpoint(name, url, expected_status=200):
    print(f"[e2e_test] Testing {name} -> {url}...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "DEVCORE-E2E-Verifier"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            status = resp.status
            body = resp.read().decode()
            if status == expected_status:
                print(f"  [PASS] {name} HTTP {status} (Payload: {len(body)} bytes)")
                return True
            else:
                print(f"  [FAIL] {name} expected HTTP {expected_status}, got {status}")
                return False
    except Exception as e:
        print(f"  [FAIL] {name} error: {e}")
        return False

def main():
    print("==========================================")
    print(" DEV_CORE v10 -- End-to-End Test Suite")
    print("==========================================")

    tests = [
        ("Dashboard API Status", "http://127.0.0.1:20129/api/dashboard/tasks?limit=5"),
        ("Gemini Router Health", "http://127.0.0.1:20130/health"),
        ("Qdrant Vector DB", "http://127.0.0.1:6333/"),
        ("Repowise Server", "http://127.0.0.1:7337/health"),
        ("Headroom Proxy", "http://127.0.0.1:8787/health"),
    ]

    passed = 0
    total = len(tests)

    for name, url in tests:
        if test_endpoint(name, url):
            passed += 1

    print("\n==========================================")
    print(f" Test Results: {passed}/{total} Passed")
    print("==========================================")

    if passed == total:
        print("[SUCCESS] All DEV_CORE v10 platform endpoints are HEALTHY and OPERATIONAL!")
        sys.exit(0)
    else:
        print(f"[WARNING] {total - passed} endpoint(s) failed or offline.")
        sys.exit(1)

if __name__ == "__main__":
    main()
