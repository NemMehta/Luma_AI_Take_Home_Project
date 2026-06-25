import { useEffect, useState } from 'react';
import { getCorpus, diagnoseCorpus } from '../api.js';
import { Section, Spinner, ErrorBanner } from './ui.jsx';
import CategoryName from './CategoryName.jsx';
import ConfidenceBar from './ConfidenceBar.jsx';
import { categoryBlurb } from '../categories.js';

export default function CorpusBrowser({ selectedModel, onCorpusLoaded, onCorpusResult }) {
  const [traces, setTraces] = useState([]);
  const [load, setLoad] = useState('loading'); // loading | loaded | error
  const [loadError, setLoadError] = useState('');
  const [rows, setRows] = useState({}); // name -> { status, result, error }
  const [running, setRunning] = useState(false); // a run-all pass is in flight
  const [progress, setProgress] = useState(0); // 1-based index of the sample being tested

  useEffect(() => {
    let active = true;
    getCorpus()
      .then((t) => active && (setTraces(t), setLoad('loaded'), onCorpusLoaded?.(t.length)))
      .catch((e) => active && (setLoadError(e.message), setLoad('error')));
    return () => { active = false; };
  }, [onCorpusLoaded]);

  async function diagnose(name) {
    setRows((r) => ({ ...r, [name]: { status: 'analyzing' } }));
    try {
      const res = await diagnoseCorpus(name, selectedModel); // NESTED: { name, true_label, diagnosis }
      setRows((r) => ({ ...r, [name]: { status: 'done', result: res } }));
      onCorpusResult?.(name, res); // lift the nested result up; Benchmark recomputes once all are in
    } catch (e) {
      setRows((r) => ({ ...r, [name]: { status: 'error', error: e.message } }));
    }
  }

  // Run every sample one at a time (not concurrently) to stay under the rate limits.
  // diagnose() swallows its own errors, so one failure doesn't abort the rest.
  async function runAll() {
    setRunning(true);
    for (let i = 0; i < traces.length; i++) {
      setProgress(i + 1);
      await diagnose(traces[i].name);
    }
    setRunning(false);
  }

  const hasRun = Object.keys(rows).length > 0;
  const buttonLabel = running
    ? `Testing ${progress} of ${traces.length}…`
    : hasRun
      ? 'Run again'
      : `Run the model on all ${traces.length} samples`;

  return (
    <Section index="02" title="Try It on Known Bugs" description="Real test failures where we already know the true cause. Run them through the model and see how often its guess matches the answer, a gut-check on how much to trust its diagnosis of your own trace.zip above.">
      {load === 'loading' && <Spinner label="Loading samples…" />}
      {load === 'error' && <ErrorBanner message={loadError} />}
      {load === 'loaded' && (
        <>
          <div className="mb-4">
            <button
              onClick={runAll}
              disabled={running}
              className="btn-primary rounded-md px-4 py-2 text-sm font-medium transition"
            >
              {buttonLabel}
            </button>
          </div>
          <ul className="space-y-3">
            {traces.map((t) => {
              const row = rows[t.name] || { status: 'idle' };
              const diag = row.result?.diagnosis; // read the NESTED diagnosis here
              const actual = row.result?.true_label ?? t.label;
              const correct = diag && diag.category === actual;
              return (
                <li key={t.name} className="rounded-lg border border-hair p-4">
                  {/* Before diagnosis, show only the plain-English scenario — the category
                      is revealed inside the result card once the row is diagnosed. */}
                  {t.injection && <p className="text-xs text-muted">{t.injection}</p>}

                  {row.status === 'analyzing' && <div className="mt-3"><Spinner label="Calling the model…" /></div>}
                  {row.status === 'error' && <div className="mt-3"><ErrorBanner message={row.error} /></div>}
                  {row.status === 'done' && diag && (
                    <div
                      className="reveal glow mt-3 rounded-md bg-surface-2 p-3"
                      style={{ '--glow': `var(--color-${actual})` }}
                    >
                      <div className="flex gap-2 text-sm">
                        <span className="w-28 shrink-0 text-muted">Known cause</span>
                        <div className="min-w-0">
                          <CategoryName category={actual} />
                          {categoryBlurb(actual) && (
                            <p className="mt-0.5 text-xs text-muted">{categoryBlurb(actual)}</p>
                          )}
                        </div>
                      </div>
                      <div className="mt-2 flex items-center gap-2 text-sm">
                        <span className="w-28 shrink-0 text-muted">Model's guess</span>
                        <CategoryName category={diag.category} />
                        <span
                          className={`ml-auto font-medium ${correct ? '' : 'text-muted'}`}
                          style={correct ? { color: `var(--color-${actual})` } : undefined}
                        >
                          {correct ? '✓ correct' : '✗ wrong'}
                        </span>
                      </div>
                      <div className="mt-3"><ConfidenceBar confidence={diag.confidence} category={diag.category} /></div>
                      <div className="mt-3">
                        <p className="mb-1 text-xs text-muted">Reasoning</p>
                        <p className="text-sm leading-relaxed text-ink">{diag.reasoning}</p>
                      </div>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        </>
      )}
    </Section>
  );
}
