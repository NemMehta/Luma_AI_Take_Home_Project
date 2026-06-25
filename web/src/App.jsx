import { useCallback, useEffect, useState } from 'react';
import UploadDiagnose from './components/UploadDiagnose.jsx';
import CorpusBrowser from './components/CorpusBrowser.jsx';
import Benchmark from './components/Benchmark.jsx';
import ModelSelector from './components/ModelSelector.jsx';
import { getModels } from './api.js';

export default function App() {
  // Corpus diagnosis results lifted up so Benchmark can recompute the matrix
  // live once every corpus trace has been diagnosed. Keyed by trace name; each
  // value is the NESTED result { name, true_label, diagnosis }. Not persisted —
  // a refresh resets this and Benchmark falls back to the saved snapshot.
  const [corpusResults, setCorpusResults] = useState({});
  const [corpusCount, setCorpusCount] = useState(0); // real corpus length, never hardcoded

  // Global model choice, shared by both flows (upload + corpus). Availability is a
  // real one-token ping per provider (see GET /models). Default to the first
  // available model; '' until verification finishes, which makes both API calls
  // omit the param and fall back to the backend's priority order.
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState('');
  const [modelsStatus, setModelsStatus] = useState('loading'); // loading | loaded | error
  const [modelsError, setModelsError] = useState('');

  useEffect(() => {
    let active = true;
    getModels()
      .then((m) => {
        if (!active) return;
        setModels(m);
        const firstAvailable = m.find((x) => x.available);
        setSelectedModel(firstAvailable ? firstAvailable.id : '');
        setModelsStatus('loaded');
      })
      .catch((e) => {
        if (!active) return;
        setModelsError(e.message);
        setModelsStatus('error');
      });
    return () => { active = false; };
  }, []);

  const handleCorpusLoaded = useCallback((count) => setCorpusCount(count), []);
  const handleCorpusResult = useCallback(
    (name, result) => setCorpusResults((prev) => ({ ...prev, [name]: result })),
    [],
  );

  return (
    <div className="relative grid min-h-screen grid-rows-[auto_1fr_auto] overflow-hidden bg-canvas text-ink lg:h-screen">
      <header className="relative border-b border-hair">
        {/* subtle, static brand light source behind the title */}
        <div
          aria-hidden
          className="pointer-events-none absolute -left-24 -top-24 h-72 w-[36rem] rounded-full opacity-25 blur-3xl"
          style={{ backgroundImage: 'radial-gradient(closest-side, var(--brand-to), transparent 70%), radial-gradient(closest-side, var(--brand-from), transparent 70%)' }}
        />
        <div className="relative mx-auto max-w-6xl px-4 py-8">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h1 className="brand-gradient-text text-3xl font-medium tracking-tight">FlakyLens</h1>
              <p className="mt-1 text-base font-medium text-accent">A clearer solution to automation.</p>
            </div>
            <div className="shrink-0 pt-1">
              <ModelSelector
                models={models}
                value={selectedModel}
                onChange={setSelectedModel}
                status={modelsStatus}
                error={modelsError}
              />
            </div>
          </div>
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted">
            Upload a Playwright{' '}
            <code className="rounded bg-surface-2 px-1 py-0.5 text-xs text-ink">trace.zip</code> and FlakyLens reads the failure
            evidence: the failed action, the error, the DOM snapshot, network activity, and a screenshot. Then it diagnoses{' '}
            <em>why</em> the test failed (a stale selector, a real bug, flaky timing, or a network failure) and gives its
            reasoning and a confidence score.
          </p>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 py-8 lg:min-h-0 lg:flex-row lg:overflow-hidden">
        {/* left pane: section 01 — stays put while the right pane scrolls */}
        <div className="lg:h-full lg:min-h-0 lg:flex-1 lg:overflow-y-auto lg:pr-1">
          <UploadDiagnose selectedModel={selectedModel} />
        </div>
        {/* right pane: sections 02 + 03 — scrolls independently of the page */}
        <div className="space-y-6 lg:h-full lg:min-h-0 lg:flex-1 lg:overflow-y-auto lg:pr-1">
          <CorpusBrowser
            selectedModel={selectedModel}
            onCorpusLoaded={handleCorpusLoaded}
            onCorpusResult={handleCorpusResult}
          />
          <Benchmark corpusResults={corpusResults} corpusCount={corpusCount} />
        </div>
      </main>

      <footer className="mx-auto w-full max-w-6xl px-4 pb-10 text-xs leading-relaxed text-faint lg:pb-4">
        Upload and per-trace Diagnose make real model calls (a few seconds each); repeated clicks may hit rate limits.
        The corpus list and benchmark are cached reads and are safe to refresh.
      </footer>
    </div>
  );
}
