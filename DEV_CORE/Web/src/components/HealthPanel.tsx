type HealthPanelProps = {
  services?: Record<string, boolean>;
};

export function HealthPanel({ services = {} }: HealthPanelProps) {
  return (
    <section className="card" aria-label="Santé plateforme">
      <p className="eyebrow">Services</p>
      <h2>Santé système</h2>
      <ul className="stack-list" style={{ listStyle: "none", padding: 0 }}>
        {Object.entries(services).map(([name, alive]) => (
          <li key={name} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
            <span style={{ color: "#f1f5f9" }}>{name.toUpperCase()}</span>
            <span className={`badge ${alive ? "ok" : "error"}`} style={{ fontSize: "10px", padding: "2px 6px", borderRadius: "4px" }}>
              <span className="sr-only">Statut : </span>
              {alive ? "ONLINE" : "OFFLINE"}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
