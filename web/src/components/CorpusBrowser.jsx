import { useEffect, useState } from 'react';
import { getCorpus, diagnoseCorpus } from '../api.js';
import { Section, Spinner, ErrorBanner } from './ui.jsx';
import CategoryBadge from './CategoryBadge.jsx';
import ConfidenceBar from './ConfidenceBar.jsx';

export default function CorpusBrowser() {
  const [traces, setTraces] = useState([]);
  const [load, setLoad] = useState('loading'); // loading | loaded | error
  const [loadError, setLoadError] = useState('');
  const [rows, setRows] = useState({}); // name -> { status, result, error }

  useEffect(() => {
    let active = true;
    getCorpus()
      .then((t) => active && (setTraces(t), setLoad('loaded')))
      .catch((e) => active && (setLoadError(e.message), setLoad('error')));
    return () => { active = false; };
  }, []);

  async function diagnose(name) {
    setRows((r) => ({ ...r, [name]: { status: 'analyzing' } }));
    try {
      const res = await diagnoseCorpus(name); // NESTED: { name, true_label, diagnosis }
      setRows((r) => ({ ...r, [name]: { status: 'done', result: res } }));
    } catch (e) {
      setRows((r) => ({ ...r, [name]: { status: 'error', error: e.message } }));
    }
  }

  return (
    <Section index="02" title="Corpus Browser" description="Seeded traces with known labels — diagnose one and compare predicted vs actual.">
      {load === 'loading' && <Spinner label="Loading corpus…" />}
      {load === 'error' && <ErrorBanner message={loadError} />}
      {load === 'loaded' && (
        <ul className="space-y-3">
          {traces.map((t) => {
            const row = rows[t.name] || { status: 'idle' };
            const diag = row.result?.diagnosis; // read the NESTED diagnosis here
            const actual = row.result?.true_label ?? t.label;
            const correct = diag && diag.category === actual;
            return (
              <li key={t.name} className="rounded-lg border border-slate-200 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm font-medium text-slate-800">{t.name}</span>
                    <span className="text-xs text-slate-400">actual</span>
                    <CategoryBadge category={t.label} />
                  </div>
                  <button
                    onClick={() => diagnose(t.name)}
                    disabled={row.status === 'analyzing'}
                    className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {row.status === 'analyzing' ? 'Analyzing…' : 'Diagnose'}
                  </button>
                </div>
                {t.injection && <p className="mt-2 text-xs text-slate-500">{t.injection}</p>}

                {row.status === 'analyzing' && <div className="mt-3"><Spinner label="Calling the model…" /></div>}
                {row.status === 'error' && <div className="mt-3"><ErrorBanner message={row.error} /></div>}
                {row.status === 'done' && diag && (
                  <div className="mt-3 rounded-md bg-slate-50 p-3">
                    <div className="flex flex-wrap items-center gap-2 text-sm">
                      <span className="text-slate-500">predicted</span>
                      <CategoryBadge category={diag.category} />
                      <span className="text-slate-400">vs actual</span>
                      <CategoryBadge category={actual} />
                      <span className={`ml-auto font-semibold ${correct ? 'text-emerald-600' : 'text-rose-600'}`}>
                        {correct ? '✓ match' : '✗ mismatch'}
                      </span>
                    </div>
                    <div className="mt-3"><ConfidenceBar confidence={diag.confidence} /></div>
                    <p className="mt-3 text-sm leading-relaxed text-slate-700">{diag.reasoning}</p>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </Section>
  );
}
