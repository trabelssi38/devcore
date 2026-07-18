"use client";

import { HealthPanel } from "../components/HealthPanel";
import { ProjectSummary } from "../components/ProjectSummary";
import { RunTimeline } from "../components/RunTimeline";
import { TaskList } from "../components/TaskList";
import { EmptyState, ErrorState, LoadingState } from "../components/UiStates";
import { useApiResource } from "../hooks/useApiResource";
import { useDevCoreEvents } from "../hooks/useDevCoreEvents";
import { getHealth, getDashboard, getWorkflows } from "../lib/apiClient";

export default function HomePage() {
  const events = useDevCoreEvents();
  const health = useApiResource(() => getHealth());
  const dashboard = useApiResource(() => getDashboard());
  const workflows = useApiResource(() => getWorkflows());

  const isLoading = 
    health.status === "loading" || 
    dashboard.status === "loading" || 
    workflows.status === "loading";

  const isError = 
    health.status === "error" || 
    dashboard.status === "error" || 
    workflows.status === "error";

  const errorMsg = 
    health.error || 
    dashboard.error || 
    workflows.error || 
    "Une erreur est survenue lors du chargement des données.";

  const activeProject = dashboard.data?.projects_raw?.[0];
  const servicesList = dashboard.data?.services_raw ?? {};
  const tasksList = activeProject?.tasks ?? [];
  const workflowsList = workflows.data?.workflows ?? [];

  const handleRetry = () => {
    health.retry();
    dashboard.retry();
    workflows.retry();
  };

  return (
    <main className="shell" aria-label="Vue synthétique DEV_CORE">
      <section className="card">
        <p className="eyebrow">DEV_CORE Platform</p>
        <h1>Interface moderne pour piloter tâches, runs et santé système.</h1>
        <p>
          Ce cockpit React/Next.js remplace le HTML monolithique généré par PowerShell.
          Il charge en moins de 3 secondes grâce à des API découplées et JSON natifs.
        </p>
      </section>

      {isLoading ? (
        <LoadingState title="Connexion à l’API" description="Chargement des données plateforme..." />
      ) : isError ? (
        <ErrorState title="Connexion interrompue" description={errorMsg} onRetry={handleRetry} />
      ) : (
        <>
          <section className="grid" aria-label="Modules principaux">
            <ProjectSummary project={activeProject} />
            <TaskList tasks={tasksList} />
            <RunTimeline workflows={workflowsList} />
            <HealthPanel services={servicesList} />
          </section>

          <section className="card" aria-label="Événements temps réel">
            <p className="eyebrow">SSE</p>
            <h2>Événements récents</h2>
            <p>{events.length} événement(s) reçus en temps réel</p>
          </section>
        </>
      )}
    </main>
  );
}
