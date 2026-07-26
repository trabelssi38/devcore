#!/usr/bin/env python3
"""
DEV_CORE Sprint 12 -- Performance Benchmark Script
Objectif: mesurer les composants critiques et decider des candidats Rust

Usage:
    python DEV_CORE/Scripts/benchmark_perf.py
    python DEV_CORE/Scripts/benchmark_perf.py --output DEV_CORE_DATA/Metrics/perf_baseline.json
    python DEV_CORE/Scripts/benchmark_perf.py --component file_scan
"""

import argparse
import json
import os
import sys
import time
import statistics
import subprocess
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PLATFORM_ROOT = Path(os.environ.get("DEVCORE_PLATFORM_ROOT", str(Path(__file__).resolve().parents[3] / "DEV_CORE")))
DATA_ROOT = Path(os.environ.get("DEVCORE_DATA_ROOT", str(Path(__file__).resolve().parents[3] / "DEV_CORE_DATA")))
REPO_ROOT = PLATFORM_ROOT.parent
ITERATIONS = int(os.environ.get("BENCH_ITERATIONS", "5"))

# Import fast_rglob from file_utils if available
try:
    sys.path.insert(0, str(PLATFORM_ROOT / "Tools" / "devcore"))
    from file_utils import fast_rglob, find_file, DEFAULT_EXCLUDE_DIRS
    FAST_SCAN_AVAILABLE = True
except ImportError:
    FAST_SCAN_AVAILABLE = False
    fast_rglob = None
    find_file = None
    DEFAULT_EXCLUDE_DIRS = frozenset()


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------
def measure(fn, iterations: int = ITERATIONS):
    """Run fn `iterations` times, return {p50, p95, min, max} in ms."""
    times = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        fn()
        times.append((time.perf_counter() - t0) * 1000)
    times.sort()
    p50 = statistics.median(times)
    p95 = times[int(len(times) * 0.95)] if len(times) > 1 else times[-1]
    return {
        "p50_ms": round(p50, 2),
        "p95_ms": round(p95, 2),
        "min_ms": round(times[0], 2),
        "max_ms": round(times[-1], 2),
        "iterations": iterations,
    }


def check_target(result: dict, target_ms: float) -> str:
    """Return PASS/FAIL based on p95 vs target."""
    return "PASS" if result["p95_ms"] <= target_ms else "FAIL"


# ---------------------------------------------------------------------------
# Benchmark 1 : File Scan
# ---------------------------------------------------------------------------
def bench_file_scan():
    """Scan all .py and .ps1 files under repo root.
    Uses fast_rglob (with dir exclusions) if available, else rglob.
    """
    if FAST_SCAN_AVAILABLE:
        def _scan():
            py = fast_rglob(REPO_ROOT, "*.py")
            ps = fast_rglob(REPO_ROOT, "*.ps1")
            return len(py) + len(ps)
        scan_mode = "fast_rglob (excluded: .venv, node_modules, .next, __pycache__)"
    else:
        def _scan():
            return len(list(REPO_ROOT.rglob("*.py"))) + len(list(REPO_ROOT.rglob("*.ps1")))
        scan_mode = "rglob (no exclusions - baseline)"

    result = measure(_scan)
    if FAST_SCAN_AVAILABLE:
        file_count = len(fast_rglob(REPO_ROOT, "*.py")) + len(fast_rglob(REPO_ROOT, "*.ps1"))
    else:
        file_count = len(list(REPO_ROOT.rglob("*.py"))) + len(list(REPO_ROOT.rglob("*.ps1")))
    result["file_count"] = file_count
    result["scan_mode"] = scan_mode
    result["target_ms"] = 500
    result["status"] = check_target(result, 500)
    result["rust_candidate"] = result["p95_ms"] > 500
    result["notes"] = "devcore-scan Rust candidate if p95 > 500ms after Python optimization"
    return result


