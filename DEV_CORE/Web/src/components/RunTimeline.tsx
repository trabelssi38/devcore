type WorkflowStep = {
  id: string;
  status: string;
};

type WorkflowRun = {
  run_id: string;
  name: string;
  status: string;
  created_at: string;
};

type RunTimelineProps = {
  workflows?: WorkflowRun[];
};

export function RunTimeline({ workflows = [] }: RunTimelineProps) {
  return (
    <section className="card" aria-label="Chronologie des runs">
      <p className="eyebrow">Workflows</p>
      <h2>Runs récents</h2>
      {workflows.length === 0 ? (
        <p style={{ color: "#64748b", fontSize: "12px" }}>Aucun run de workflow enregistré.</p>
      ) : (
        <ol className="stack-list" style={{ listStyle: "none", padding: 0 }}>
          {workflows.map((run) => (
            <li key={run.run_id} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
              <span className="mono" style={{ color: "#e2e8f0" }}>{run.name} ({run.run_id})</span>
              <span className={`badge ${run.status}`} style={{ fontSize: "10px", padding: "2px 6px", borderRadius: "4px" }}>
                {run.status.toUpperCase()}
              </span>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
