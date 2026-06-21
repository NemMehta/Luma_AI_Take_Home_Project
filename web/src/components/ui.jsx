export function Section({ index, title, description, children }) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-100 px-5 py-4">
        <div className="flex items-baseline gap-2">
          <span className="text-xs font-semibold text-slate-400">{index}</span>
          <h2 className="text-lg font-semibold text-slate-800">{title}</h2>
        </div>
        {description && <p className="mt-1 text-sm text-slate-500">{description}</p>}
      </div>
      <div className="px-5 py-5">{children}</div>
    </section>
  );
}

export function Spinner({ label }) {
  return (
    <div className="flex items-center gap-2 text-sm text-slate-500">
      <span className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-slate-300 border-t-slate-600" />
      {label}
    </div>
  );
}

export function ErrorBanner({ message }) {
  return (
    <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
      <span className="font-medium">Error:</span> {message}
    </div>
  );
}