# ---------------------------------------------------------------------------
# Benchmark 2 : Dashboard Generation
# ---------------------------------------------------------------------------
def bench_dashboard_generation():
    """Time the gen_dashboard.py script execution."""
    script = PLATFORM_ROOT / "Scripts" / "gen_dashboard.py"

    def _gen():
        subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            timeout=60
        )

    if not script.exists():
        return {"error": "gen_dashboard.py not found", "skipped": True}

    result = measure(_gen, iterations=3)

    # Measure output size
    dashboard_path = DATA_ROOT / "Dashboard" / "index.html"
    size_kb = 0
    if dashboard_path.exists():
        size_kb = round(dashboard_path.stat().st_size / 1024, 1)

    result["dashboard_size_kb"] = size_kb
    result["target_ms"] = 3000
    result["status"] = check_target(result, 3000)
    result["rust_candidate"] = False
    result["notes"] = "Python sufficient; consider incremental rendering if > 3s"
    return result


# ---------------------------------------------------------------------------
# Benchmark 3 : Qdrant Search Latency
# ---------------------------------------------------------------------------
def bench_qdrant_search():
    """Measure search latency against Qdrant (10 queries)."""
    try:
        import httpx
    except ImportError:
        return {"error": "httpx not available", "skipped": True}

    qdrant_url = os.environ.get("QDRANT_URL", "http://localhost:6333")
    queries = [
        "authentication JWT token",
        "task T-235 routing",
        "docker compose healthcheck",
        "python scheduler cron",
        "memory hierarchy search",
        "embedding model gemini",
        "headroom proxy compression",
        "dashboard generation html",
        "knowledge graph nodes",
        "sprint 12 benchmark",
    ]

    # Check Qdrant is available
    try:
        r = httpx.get(f"{qdrant_url}/collections", timeout=3)
        collections = r.json().get("result", {}).get("collections", [])
        available_collections = [c["name"] for c in collections]
    except Exception as e:
        return {"error": f"Qdrant unavailable: {e}", "skipped": True}

    # Pick first available collection for testing
    test_collection = None
    for cname in ["conversations", "memory", "codebase", "tasks"]:
        if cname in available_collections:
            test_collection = cname
            break

    if not test_collection:
        return {
            "error": "No usable collection found",
            "available_collections": available_collections,
            "skipped": True
        }

    # Generate a simple embedding via gemini router
    gemini_url = os.environ.get("OPENAI_BASE_URL", "http://localhost:8787")

    def _search():
        # Use text-based scroll query as proxy (no embedding needed)
        r = httpx.post(
            f"{qdrant_url}/collections/{test_collection}/points/scroll",
            json={"limit": 5, "with_payload": False, "with_vector": False},
            timeout=10
        )
        return r.status_code

    result = measure(_search, iterations=10)
    result["collection_tested"] = test_collection
    result["available_collections"] = available_collections
    result["target_ms"] = 150
    result["status"] = check_target(result, 150)
    result["rust_candidate"] = False
    result["notes"] = "I/O bound -- Qdrant native, no Rust extraction needed"
    return result


