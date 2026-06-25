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

// Configured models and whether each is live right now (real one-token ping,
// cached server-side). Priority order, so the first `available` is the default.
export async function getModels() {
  const res = await fetch('/models');
  if (!res.ok) throw await toError(res);
  const data = await res.json(); // { models: [{id, label, model, available, reason}] }
  return data.models ?? [];
}

export async function getBenchmark() {
  const res = await fetch('/benchmark');
  if (!res.ok) throw await toError(res);
  return res.json(); // { accuracy, correct, classified, total_failing, confusion_matrix }
}

// FLAT: { category, confidence, reasoning }
// `model` (optional) is a provider id from getModels(); omitted => backend default.
export async function diagnoseUpload(file, model) {
  const form = new FormData();
  form.append('file', file);
  if (model) form.append('model', model);
  const res = await fetch('/diagnose', { method: 'POST', body: form });
  if (!res.ok) throw await toError(res);
  return res.json();
}

// NESTED: { name, true_label, diagnosis: { category, confidence, reasoning } }
// `model` (optional) is a provider id from getModels(); omitted => backend default.
export async function diagnoseCorpus(name, model) {
  const query = model ? `?model=${encodeURIComponent(model)}` : '';
  const res = await fetch(`/corpus/${encodeURIComponent(name)}/diagnose${query}`);
  if (!res.ok) throw await toError(res);
  return res.json();
}
