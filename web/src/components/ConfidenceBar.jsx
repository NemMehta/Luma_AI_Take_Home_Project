export default function ConfidenceBar({ confidence }) {
  const pct = Math.round((confidence ?? 0) * 100);
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs text-slate-500">
        <span>Confidence</span>
        <span className="font-medium text-slate-700">{pct}%</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200">
        <div className="h-full rounded-full bg-slate-700 transition-all" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
