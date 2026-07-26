import argparse
import html
import json
import os
import re
import sys
import urllib.request
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path


PRICE_KEYS = ("input", "cached_input", "output")


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, payload):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def fetch_text(url, timeout=20):
    if url.startswith("file://"):
        return Path(url[7:]).read_text(encoding="utf-8")
    if Path(url).exists():
        return Path(url).read_text(encoding="utf-8")
    req = urllib.request.Request(url, headers={"User-Agent": "DEV_CORE pricing sync"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        data = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
        return data.decode(charset, errors="ignore")


def normalize_model_name(value):
    name = str(value or "").strip().lower()
    name = re.sub(r"\s*\([^)]*\)\s*$", "", name).strip()
    name = re.sub(r"\s+", "-", name)
    if name.startswith("models/"):
        name = name.split("/", 1)[1]
    return name


def normalize_prices(prices):
    normalized = {}
    for key in PRICE_KEYS:
        value = prices.get(key) if isinstance(prices, dict) else None
        if value is None:
            return None
        try:
            normalized[key] = round(float(value), 6)
        except (TypeError, ValueError):
            return None
    return normalized


def html_to_text(text):
    text = re.sub(r"<script\b.*?</script>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text)


def parse_json_catalog(text):
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {}
    models = payload.get("models", payload if isinstance(payload, dict) else {})
    if not isinstance(models, dict):
        return {}
    parsed = {}
    for model_id, model in models.items():
        prices = None
        if isinstance(model, dict):
            prices = normalize_prices(model.get("pricing_per_million_usd") or model)
        if prices:
            parsed[normalize_model_name(model_id)] = {
                "pricing_per_million_usd": prices,
                "confidence": "high",
                "extractor": "json",
            }
    return parsed


def price_near_label(window, label):
    label = label.replace("_", r"[\s_-]?")
    patterns = [
        rf"{label}[^$]{{0,160}}\$\s*([0-9]+(?:\.[0-9]+)?)",
        rf"\$\s*([0-9]+(?:\.[0-9]+)?)[^$]{{0,160}}{label}",
    ]
    for pattern in patterns:
        match = re.search(pattern, window, re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None


def parse_text_catalog(text, known_models):
    plain = html_to_text(text)
    lower = plain.lower()
    parsed = {}
    for model_id in known_models:
        variants = {
            model_id,
            model_id.replace("-", " "),
            model_id.replace(".", " "),
            model_id.replace("-", " ").replace(".", " "),
        }
        positions = [lower.find(variant) for variant in variants if lower.find(variant) >= 0]
        if not positions:
            continue
        start = max(min(positions) - 800, 0)
        window = plain[start : start + 2400]
        prices = {
            "input": price_near_label(window, "input"),
            "cached_input": price_near_label(window, "cached input") or price_near_label(window, "cache read"),
            "output": price_near_label(window, "output"),
        }
        normalized = normalize_prices(prices)
        if normalized:
            parsed[model_id] = {
                "pricing_per_million_usd": normalized,
                "confidence": "medium",
                "extractor": "text_window",
            }
    return parsed


def parse_catalog(text, known_models):
    parsed = parse_json_catalog(text)
    if parsed:
        return parsed
    return parse_text_catalog(text, known_models)


def collect_remote_prices(registry, source_override=None):
    known_models = {normalize_model_name(model_id) for model_id in registry.get("models", {})}
    provider_by_model = {
        normalize_model_name(model_id): model.get("provider")
        for model_id, model in registry.get("models", {}).items()
        if isinstance(model, dict)
    }
    sources = {"override": source_override} if source_override else registry.get("sources", {})
    remote = {}
    source_errors = {}
    for provider, url in sources.items():
        if not url:
            continue
        try:
            catalog = parse_catalog(fetch_text(url), known_models)
        except Exception as exc:
            source_errors[provider] = str(exc)
            continue
        for model_id, entry in catalog.items():
            if source_override or provider_by_model.get(model_id) == provider:
                entry["source"] = provider
                entry["source_url"] = url
                remote[model_id] = entry
    return remote, source_errors


def diff_prices(registry, remote):
    changes = {}
    unchanged = {}
    missing_remote = []
    skipped_manual = []
    for model_id, model in sorted(registry.get("models", {}).items()):
        canonical_id = normalize_model_name(model_id)
        current = normalize_prices(model.get("pricing_per_million_usd", {}))
        proposed_entry = remote.get(canonical_id)
        if model.get("manual_override"):
            skipped_manual.append(model_id)
            continue
        if not proposed_entry:
            missing_remote.append(model_id)
            continue
        proposed = proposed_entry["pricing_per_million_usd"]
        if current != proposed:
            changes[model_id] = {
                "current": current,
                "proposed": proposed,
                "source": proposed_entry.get("source"),
                "source_url": proposed_entry.get("source_url"),
                "confidence": proposed_entry.get("confidence"),
                "extractor": proposed_entry.get("extractor"),
            }
        else:
            unchanged[model_id] = current
    return {
        "changes": changes,
        "unchanged": unchanged,
        "missing_remote": missing_remote,
        "skipped_manual": skipped_manual,
    }


def should_apply(args, registry):
    sync_config = registry.get("sync", {}) if isinstance(registry.get("sync"), dict) else {}
    return args.apply or os.environ.get("DEVCORE_PRICING_AUTO_APPLY") == "1" or bool(sync_config.get("auto_apply"))


def apply_changes(registry, diff, checked_at, allow_medium_confidence=False):
    updated = deepcopy(registry)
    applied_count = 0
    for model_id, change in diff["changes"].items():
        if change.get("confidence") != "high" and not allow_medium_confidence:
            continue
        model = updated["models"][model_id]
        model["pricing_per_million_usd"] = change["proposed"]
        model["last_checked_at"] = checked_at
        model["last_updated_at"] = checked_at
        model["pricing_source_url"] = change["source_url"]
        model["pricing_sync_confidence"] = change["confidence"]
        applied_count += 1
    sync = updated.setdefault("sync", {})
    sync["last_checked_at"] = checked_at
    sync["last_status"] = "updated" if applied_count else "checked"
    return updated, applied_count


def build_report(registry, remote, source_errors, diff, applied, checked_at):
    return {
        "schema_version": 1,
        "checked_at": checked_at,
        "applied": applied,
        "changes_count": len(diff["changes"]),
        "remote_models_count": len(remote),
        "changes": diff["changes"],
        "missing_remote": diff["missing_remote"],
        "skipped_manual": diff["skipped_manual"],
        "source_errors": source_errors,
        "sources": registry.get("sources", {}),
    }


def default_paths():
    platform_root = Path(os.environ.get("DEVCORE_PLATFORM_ROOT", Path(__file__).resolve().parents[2]))
    data_root = Path(os.environ.get("DEVCORE_DATA_ROOT", str(Path(__file__).resolve().parents[4] / "DEV_CORE_DATA")))
    return (
        platform_root / "Config" / "model_pricing.json",
        data_root / "Logs" / "pricing" / "model_pricing_sync_report.json",
    )


def main():
    default_registry, default_report = default_paths()
    parser = argparse.ArgumentParser(description="Check and optionally update DEV_CORE model pricing.")
    parser.add_argument("--registry", default=str(default_registry))
    parser.add_argument("--report-out", default=str(default_report))
    parser.add_argument("--source", help="Override source URL/path for tests or a trusted catalog.")
    parser.add_argument("--apply", action="store_true", help="Apply detected pricing changes to the registry.")
    parser.add_argument("--allow-medium-confidence", action="store_true", help="Allow text-scraped pricing changes to be applied.")
    parser.add_argument("--fail-on-change", action="store_true", help="Return exit code 2 when changes are detected.")
    args = parser.parse_args()

    checked_at = utc_now()
    registry = load_json(args.registry)
    remote, source_errors = collect_remote_prices(registry, args.source)
    diff = diff_prices(registry, remote)
    applied = False

    if should_apply(args, registry) and diff["changes"]:
        updated, applied_count = apply_changes(registry, diff, checked_at, allow_medium_confidence=args.allow_medium_confidence)
        applied = applied_count > 0
        if applied:
            write_json(args.registry, updated)

    report = build_report(registry, remote, source_errors, diff, applied, checked_at)
    write_json(args.report_out, report)
    print(f"[SUCCESS] Pricing sync report -> {args.report_out}")
    print(f"[INFO] changes={len(diff['changes'])} applied={applied} remote_models={len(remote)}")

    if args.fail_on_change and diff["changes"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
