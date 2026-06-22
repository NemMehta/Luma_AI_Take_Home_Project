import { useRef, useState } from 'react';
import { diagnoseUpload } from '../api.js';
import { Section, Spinner } from './ui.jsx';
import DiagnosisCard from './DiagnosisCard.jsx';

export default function UploadDiagnose() {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState('idle'); // idle | analyzing | done | error
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef(null);

  function pick(f) {
    if (!f) return;
    setFile(f);
    setStatus('idle');
    setResult(null);
    setError('');
  }

  async function run() {
    if (!file) return;
    setStatus('analyzing');
    setError('');
    setResult(null);
    try {
      setResult(await diagnoseUpload(file)); // FLAT shape
      setStatus('done');
    } catch (e) {
      setError(e.message);
      setStatus('error');
    }
  }

  return (
    <Section index="01" title="Upload & Diagnose" description="Drop a trace.zip from any Playwright run to get a diagnosis.">
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); pick(e.dataTransfer.files?.[0]); }}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-8 text-center transition ${
          dragOver ? 'border-violet-400 bg-violet-50' : 'border-slate-300 bg-slate-50 hover:border-slate-400'
        }`}
      >
        <input ref={inputRef} type="file" accept=".zip" className="hidden" onChange={(e) => pick(e.target.files?.[0])} />
        <p className="text-sm font-medium text-slate-700">
          {file ? file.name : 'Drop a trace.zip here, or click to choose'}
        </p>
        <p className="mt-1 text-xs text-slate-400">Playwright trace archive (.zip)</p>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <button
          onClick={run}
          disabled={!file || status === 'analyzing'}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          {status === 'analyzing' ? 'Analyzing…' : 'Diagnose'}
        </button>
        {status === 'analyzing' && <Spinner label="Analyzing trace — this calls the model and takes a few seconds." />}
      </div>

      <p className="mt-3 text-xs text-slate-400">
        Heads-up: a timing failure can sometimes read as{' '}
        <span className="font-medium text-slate-500">real_bug</span> — a single trace doesn't always show whether
        waiting a little longer would have fixed it.
      </p>

      {/* Rejection / error state. Deliberately NOT a DiagnosisCard: no category
          pill, no confidence bar — so a boundary rejection (e.g. uploading a
          non-trace zip) can never be mistaken for a red-tinted real_bug result. */}
      {status === 'error' && (
        <div className="mt-4 rounded-lg border border-rose-300 bg-rose-50 p-4">
          <div className="flex items-center gap-2">
            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-rose-200 text-xs font-bold text-rose-700">!</span>
            <p className="text-sm font-semibold text-rose-800">Couldn’t diagnose this upload</p>
          </div>
          <p className="mt-2 text-sm leading-relaxed text-rose-700">{error}</p>
          <p className="mt-2 text-xs text-rose-500">No category or confidence is shown — nothing was diagnosed.</p>
        </div>
      )}
      {status === 'done' && result && <div className="mt-4"><DiagnosisCard diagnosis={result} /></div>}
    </Section>
  );
}
