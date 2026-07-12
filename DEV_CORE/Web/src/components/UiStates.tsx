type StateProps = {
  title: string;
  description: string;
};

export function LoadingState({ title, description }: StateProps) {
  return (
    <section className="card state-card" aria-live="polite" aria-busy="true">
      <p className="eyebrow">Chargement</p>
      <h2>{title}</h2>
      <p>{description}</p>
    </section>
  );
}

export function EmptyState({ title, description }: StateProps) {
  return (
    <section className="card state-card" aria-live="polite">
      <p className="eyebrow">Vide</p>
      <h2>{title}</h2>
      <p>{description}</p>
    </section>
  );
}

export function ErrorState({ title, description, onRetry }: StateProps & { onRetry: () => void }) {
  return (
    <section className="card state-card" aria-live="polite">
      <p className="eyebrow danger">Erreur</p>
      <h2>{title}</h2>
      <p>{description}</p>
      <RetryButton onRetry={onRetry} />
    </section>
  );
}

export function RetryButton({ onRetry }: { onRetry: () => void }) {
  return (
    <button className="button" type="button" onClick={onRetry}>
      Réessayer
    </button>
  );
}
