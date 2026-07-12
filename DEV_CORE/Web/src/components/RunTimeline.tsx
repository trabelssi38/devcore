const runs = [
  { id: "run-api", statusText: "succeeded" },
  { id: "run-worker", statusText: "queued" },
];

export function RunTimeline() {
  return (
    <section className="card" aria-label="Chronologie des runs">
      <p className="eyebrow">Runs</p>
      <h2>Exécution durable</h2>
      <ol className="stack-list">
        {runs.map((run) => (
          <li key={run.id}>
            <span className="mono">{run.id}</span>
            <span className="badge">
              <span className="sr-only">Statut : </span>
              {run.statusText}
            </span>
          </li>
        ))}
      </ol>
    </section>
  );
}
