type Task = {
  id: string;
  title: string;
  status: string;
  mode: string;
  steps_done: number;
  steps_total: number;
};

type TaskListProps = {
  tasks?: Task[];
};

export function TaskList({ tasks = [] }: TaskListProps) {
  return (
    <section className="card" aria-label="Liste des tâches">
      <p className="eyebrow">Tâches</p>
      <h2>Backlog actif</h2>
      {tasks.length === 0 ? (
        <p style={{ color: "#64748b", fontSize: "12px" }}>Aucune tâche dans le backlog.</p>
      ) : (
        <ul className="stack-list" style={{ listStyle: "none", padding: 0 }}>
          {tasks.map((task) => (
            <li key={task.id} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
              <span className="mono" style={{ color: "#a5b4fc", fontWeight: "bold" }}>{task.id}</span>
              <span style={{ flex: 1, marginLeft: "12px", color: "#f1f5f9" }}>{task.title}</span>
              <span className={`badge ${task.status}`} style={{ fontSize: "10px", padding: "2px 6px", borderRadius: "4px" }}>
                {task.status.toUpperCase()}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
