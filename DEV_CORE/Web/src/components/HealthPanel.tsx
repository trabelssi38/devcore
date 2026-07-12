const checks = [
  { name: "API Gateway", statusText: "ok" },
  { name: "Workers", statusText: "ok" },
  { name: "Database", statusText: "ready" },
];

export function HealthPanel() {
  return (
    <section className="card" aria-label="Santé plateforme">
      <p className="eyebrow">Health</p>
      <h2>Santé système</h2>
      <ul className="stack-list">
        {checks.map((check) => (
          <li key={check.name}>
            <span>{check.name}</span>
            <span className="badge">
              <span className="sr-only">Statut : </span>
              {check.statusText}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
