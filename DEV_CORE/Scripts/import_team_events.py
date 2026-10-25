"""Import legacy bus events into the PostgreSQL team-schema events table."""
from __future__ import annotations
import argparse, json, sqlite3, uuid
from datetime import datetime, timezone
from pathlib import Path
import psycopg

NAMESPACE = uuid.UUID("3bbec48a-1d88-524e-b9da-55e57b23a3c7")

def j(value):
    if not value: return "{}"
    try: json.loads(value); return value
    except json.JSONDecodeError: return json.dumps({"source_text": value})

def run(candidate: Path, database: str, password: str, output: Path) -> dict:
    s=sqlite3.connect(f"file:{candidate.resolve().as_posix()}?mode=ro&immutable=1",uri=True)
    pg=psycopg.connect(host="127.0.0.1",port=5432,user="postgres",password=password,dbname=database)
    with pg.cursor() as c:
        c.execute("SELECT project_id, legacy_id, task_uuid FROM tasks")
        task_map = {(row[0], row[1]): str(row[2]) for row in c.fetchall()}
        rows=s.execute("SELECT id,source,event_type,project,task_id,correlation_id,payload,created_at FROM bus_events")
        count=0; quarantined=0
        for row in rows:
            task_uuid = task_map.get((row[3], row[4])) if row[4] else None
            c.execute("""INSERT INTO events (id,project_id,task_uuid,event_type,source,correlation_id,payload,created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s) ON CONFLICT (id) DO NOTHING""",
                      (str(row[0]),row[3],task_uuid,row[2],row[1],row[5],j(row[6]),row[7]))
            count+=1
        pg.commit()
        c.execute("SELECT count(*) FROM events")
        stored=c.fetchone()[0]
        c.execute("SELECT count(*) FROM events e LEFT JOIN projects p ON p.id=e.project_id WHERE p.id IS NULL")
        orphan=c.fetchone()[0]
    pg.close(); s.close()
    result={"report_version":1,"created_utc":datetime.now(timezone.utc).isoformat(),"status":"events_imported","database":database,"source_events":count,"stored_events":stored,"orphan_events":orphan,"quarantined":quarantined,"blockers":[] if orphan==0 else ["orphan_events"]}
    output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8"); print(json.dumps(result,ensure_ascii=False)); return result

def main()->int:
    p=argparse.ArgumentParser(); p.add_argument("--candidate",type=Path,required=True); p.add_argument("--database",required=True); p.add_argument("--password",required=True); p.add_argument("--output",type=Path,required=True); a=p.parse_args(); r=run(a.candidate.resolve(strict=True),a.database,a.password,a.output); return 0 if not r["blockers"] else 2
if __name__ == "__main__": raise SystemExit(main())
