import CategoryBadge from './CategoryBadge.jsx';
import ConfidenceBar from './ConfidenceBar.jsx';

// For the FLAT diagnosis shape ({category, confidence, reasoning}) — used by upload.
export default function DiagnosisCard({ diagnosis }) {
  if (!diagnosis) return null;
  return (
    <div className="space-y-3 rounded-lg border border-slate-200 bg-slate-50 p-4">
      <div className="flex items-center gap-2">
        <span className="text-xs uppercase tracking-wide text-slate-400">Category</span>
        <CategoryBadge category={diagnosis.category} />
      </div>
      <ConfidenceBar confidence={diagnosis.confidence} />
      <div>
        <p className="mb-1 text-xs uppercase tracking-wide text-slate-400">Reasoning</p>
        <p className="text-sm leading-relaxed text-slate-700">{diagnosis.reasoning}</p>
      </div>
    </div>
  );
}
