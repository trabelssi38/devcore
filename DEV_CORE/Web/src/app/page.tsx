const cards = [
  { label: "API", value: "Gateway v1", tone: "var(--color-success)" },
  { label: "Workers", value: "Durable runs", tone: "var(--color-accent)" },
  { label: "Observability", value: "Trace + metrics", tone: "var(--color-warning)" },
];

export default function HomePage() {
  return (
    <main className="shell" aria-label="Vue synthétique DEV_CORE">
      <section className="card">
        <p className="eyebrow">DEV_CORE Platform</p>
        <h1>Interface moderne pour piloter tâches, runs et santé système.</h1>
        <p>
          Ce shell React/Next.js remplace progressivement le HTML métier généré par PowerShell avec une base
          TypeScript, accessible et maintenable.
        </p>
      </section>

      <section className="grid" aria-label="Modules principaux">
        {cards.map((card) => (
          <article className="card" key={card.label}>
            <p className="eyebrow" style={{ color: card.tone }}>
              {card.label}
            </p>
            <h2>{card.value}</h2>
          </article>
        ))}
      </section>
    </main>
  );
}
