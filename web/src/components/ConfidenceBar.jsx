export default function ConfidenceBar({ confidence, category }) {
  const pct = Math.round((confidence ?? 0) * 100);
  // The winning bar glows in its category color (falls back to the accent).
  const glow = category ? `var(--color-${category})` : 'var(--color-accent)';
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs text-muted">
        <span>Confidence</span>
        <span className="font-mono font-medium text-ink">{pct}%</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-surface-2">
        <div
          className="glow h-full rounded-full transition-all"
          style={{ width: `${pct}%`, background: glow, '--glow': glow }}
        />
      </div>
    </div>
  );
}
