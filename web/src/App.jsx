import { useCallback, useState } from 'react';
import UploadDiagnose from './components/UploadDiagnose.jsx';
import CorpusBrowser from './components/CorpusBrowser.jsx';
import Benchmark from './components/Benchmark.jsx';

export default function App() {
  // Corpus diagnosis results lifted up so Benchmark can recompute the matrix
  // live once every corpus trace has been diagnosed. Keyed by trace name; each
  // value is the NESTED result { name, true_label, diagnosis }. Not persisted —
  // a refresh resets this and Benchmark falls back to the saved snapshot.
  const [corpusResults, setCorpusResults] = useState({});
  const [corpusCount, setCorpusCount] = useState(0); // real corpus length, never hardcoded

  const handleCorpusLoaded = useCallback((count) => setCorpusCount(count), []);
  const handleCorpusResult = useCallback(
    (name, result) => setCorpusResults((prev) => ({ ...prev, [name]: result })),
    [],
  );

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-3xl px-4 py-8">
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">FlakyLens</h1>
          <p className="mt-1 text-base font-medium text-violet-600">A clearer solution to automation.</p>
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-slate-600">
            Upload a Playwright{' '}
            <code className="rounded bg-slate-100 px-1 py-0.5 text-xs">trace.zip</code> and FlakyLens reads the failure
            evidence — the failed action, the error, the DOM snapshot, network activity and a screenshot — then diagnoses{' '}
            <em>why</em> the test failed: a stale selector, a real bug, flaky timing, or a network failure — with its
            reasoning and a confidence score.
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-3xl space-y-8 px-4 py-8">
        <UploadDiagnose />
        <CorpusBrowser onCorpusLoaded={handleCorpusLoaded} onCorpusResult={handleCorpusResult} />
        <Benchmark corpusResults={corpusResults} corpusCount={corpusCount} />
      </main>

      <footer className="mx-auto max-w-3xl px-4 pb-10 text-xs leading-relaxed text-slate-400">
        Upload and per-trace Diagnose make real model calls (a few seconds each); repeated clicks may hit rate limits.
        The corpus list and benchmark are cached reads and are safe to refresh.
      </footer>
    </div>
  );
}
