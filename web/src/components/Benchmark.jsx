import { useEffect, useState } from 'react';
import { getBenchmark } from '../api.js';
import { Section, Spinner, ErrorBanner } from './ui.jsx';

export default function Benchmark({ corpusResults = {}, corpusCount = 0 }) {
  const [data, setData] = useState(null); // the saved snapshot from /benchmark
  const [load, setLoad] = useState('loading'); // loading | loaded | error
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    getBenchmark()
      .then((d) => active && (setData(d), setLoad('loaded')))
      .catch((e) => active && (setError(e.message), setLoad('error')));
    return () => { active = false; };
  }, []);

  // Recompute live only once EVERY corpus trace has a (successful) diagnosis.
  // Partial results leave the saved snapshot untouched. Computed in-render from
  // props — nothing is saved, so a refresh returns to the committed snapshot.
  const allDone = corpusCount > 0 && Object.keys(corpusResults).length >= corpusCount;
  const live = allDone && data ? computeLiveBenchmark(corpusResults, data) : null;

  return (
    <Section index="03" title="Benchmark" description="Classifier accuracy on the labeled corpus.">
      {load === 'loading' && <Spinner label="Loading benchmark…" />}
      {load === 'error' && <ErrorBanner message={error} />}
      {load === 'loaded' && data && <BenchmarkBody data={live ?? data} isLive={!!live} />}
    </Section>
  );
}

// Build a confusion matrix from this session's corpus diagnoses, reusing the
// saved snapshot's category set (same rows/cols) so the table keeps its shape.
function computeLiveBenchmark(corpusResults, snapshot) {
  const snapMatrix = snapshot.confusion_matrix || {};
  const rows = Object.keys(snapMatrix);
  const cols = Array.from(new Set(rows.flatMap((r) => Object.keys(snapMatrix[r] || {}))));

  const matrix = {};
  for (const r of rows) {
    matrix[r] = {};
    for (const c of cols) matrix[r][c] = 0;
  }

  let correct = 0;
  let classified = 0;
  for (const res of Object.values(corpusResults)) {
    const actual = res.true_label;
    const predicted = res.diagnosis?.category;
    classified += 1;
    if (actual === predicted) correct += 1;
    if (matrix[actual] && predicted in matrix[actual]) matrix[actual][predicted] += 1;
  }

  return {
    confusion_matrix: matrix,
    accuracy: classified ? correct / classified : 0,
    correct,
    classified,
  };
}

function BenchmarkBody({ data, isLive }) {
  const matrix = data.confusion_matrix || {};
  const rows = Object.keys(matrix);
  const cols = Array.from(new Set(rows.flatMap((r) => Object.keys(matrix[r] || {})))).sort();
  const pct = Math.round((data.accuracy ?? 0) * 100);

  return (
    <div>
      <div className="flex items-baseline gap-3">
        <span className="text-3xl font-bold text-slate-900">{pct}%</span>
        <span className="text-sm text-slate-500">accuracy ({data.correct}/{data.classified} correct)</span>
      </div>
      <p className="mt-1 text-xs text-slate-400">
        {isLive
          ? 'Recomputed live from your corpus diagnoses this session. The model is non-deterministic, so this may differ from the committed baseline.'
          : 'Showing the committed benchmark, a saved run across all labeled samples kept stable for reproducibility. Diagnose all corpus samples in section 02 to recompute this live from fresh predictions.'}
      </p>

      <p className="mt-5 text-xs text-slate-500">
        How to read this: each row is the true label, each column is the model's guess. Cells on the diagonal are
        correct; anything off the diagonal is the model mixing up one category for another.
      </p>

      <div className="mt-3 overflow-x-auto">
        <table className="border-collapse text-sm">
          <thead>
            <tr>
              <th className="px-3 py-2 text-left text-xs font-medium text-slate-400">true \ predicted</th>
              {cols.map((c) => (
                <th key={c} className="px-3 py-2 text-left font-mono text-xs text-slate-500">{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r} className="border-t border-slate-100">
                <td className="px-3 py-2 font-mono text-xs text-slate-600">{r}</td>
                {cols.map((c) => {
                  const v = matrix[r]?.[c] ?? 0;
                  const diagonal = r === c;
                  return (
                    <td
                      key={c}
                      className={`px-3 py-2 text-center tabular-nums ${
                        v === 0
                          ? 'text-slate-300'
                          : diagonal
                            ? 'font-semibold text-emerald-700'
                            : 'font-semibold text-rose-600'
                      }`}
                    >
                      {v}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-5 rounded-md border-l-4 border-amber-300 bg-amber-50 px-4 py-3 text-sm leading-relaxed text-slate-600">
        Worth knowing: <span className="font-medium text-slate-700">flaky_timing</span> and{' '}
        <span className="font-medium text-slate-700">real_bug</span> can land differently from one run to the next. A
        single trace only captures the moment the test failed — it doesn't show whether waiting a little longer would
        have fixed it — so the model is making a judgment call right at that boundary. Re-run the corpus and you may see
        that one cell drift off the diagonal.
      </div>
    </div>
  );
}
