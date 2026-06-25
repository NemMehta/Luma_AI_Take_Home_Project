import { Spinner } from './ui.jsx';

// Global model picker for the header. Available models are selectable; unavailable
// ones stay in the list but are disabled (browsers grey them) with their reason
// appended, so you can see *why* a key isn't usable — not just that it's missing.
export default function ModelSelector({ models, value, onChange, status, error }) {
  const selectClass =
    'min-w-0 max-w-full rounded-md border border-hair bg-surface-2 px-3 py-1.5 text-sm text-ink ' +
    'transition hover:border-muted disabled:cursor-not-allowed disabled:text-faint';

  return (
    <div className="flex items-center gap-2">
      <label htmlFor="model-select" className="text-xs font-medium text-muted">
        Model
      </label>

      {status === 'loading' && (
        <div className="flex items-center gap-2">
          <select id="model-select" className={selectClass} disabled>
            <option>Verifying models…</option>
          </select>
          <Spinner label="" />
        </div>
      )}

      {status === 'error' && (
        <span className="text-xs text-warn">Couldn’t load models: {error}</span>
      )}

      {status === 'loaded' && (
        <select
          id="model-select"
          className={selectClass}
          value={value}
          disabled={models.length === 0}
          onChange={(e) => onChange(e.target.value)}
        >
          {models.length === 0 && <option value="">No models configured</option>}
          {models.map((m) => (
            <option key={m.id} value={m.id} disabled={!m.available}>
              {m.available ? m.label : `${m.label} — ${m.reason}`}
            </option>
          ))}
        </select>
      )}
    </div>
  );
}
