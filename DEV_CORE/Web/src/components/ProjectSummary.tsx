type ProjectSummaryProps = {
  project?: {
    name: string;
    progress: number;
    active_task: string;
    mode: string;
    statusText?: string;
  };
};

export function ProjectSummary({ project }: ProjectSummaryProps) {
  const name = project?.name ?? "devcore";
  const progress = project?.progress ?? 0;
  const activeTask = project?.active_task ?? "Aucune";
  const mode = project?.mode ?? "N/A";

  return (
    <section className="card" aria-label="Résumé projet">
      <p className="eyebrow">Projet</p>
      <h2>{name}</h2>
      <p>{progress}% complété</p>
      <dl className="definition-grid">
        <div>
          <dt>Tâche active</dt>
          <dd className="mono">{activeTask}</dd>
        </div>
        <div>
          <dt>Mode de routage</dt>
          <dd>{mode}</dd>
        </div>
      </dl>
    </section>
  );
}
