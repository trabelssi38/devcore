from __future__ import annotations

from collections import Counter
from collections.abc import Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import PlainTextResponse


class InMemoryMetricsRegistry:
    def __init__(self) -> None:
        self.http_requests: Counter[tuple[str, str, int]] = Counter()
        self.worker_runs: Counter[str] = Counter()
        self.workflows: Counter[tuple[str, str]] = Counter()

    def record_http_request(self, *, method: str, path: str, status_code: int) -> None:
        self.http_requests[(method, path, status_code)] += 1

    def record_worker_run(self, *, result: str) -> None:
        self.worker_runs[result] += 1

    def record_workflow_run(self, *, name: str, status: str) -> None:
        self.workflows[(name, status)] += 1

    def render_prometheus(self) -> str:
        # Dynamically load and count workflows from storage before rendering
        try:
            import sys
            from pathlib import Path
            api_dir = Path(__file__).resolve().parent
            tools_dir = api_dir.parents[1] / "Tools"
            if str(tools_dir) not in sys.path:
                sys.path.insert(0, str(tools_dir))

            import json
            from devcore.paths import get_paths
            paths = get_paths()
            workflows_dir = paths.data_root / "Workflows"
            if workflows_dir.exists():
                self.workflows.clear()
                for state_file in workflows_dir.glob("*.state.json"):
                    try:
                        data = json.loads(state_file.read_text(encoding="utf-8"))
                        name = data.get("name", "unknown")
                        status = data.get("status", "unknown")
                        self.record_workflow_run(name=name, status=status)
                    except Exception:
                        pass
        except Exception:
            pass

        lines = [
            "# HELP devcore_http_requests_total Total HTTP requests.",
            "# TYPE devcore_http_requests_total counter",
        ]
        for (method, path, status_code), value in sorted(self.http_requests.items()):
            lines.append(
                f'devcore_http_requests_total{{method="{method}",path="{path}",status_code="{status_code}"}} {value}'
            )
        lines.extend(
            [
                "# HELP devcore_worker_runs_total Total worker runs.",
                "# TYPE devcore_worker_runs_total counter",
            ]
        )
        for result, value in sorted(self.worker_runs.items()):
            lines.append(f'devcore_worker_runs_total{{result="{result}"}} {value}')

        lines.extend(
            [
                "# HELP devcore_workflows_total Total workflows executed.",
                "# TYPE devcore_workflows_total counter",
            ]
        )
        for (name, status), value in sorted(self.workflows.items()):
            lines.append(f'devcore_workflows_total{{name="{name}",status="{status}"}} {value}')

        return "\n".join(lines) + "\n"


def configure_metrics(app: FastAPI, *, registry: InMemoryMetricsRegistry | None = None) -> FastAPI:
    if hasattr(app.state, "metrics_registry"):
        if registry is not None:
            app.state.metrics_registry = registry
        return app

    registry = registry or InMemoryMetricsRegistry()

    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        if request.url.path != "/api/v1/metrics":
            registry.record_http_request(method=request.method, path=request.url.path, status_code=response.status_code)
        return response

    @app.get("/api/v1/metrics", include_in_schema=False)
    async def metrics() -> PlainTextResponse:
        return PlainTextResponse(registry.render_prometheus(), media_type="text/plain; version=0.0.4")

    app.state.metrics_registry = registry
    return app
