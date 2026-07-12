"use client";

import { HealthPanel } from "../components/HealthPanel";
import { ProjectSummary } from "../components/ProjectSummary";
import { RunTimeline } from "../components/RunTimeline";
import { TaskList } from "../components/TaskList";
import { useDevCoreEvents } from "../hooks/useDevCoreEvents";
import { getHealth } from "../lib/apiClient";

export default function HomePage() {
  const events = useDevCoreEvents();
  void getHealth;

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

      <section className="card" aria-label="Événements temps réel">
        <p className="eyebrow">SSE</p>
        <h2>Événements récents</h2>
        <p>{events.length} événement(s) reçus</p>
      </section>
    </main>
  );
}
