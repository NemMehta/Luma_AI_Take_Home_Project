import CategoryName from './CategoryName.jsx';
import ConfidenceBar from './ConfidenceBar.jsx';
import { categoryBlurb } from '../categories.js';

// For the FLAT diagnosis shape ({category, confidence, reasoning}) — used by upload.
export default function DiagnosisCard({ diagnosis }) {
  if (!diagnosis) return null;
  return (
    <div className="space-y-3 rounded-lg border border-hair bg-surface-2 p-4">
      <div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted">Category</span>
          <CategoryName category={diagnosis.category} />
        </div>
        {categoryBlurb(diagnosis.category) && (
          <p className="mt-1 text-xs text-muted">{categoryBlurb(diagnosis.category)}</p>
        )}
      </div>
      <ConfidenceBar confidence={diagnosis.confidence} category={diagnosis.category} />
      <div>
        <p className="mb-1 text-xs text-muted">Reasoning</p>
        <p className="text-sm leading-relaxed text-ink">{diagnosis.reasoning}</p>
      </div>
    </div>
  );
}
