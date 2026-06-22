// One helper per endpoint. Each throws an Error with a readable message on
// failure so the UI can show it cleanly. Mind the differing response shapes:
// POST /diagnose is FLAT; GET /corpus/{name}/diagnose is NESTED under `diagnosis`.

async function toError(res) {
  let detail = `${res.status} ${res.statusText}`;
  try {
    const body = await res.json();
    if (body && body.detail) detail = body.detail;
  } catch {
    /* non-JSON error body — keep the status line */
  }
  const err = new Error(detail);
  err.status = res.status; // expose HTTP status so callers can branch (e.g. 422 vs 5xx)
  return err;
}

export async function getCorpus() {
  const res = await fetch('/corpus');
  if (!res.ok) throw await toError(res);
  const data = await res.json(); // { traces: [{name, file, label, injection}] }
  return data.traces ?? [];
}

export async function getBenchmark() {
  const res = await fetch('/benchmark');
  if (!res.ok) throw await toError(res);
  return res.json(); // { accuracy, correct, classified, total_failing, confusion_matrix }
}

// FLAT: { category, confidence, reasoning }
export async function diagnoseUpload(file) {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch('/diagnose', { method: 'POST', body: form });
  if (!res.ok) throw await toError(res);
  return res.json();
}

// NESTED: { name, true_label, diagnosis: { category, confidence, reasoning } }
export async function diagnoseCorpus(name) {
  const res = await fetch(`/corpus/${encodeURIComponent(name)}/diagnose`);
  if (!res.ok) throw await toError(res);
  return res.json();
}
