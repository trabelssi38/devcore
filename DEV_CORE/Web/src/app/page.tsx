import { HealthPanel } from "../components/HealthPanel";
import { ProjectSummary } from "../components/ProjectSummary";
import { RunTimeline } from "../components/RunTimeline";
import { TaskList } from "../components/TaskList";

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
        <ProjectSummary />
        <TaskList />
        <RunTimeline />
        <HealthPanel />
      </section>
    </main>
  );
}
