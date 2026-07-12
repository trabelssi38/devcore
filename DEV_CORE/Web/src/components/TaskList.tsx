const tasks = [
  { id: "S7-01", title: "Frontend shell", statusText: "terminé" },
  { id: "S7-02", title: "Core dashboard", statusText: "en cours" },
];

export function TaskList() {
  return (
    <section className="card" aria-label="Liste des tâches">
      <p className="eyebrow">Tâches</p>
      <h2>Backlog actif</h2>
      <ul className="stack-list">
        {tasks.map((task) => (
          <li key={task.id}>
            <span className="mono">{task.id}</span>
            <span>{task.title}</span>
            <span className="badge">
              <span className="sr-only">Statut : </span>
              {task.statusText}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
