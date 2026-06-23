export function Section({ index, title, description, children }) {
  return (
    <section className="rounded-xl border border-hair bg-surface">
      <div className="border-b border-hair px-5 py-4">
        <div className="flex items-baseline gap-2">
          <span className="text-xs font-medium text-accent">{index}</span>
          <h2 className="text-lg font-medium text-ink">{title}</h2>
        </div>
        {description && <p className="mt-1 text-sm text-muted">{description}</p>}
      </div>
      <div className="px-5 py-5">{children}</div>
    </section>
  );
}

export function Spinner({ label }) {
  return (
    <div className="flex items-center gap-2 text-sm text-muted">
      <span className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-hair border-t-ink" />
      {label}
    </div>
  );
}

export function ErrorBanner({ message }) {
  return (
    <div className="rounded-md border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">
      <span className="font-medium">Error:</span> {message}
    </div>
  );
}
