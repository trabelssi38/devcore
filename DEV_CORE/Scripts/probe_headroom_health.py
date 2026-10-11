"""Read-only local health probe. Supervisor imposes a process-wide deadline."""
import argparse
import json
from pathlib import Path
import sys
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from devcore_engine.infra.llm_route_contract import PORTS


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--route", choices=PORTS, required=True)
    args = parser.parse_args()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(f"http://127.0.0.1:{PORTS[args.route]}/healthz", timeout=2) as response:
            raw = response.read(32769)
            if len(raw) > 32768:
                raise ValueError("Health document too large")
            document = json.loads(raw)
        print(json.dumps(document))
    except Exception as exc:
        print(type(exc).__name__, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