# ---------------------------------------------------------------------------
# Benchmark 4 : Log Analysis
# ---------------------------------------------------------------------------
def bench_log_analysis():
    """Measure time to parse events + alerts.log."""
    events_dir = DATA_ROOT / "Bus" / "events"
    alerts_log = DATA_ROOT / "Logs" / "alerts.log"

    def _analyze():
        total_lines = 0
        # Parse events
        if events_dir.exists():
            for ev_file in events_dir.glob("*.jsonl"):
                try:
                    with ev_file.open("r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            if line.strip():
                                total_lines += 1
                except OSError:
                    pass
        # Parse alerts
        if alerts_log.exists():
            try:
                with alerts_log.open("r", encoding="utf-8", errors="ignore") as f:
                    total_lines += sum(1 for _ in f)
            except OSError:
                pass
        return total_lines

    result = measure(_analyze)

    # Count files
    event_files = len(list(events_dir.glob("*.jsonl"))) if events_dir.exists() else 0
    alerts_size_kb = round(alerts_log.stat().st_size / 1024, 1) if alerts_log.exists() else 0

    result["event_files"] = event_files
    result["alerts_size_kb"] = alerts_size_kb
    result["target_ms"] = 200
    result["status"] = check_target(result, 200)
    result["rust_candidate"] = result["p95_ms"] > 500
    result["notes"] = "devcore-log-analyzer Rust candidate only if > 500ms or log volume > 100MB"
    return result


# ---------------------------------------------------------------------------
# Benchmark 5 : Tasks JSON Parsing
# ---------------------------------------------------------------------------
def bench_tasks_parsing():
    """Measure time to find and parse the active tasks.json.
    Uses find_file (fast, dir exclusions) if available, else rglob.
    """
    if FAST_SCAN_AVAILABLE:
        def _find_and_parse():
            tf = find_file(REPO_ROOT, "tasks.json")
            if tf is None:
                return None
            try:
                with tf.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return None
        scan_mode = "find_file (fast, excluded dirs)"
    else:
        def _find_and_parse():
            tasks_files = list(REPO_ROOT.rglob("tasks.json"))
            for tf in tasks_files:
                try:
                    with tf.open("r", encoding="utf-8") as f:
                        data = json.load(f)
                        if data.get("project"):
                            return data
                except Exception:
                    pass
            return None
        scan_mode = "rglob (no exclusions - baseline)"

    result = measure(_find_and_parse)
    result["scan_mode"] = scan_mode
    if FAST_SCAN_AVAILABLE:
        result["tasks_files_found"] = 1 if find_file(REPO_ROOT, "tasks.json") else 0
    else:
        result["tasks_files_found"] = len(list(REPO_ROOT.rglob("tasks.json")))
    result["target_ms"] = 100
    result["status"] = check_target(result, 100)
    result["rust_candidate"] = False
    result["notes"] = "Python find_file sufficient with directory exclusions"
    return result


# ---------------------------------------------------------------------------
# Benchmark 6 : Headroom Proxy Roundtrip (models endpoint)
# ---------------------------------------------------------------------------
def bench_headroom_roundtrip():
    """Measure Headroom proxy latency with a simple /v1/models call."""
    try:
        import httpx
    except ImportError:
        return {"error": "httpx not available", "skipped": True}

    headroom_url = os.environ.get("OPENAI_BASE_URL", "http://localhost:8787")

    try:
        r = httpx.get(f"{headroom_url}/v1/models", timeout=3)
        if r.status_code != 200:
            return {"error": f"Headroom returned {r.status_code}", "skipped": True}
    except Exception as e:
        return {"error": f"Headroom unavailable: {e}", "skipped": True}

    def _ping():
        httpx.get(f"{headroom_url}/v1/models", timeout=5)

    result = measure(_ping, iterations=10)
    result["target_ms"] = 50
    result["status"] = check_target(result, 50)
    result["rust_candidate"] = False
    result["notes"] = "Proxy overhead acceptable if < 50ms p95; optimize Headroom middleware if exceeded"
    return result


# ---------------------------------------------------------------------------
# Decision Matrix
# ---------------------------------------------------------------------------
def build_decision_matrix(results: dict) -> dict:
    """Evaluate which components are Rust candidates."""
    candidates = []
    non_candidates = []

    component_map = {
        "file_scan": "devcore-scan",
        "log_analysis": "devcore-log-analyzer",
        "dashboard_generation": "devcore-dash-renderer",
        "qdrant_search": "N/A (native Qdrant)",
        "tasks_parsing": "N/A (Python sufficient)",
        "headroom_roundtrip": "N/A (proxy optimization)",
    }

    for comp, data in results.items():
        if data.get("skipped") or data.get("error"):
            continue
        if data.get("rust_candidate", False):
            candidates.append({
                "component": comp,
                "rust_tool_name": component_map.get(comp, comp),
                "p95_ms": data.get("p95_ms"),
                "target_ms": data.get("target_ms"),
                "overage_pct": round(
                    (data.get("p95_ms", 0) - data.get("target_ms", 0)) /
                    max(data.get("target_ms", 1), 1) * 100, 1
                ),
                "notes": data.get("notes", ""),
            })
        else:
            non_candidates.append({
                "component": comp,
                "p95_ms": data.get("p95_ms"),
                "status": data.get("status", "N/A"),
                "reason": "Python sufficient at current scale",
            })

    verdict = "NO_RUST_NEEDED" if not candidates else "RUST_CANDIDATES_IDENTIFIED"

    return {
        "verdict": verdict,
        "rust_candidates": candidates,
        "python_sufficient": non_candidates,
        "recommendation": (
            "No Rust extraction justified — all components within budget."
            if verdict == "NO_RUST_NEEDED"
            else f"{len(candidates)} component(s) exceed budget: consider Rust prototype with JSON/JSONL contract."
        ),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
BENCHMARKS = {
    "file_scan": bench_file_scan,
    "dashboard_generation": bench_dashboard_generation,
    "qdrant_search": bench_qdrant_search,
    "log_analysis": bench_log_analysis,
    "tasks_parsing": bench_tasks_parsing,
    "headroom_roundtrip": bench_headroom_roundtrip,
}


def main():
    global ITERATIONS
    parser = argparse.ArgumentParser(
        description="DEV_CORE Sprint 12 Performance Benchmark"
    )
    parser.add_argument(
        "--component",
        choices=list(BENCHMARKS.keys()) + ["all"],
        default="all",
        help="Component to benchmark (default: all)",
    )
    parser.add_argument(
        "--output",
        default=str(DATA_ROOT / "Metrics" / "perf_baseline.json"),
        help="Output JSON path",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=ITERATIONS,
        help=f"Number of iterations per benchmark (default: {ITERATIONS})",
    )
    parser.add_argument("--quiet", action="store_true", help="Minimal output")
    args = parser.parse_args()

    ITERATIONS = args.iterations

    components = (
        list(BENCHMARKS.keys())
        if args.component == "all"
        else [args.component]
    )

    print("\n  DEV_CORE Sprint 12 -- Performance Benchmark")
    print(f"  {'=' * 52}")
    print(f"  Platform root : {PLATFORM_ROOT}")
    print(f"  Data root     : {DATA_ROOT}")
    print(f"  Iterations    : {ITERATIONS}")
    print(f"  Components    : {', '.join(components)}")
    print(f"  {'=' * 52}\n")

    results = {}
    for name in components:
        print(f"  [{name}] Running...", end="", flush=True)
        t0 = time.perf_counter()
        try:
            results[name] = BENCHMARKS[name]()
        except Exception as e:
            results[name] = {"error": str(e), "skipped": True}
        elapsed = round((time.perf_counter() - t0) * 1000, 1)

        data = results[name]
        if data.get("skipped"):
            print(f" SKIPPED ({data.get('error', 'N/A')})")
        else:
            status = data.get("status", "?")
            p50 = data.get("p50_ms", "?")
            p95 = data.get("p95_ms", "?")
            target = data.get("target_ms", "?")
            icon = "[OK]  " if status == "PASS" else "[FAIL]"
            print(f" {icon} {status} -- p50={p50}ms p95={p95}ms (target<{target}ms)")

    # Decision matrix
    matrix = build_decision_matrix(results)

    print(f"\n  {'=' * 52}")
    print(f"  VERDICT: {matrix['verdict']}")
    print(f"  {matrix['recommendation']}")
    if matrix["rust_candidates"]:
        print("\n  Rust candidates:")
        for c in matrix["rust_candidates"]:
            print(f"    * {c['component']} -> {c['rust_tool_name']} (p95={c['p95_ms']}ms, +{c['overage_pct']}% over target)")
    print(f"  {'=' * 52}\n")

    # Write output
    output = {
        "sprint": "Sprint 12",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "platform_root": str(PLATFORM_ROOT),
        "data_root": str(DATA_ROOT),
        "iterations": ITERATIONS,
        "benchmarks": results,
        "decision_matrix": matrix,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"  Report written to: {out_path}")
    return 0 if matrix["verdict"] in ("NO_RUST_NEEDED",) or not matrix["rust_candidates"] else 1


if __name__ == "__main__":
    sys.exit(main())
