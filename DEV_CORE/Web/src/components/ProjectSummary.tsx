const project = {
  name: "devcore",
  statusText: "Plateforme active",
  apiVersion: "v1",
};

export function ProjectSummary() {
  return (
    <section className="card" aria-label="Résumé projet">
      <p className="eyebrow">Projet</p>
      <h2>{project.name}</h2>
      <p>{project.statusText}</p>
      <dl className="definition-grid">
        <div>
          <dt>API</dt>
          <dd>{project.apiVersion}</dd>
        </div>
        <div>
          <dt>Mode</dt>
          <dd>modernisation</dd>
        </div>
      </dl>
    </section>
  );
}
