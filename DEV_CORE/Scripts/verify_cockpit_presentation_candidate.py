"""Read and render the candidate Cockpit against an explicit local project.

This is an operational read-only preflight, not a database fixture or migration.
No rendered project data or credentials are written to disk.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from urllib.parse import urlparse


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--expected-database', required=True)
    parser.add_argument('--project', action='append', required=True)
    parser.add_argument('--task-offset', type=int, default=0)
    parser.add_argument('--manifest', type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding='utf-8'))
    dsn = config.get('environment', {}).get('DEVCORE_DATABASE_URL', '')
    target = urlparse(dsn)
    if target.hostname != '127.0.0.1' or target.path.lstrip('/') != args.expected_database:
        raise RuntimeError('Installed local PostgreSQL target differs')
    base = Path(__file__).resolve().parents[1]
    sys.path[:0] = [str(base), str(base / 'API')]
    with tempfile.TemporaryDirectory(prefix='devcore-cockpit-preflight-') as temporary:
        os.environ['DEVCORE_LOCAL_ROOT'] = str(Path(temporary) / 'local')
        os.environ['DEVCORE_DATA_ROOT'] = str(Path(temporary) / 'data')
        if args.manifest:
            os.environ['DEVCORE_GLOBAL_STACK_MANIFEST'] = str(args.manifest.resolve(strict=True))
        from devcore_engine.security.identity import Principal
        from devcore_engine.services.postgres_dashboard import PostgresDashboardProjection
        from devcore_api.team_cockpit import render_team_cockpit
        projection = PostgresDashboardProjection(dsn)
        results = []
        for project in args.project:
            snapshot = projection.snapshot(Principal('operational-preflight', 'local', project, 'task.read'),
                                           task_offset=args.task_offset)
            json.dumps(snapshot)
            for terminal in (False, True):
                page = render_team_cockpit(base / 'Dashboard', snapshot, terminal=terminal)
                if '{{TASKS_PIPELINE}}' in page or '{{TASK_DETAILS_MAP}}' in page or '<form id="settings-form"' in page:
                    raise RuntimeError('Candidate Cockpit rendering incomplete')
            results.append({'project': project, **snapshot['counts'], 'views_rendered': 2,
                            'detail_entries': len(snapshot['task_details'])})
    print(json.dumps({'status': 'cockpit_presentation_preflight_verified',
                      'json_serializable': True, 'projects': results}))


if __name__ == '__main__':
    main()
