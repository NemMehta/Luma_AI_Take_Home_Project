import { useRef, useState } from 'react';
import { diagnoseUpload } from '../api.js';
import { Section, Spinner } from './ui.jsx';
import DiagnosisCard from './DiagnosisCard.jsx';

export default function UploadDiagnose() {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState('idle'); // idle | analyzing | done | rejected | error
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
      // 422 = the file itself is bad -> 'rejected' (dead end). 5xx / network
      // error -> 'error' (transient): the file may be fine, allow a retry.
      setStatus(e.status === 422 ? 'rejected' : 'error');
    }
  }

  return (
    <Section index="01" title="Upload & Diagnose" description="Drop a trace.zip from any Playwright run to get a diagnosis.">
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); pick(e.dataTransfer.files?.[0]); }}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-8 text-center transition ${dragOver ? 'border-accent bg-accent/10' : 'border-hair bg-surface-2 hover:border-muted'
          }`}
      >
        <input ref={inputRef} type="file" accept=".zip" className="hidden" onChange={(e) => pick(e.target.files?.[0])} />
        <p className="text-sm font-medium text-ink">
          {file ? file.name : 'Drop a trace.zip here, or click to choose'}
        </p>
        <p className="mt-1 text-xs text-muted">Playwright trace archive (.zip)</p>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <button
          onClick={run}
          // A rejected (422) file is a dead end: stay disabled while it shows.
          // pick() resets status to 'idle' on a new file, which re-enables.
          // A transient 'error' (5xx / network) keeps the button enabled so the
          // same file can be retried.
          disabled={!file || status === 'analyzing' || status === 'rejected'}
          className="btn-primary rounded-md px-4 py-2 text-sm font-medium transition"
        >
          {status === 'analyzing' ? 'Analyzing…' : 'Diagnose'}
        </button>
        {status === 'analyzing' && <Spinner label="Analyzing trace — this calls the model and takes a few seconds." />}
      </div>

      <p className="mt-3 text-xs text-muted">
        Heads-up: a timing failure can sometimes read as{' '}
        <span className="font-medium text-ink">real_bug</span> — a single trace doesn't always show whether
        waiting a little longer would have fixed it.
      </p>

      {/* Rejected (HTTP 422): the file itself is bad — a dead end. Deliberately
          NOT a DiagnosisCard (no category pill, no confidence bar), so a boundary
          rejection can never be mistaken for a red-tinted real_bug result. The
          Diagnose button stays disabled until a different file is picked. */}
      {status === 'rejected' && (
        <div className="mt-4 rounded-lg border border-danger/30 bg-danger/10 p-4">
          <div className="flex items-center gap-2">
            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-danger/20 text-xs font-medium text-danger">!</span>
            <p className="text-sm font-medium text-danger">Couldn’t diagnose this upload</p>
          </div>
          <p className="mt-2 text-sm leading-relaxed text-danger">{error}</p>
          <button
            onClick={() => inputRef.current?.click()}
            className="mt-3 rounded-md border border-danger/40 px-3 py-1.5 text-sm font-medium text-danger transition hover:bg-danger/10"
          >
            Choose a different file
          </button>
        </div>
      )}

      {/* Transient error (5xx / network): the file may be fine, so this is NOT a
          dead end — the Diagnose button stays enabled to retry the same file.
          Also not a DiagnosisCard. Amber (not rose) to read as "try again", not
          "your file is bad". */}
      {status === 'error' && (
        <div className="mt-4 rounded-lg border border-warn/30 bg-warn/10 p-4">
          <div className="flex items-center gap-2">
            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-warn/20 text-xs font-medium text-warn">!</span>
            <p className="text-sm font-medium text-warn">Couldn’t reach the diagnosis service</p>
          </div>
          <p className="mt-2 text-sm leading-relaxed text-warn">{error}</p>
          <p className="mt-2 text-xs font-medium text-warn/80">This looks temporary — press Diagnose to try the same file again.</p>
        </div>
      )}
      {status === 'done' && result && <div className="reveal mt-4"><DiagnosisCard diagnosis={result} /></div>}
    </Section>
  );
}
